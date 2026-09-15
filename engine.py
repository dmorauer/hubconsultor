"""Local spreadsheet conversion. Source files are never written to."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from difflib import SequenceMatcher
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

KINDS = ('EMPLOYER', 'CUST', 'EXPENSES', 'USERS')
SHEETS = {'EMPLOYER': 'Empresas', 'CUST': 'Centros de Custo',
          'EXPENSES': 'Tipos de Despesa', 'USERS': 'Colaboradores'}
LABELS = {'EMPLOYER': 'Unidades de negócio', 'CUST': 'Centros de custo',
          'EXPENSES': 'Tipos de despesa', 'USERS': 'Usuários'}
WIDTHS = {'EMPLOYER': 20, 'CUST': 5, 'EXPENSES': 16, 'USERS': 14}
ENUMS = {'EMPLOYER': {}, 'CUST': {3: ('S', 'N')},
         'USERS': {1: ('M', 'F'), 6: ('S', 'N')},
         'EXPENSES': {4: ('VALOR', 'QUANTIDADE'), **{i: ('S', 'N') for i in range(6, 16)}}}
COMPANY_COL = {'USERS': 9, 'CUST': 4}

def norm(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', value.lower())

def text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()

def document(value):
    return re.sub(r'[.\-/\s]', '', text(value))

def email_valid(value):
    return bool(re.fullmatch(r'[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+', text(value)))

def valid_domain(value):
    return bool(re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}', value.lower()))

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_value(cell, value):
    """Treat worksheet strings as data, never executable spreadsheet formulas."""
    cell.value = None if value == '' else value
    if isinstance(value, str):
        cell.data_type = 's'

@dataclass
class Record:
    kind: str
    row: int
    values: list
    source: dict

    @property
    def key(self):
        return f'{self.kind}:{self.row}'

@dataclass
class Issue:
    kind: str
    row: int
    col: int | None
    message: str
    severity: str = 'Pendente'

@dataclass
class Suggestion:
    row: int
    name: str
    original: str
    proposed: str
    company: str
    domain: str
    confirmed_domain: bool
    note: str

@dataclass
class Analysis:
    records: dict
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)

    @property
    def blocking(self):
        return [i for i in self.issues if i.severity != 'Aviso']

class Project:
    def duplicate_users(self, data=None):
        """Compare effective output values, never merge or discard source rows."""
        groups = defaultdict(list)
        for record in (self.effective() if data is None else data)['USERS']:
            cpf = document(record.values[2])
            if cpf:
                groups[cpf].append(record)
        result = []
        for cpf, records in groups.items():
            if len(records) < 2:
                continue
            differences = [col for col in range(WIDTHS['USERS'])
                           if len({text(r.values[col]) for r in records}) > 1]
            classification = ('Dados de saída iguais' if not differences else
                              'Nomes diferentes' if 0 in differences else 'Dados divergentes')
            result.append(dict(cpf=cpf, records=records, differences=differences,
                               classification=classification))
        return result

    VERSION = 1

    def __init__(self, source, template_dir):
        self.source = Path(source).resolve()
        self.template_dir = Path(template_dir).resolve()
        self.templates = {k: self.template_dir / f'DEFAULT_{k}.xlsx' for k in KINDS}
        self.headers = {}
        self.template_sheets = {}
        self.decisions = {}
        self.domains = {}  # Only explicit user confirmation makes a domain authoritative.
        self.history = []
        self.base_issues = []
        self.records = {k: [] for k in KINDS}
        self.original_values = {}
        self.fingerprints = {'source': file_hash(self.source)}
        self._load_templates()
        self._load_source()

    def _load_templates(self):
        # The bundled schema is the exact supplied import contract, not inferred labels.
        schema = json.loads((Path(__file__).parent / 'schema.json').read_text(encoding='utf8'))
        for kind, path in self.templates.items():
            if not path.is_file():
                raise ValueError(f'Modelo não encontrado: {path.name}')
            wb = openpyxl.load_workbook(path)
            if len(wb.sheetnames) != 1:
                raise ValueError(f'{path.name}: esperado um único separador de carga.')
            sheet = wb.active
            headers = [sheet.cell(1, c + 1).value for c in range(WIDTHS[kind])]
            if headers != schema[kind]['headers'] or sheet.title != schema[kind]['sheet']:
                raise ValueError(f'{path.name}: cabeçalhos ou aba diferentes do modelo suportado. Revise o mapeamento antes de usar este layout.')
            if any(cell.value is not None for row in sheet.iter_rows(min_row=2) for cell in row):
                raise ValueError(f'{path.name}: o modelo deve estar vazio abaixo do cabeçalho.')
            self.headers[kind] = headers
            self.template_sheets[kind] = sheet.title
            self.fingerprints[kind] = file_hash(path)
            wb.close()

    def _load_source(self):
        wb = openpyxl.load_workbook(self.source, data_only=False)
        try:
            for kind, sheet_name in SHEETS.items():
                if sheet_name not in wb.sheetnames:
                    raise ValueError(f'Aba ausente na origem: {sheet_name}.')
                sheet = wb[sheet_name]
                cols = {norm(c.value): c.column for c in sheet[1] if c.value is not None}
                required = {'EMPLOYER': ['Nome', 'CNPJ'], 'CUST': ['Código Centro de custo', 'Nome centro de Custo'],
                            'EXPENSES': ['Nome da Despesa'], 'USERS': ['Nome completo', 'CPF', 'E-mail', 'Ativo (S ou N)']}[kind]
                for header in required:
                    if norm(header) not in cols:
                        raise ValueError(f'{sheet_name}: coluna obrigatória do layout ausente: {header}.')
                ncols = 6 if kind == 'EXPENSES' else 5 if kind == 'CUST' else 14 if kind == 'EMPLOYER' else 23
                for row in sheet.iter_rows(min_row=2):
                    if not any(c.value is not None for c in row[:ncols]):
                        continue
                    if kind == 'EXPENSES' and text(row[0].value).upper().startswith('OBS.:'):
                        self.base_issues.append(Issue(kind, row[0].row, None, 'Observação excluída da carga. Confira se as despesas preenchidas são definitivas.', 'Aviso'))
                        continue
                    src = {text(sheet.cell(1, c.column).value): c.value for c in row[:ncols] if sheet.cell(1, c.column).value is not None}
                    def get(*labels):
                        for label in labels:
                            col = cols.get(norm(label))
                            if col:
                                value = sheet.cell(row[0].row, col).value
                                if isinstance(value, str) and value.startswith('='):
                                    self.base_issues.append(Issue(kind, row[0].row, None, f'Fórmula na origem ({label}); substituir por dado literal e carregar novamente.', 'Erro'))
                                    return ''
                                return value
                        return None
                    if kind == 'EMPLOYER':
                        labels = ['Nome', 'CNPJ', 'Nome para contato', 'Telefone', 'E-mail', 'Moeda (BRL, EUR, USD)', 'Código de integração']
                        address = ['CEP', 'Logradouro', 'Número', 'Bairro', 'Cidade', 'Estado', 'País']
                        values = [get(l) for l in labels] + [None] * 6 + [get(l) for l in address]
                    elif kind == 'CUST':
                        values = [None, get('Código Centro de custo'), get('Nome centro de Custo'), None, get('Empresa(CNPJ)')]
                    elif kind == 'EXPENSES':
                        values = [None, get('Nome da Despesa'), None, None, None, get('Item de Orçamento')] + [None] * 10
                    else:
                        casa, extra = get('Código de integração Casafruti'), get('Código de integração Extrafruti')
                        code = get('Código de integração')
                        if code is None:
                            code = casa if casa is not None and extra is None else extra if extra is not None and casa is None else None
                        values = [get('Nome completo'), get('Sexo (M ou F)'), get('CPF'), get('E-mail'), get('Data de nascimento'), code,
                                  get('Ativo (S ou N)'), get('Usuário'), get('Senha'), get('Empresa (CNPJ)'),
                                  get('Centro de custo (Cód. no ERP)'), get('Descrição centro de custo'), None, None]
                    self.original_values[f'{kind}:{row[0].row}'] = list(values)
                    values = [self.coerce(kind, c, v) for c, v in enumerate(values)]
                    self.records[kind].append(Record(kind, row[0].row, values, src))
        finally:
            wb.close()

    @staticmethod
    def coerce(kind, col, value):
        if value is None or value == '':
            return ''
        if kind == 'USERS' and col == 8:
            return str(value)  # Do not trim passwords.
        if kind == 'USERS' and col == 4:
            if isinstance(value, (datetime, date)):
                return datetime.combine(value.date() if isinstance(value, datetime) else value, datetime.min.time())
            raw = text(value)
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    pass
            return raw
        value = text(value)
        if (kind == 'USERS' and col == 2) or (kind == 'EMPLOYER' and col in (1, 13)):
            return document(value)
        if col in ENUMS[kind]:
            return {'SIM': 'S', 'NÃO': 'N', 'NAO': 'N'}.get(value.upper(), value.upper())
        if kind == 'EMPLOYER' and col == 19:
            return 'BRA' if value.upper() == 'BRASIL' else value.upper()
        if kind == 'CUST' and col == 4:
            return document(value) if re.fullmatch(r'[\d.\-/\s]+', value) else value
        if kind == 'USERS' and col == 9:
            return document(value) if re.fullmatch(r'[\d.\-/\s]+', value) else value
        return value

    def effective(self):
        result = copy.deepcopy(self.records)
        for records in result.values():
            for record in records:
                for c, v in self.decisions.get(record.key, {}).items():
                    record.values[int(c)] = self.coerce(record.kind, int(c), v)
        return result

    def normalizations(self):
        proposals = []
        for kind, records in self.records.items():
            for record in records:
                original = self.original_values[record.key]
                for col, before in enumerate(original):
                    if str(col) in self.decisions.get(record.key, {}) or before is None or (kind == 'USERS' and col == 8):
                        continue
                    after = self.coerce(kind, col, before)
                    category = None
                    if kind == 'USERS' and col == 4:
                        if isinstance(before, str) and isinstance(after, datetime):
                            category = 'Datas'
                    elif (kind == 'USERS' and col in (2, 9)) or (kind == 'EMPLOYER' and col in (1, 13)) or (kind == 'CUST' and col == 4):
                        if isinstance(before, str) and before != after:
                            category = 'Documentos'
                    elif ENUMS[kind].get(col) == ('S', 'N'):
                        if isinstance(before, str) and before != after and after in ('S', 'N'):
                            category = 'Sim/Não'
                    elif isinstance(before, str):
                        cleaned = re.sub(r'\s+', ' ', before).strip()
                        if before != cleaned:
                            category = 'Espaços'
                            after = self.coerce(kind, col, cleaned)
                    if category:
                        proposals.append(dict(kind=kind, row=record.row, col=col, category=category,
                                              before=before, after=after))
        return proposals

    def catalog_suggestions(self):
        data = self.effective()
        proposals = []
        companies = data['EMPLOYER']

        def similarity(left, right):
            a, b = norm(left), norm(right)
            return SequenceMatcher(None, a, b).ratio() if a and b else 0

        def company_matches(value):
            if not text(value):
                return []
            exact = [r for r in companies if text(value) in
                     (text(r.values[1]), text(r.values[6])) and text(r.values[1])]
            if exact:
                return exact
            return [r for r in companies if text(r.values[1]) and similarity(value, r.values[0]) >= .85]

        def add(record, changes, reference, reason):
            changes = {col: value for col, value in changes.items()
                       if text(record.values[col]) != text(value)}
            if changes:
                proposals.append(dict(kind=record.kind, row=record.row,
                    before={col: record.values[col] for col in changes}, changes=changes,
                    reference=f'{SHEETS[reference.kind]} — linha {reference.row}', reason=reason))

        for kind, col in [('USERS', 9), ('CUST', 4)]:
            for record in data[kind]:
                value = record.values[col]
                for company in company_matches(value):
                    add(record, {col: company.values[1]}, company,
                        f'Unidade: {company.values[0]}. Correspondência por código ou nome; confirme a identificação.')

        for record in data['USERS']:
            matches = company_matches(record.values[9])
            # Never select a cost center using an inferred/ambiguous company.
            exact_companies = {text(r.values[1]) for r in matches if text(record.values[9]) in
                               (text(r.values[1]), text(r.values[6]))}
            if len(exact_companies) != 1:
                continue
            company = next(iter(exact_companies))
            candidates = []
            for cost in data['CUST']:
                cost_companies = {text(r.values[1]) for r in company_matches(cost.values[4])
                                  if text(cost.values[4]) in (text(r.values[1]), text(r.values[6]))}
                if cost_companies == {company} and text(cost.values[1]) and text(cost.values[2]):
                    candidates.append(cost)
            code, description = text(record.values[10]), text(record.values[11])
            exact = [c for c in candidates if code and code == text(c.values[1])]
            chosen = exact or [c for c in candidates if similarity(description, c.values[2]) >= .85]
            for cost in chosen:
                add(record, {10: cost.values[1], 11: cost.values[2]}, cost,
                    'Código exato na mesma unidade.' if exact else
                    'Descrição semelhante na mesma unidade; confira antes de aplicar.')
        return proposals

    def accept_catalog_suggestion(self, proposal):
        if proposal not in self.catalog_suggestions():
            raise ValueError('A sugestão mudou. Atualize a análise antes de confirmar.')
        for col, value in proposal['changes'].items():
            self.set_value(proposal['kind'], [proposal['row']], col, value)
            self.history[-1][4] = proposal['before'][col]

    def accept_normalizations(self, preview):
        current = self.normalizations()
        if not preview or any(p not in current for p in preview):
            raise ValueError('A revisão mudou. Atualize as sugestões antes de confirmar.')
        for p in preview:
            value = p['after'].strftime('%Y-%m-%d') if isinstance(p['after'], datetime) else p['after']
            self.set_value(p['kind'], [p['row']], p['col'], value)
            self.history[-1][4] = p['before']

    def set_value(self, kind, rows, col, value):
        if kind == 'USERS' and col == 2 and len(set(rows)) > 1:
            raise ValueError('CPF é individual. Para normalizar vários CPFs, use Correções em lote: cada linha mantém seu próprio documento.')
        if kind not in KINDS or not 0 <= col < WIDTHS[kind]:
            raise ValueError('Campo de destino inválido.')
        known = {r.row for r in self.records[kind]}
        if not rows or any(row not in known for row in rows):
            raise ValueError('Selecione registros válidos.')
        for row in rows:
            key = f'{kind}:{row}'
            previous = self.decisions.get(key, {}).get(str(col), '(origem)')
            self.decisions.setdefault(key, {})[str(col)] = value
            self.history.append([datetime.now().isoformat(timespec='seconds'), kind, row, self.headers[kind][col],
                                 '[oculto]' if kind == 'USERS' and col == 8 else previous,
                                 '[oculto]' if kind == 'USERS' and col == 8 else value])

    def integration_suggestions(self, rows):
        proposals = []
        for record in self.effective()['USERS']:
            if record.row not in rows:
                continue
            source = {norm(k): v for k, v in record.source.items()}
            extra = text(source.get(norm('Código de integração Extrafruti')))
            casa = text(source.get(norm('Código de integração Casafruti')))
            valid = bool(extra and casa and not any(c in extra + casa for c in '.\r\n')
                         and not extra.startswith('=') and not casa.startswith('='))
            proposals.append(dict(row=record.row, name=text(record.values[0]),
                extra=extra, casa=casa, before=record.values[5],
                after=f'0.{extra}.1.{casa}' if valid else '',
                note='Pronto para confirmar' if valid else 'Revise na origem: faltam códigos ou contêm ponto, fórmula ou quebra de linha.'))
        return proposals

    def accept_integration_suggestions(self, preview):
        current = self.integration_suggestions([p['row'] for p in preview])
        if not preview or preview != current or any(not p['after'] for p in preview):
            raise ValueError('A proposta mudou ou há códigos inválidos. Reabra a revisão.')
        for proposal in preview:
            self.set_value('USERS', [proposal['row']], 5, proposal['after'])
            self.history[-1][4] = proposal['before']

    def confirm_domain(self, company, domain):
        domain = domain.strip().lower().lstrip('@')
        if not valid_domain(domain):
            raise ValueError('Informe um domínio válido, como extrafruti.com.br.')
        companies = {r.values[1] for r in self.effective()['EMPLOYER']}
        if company not in companies:
            raise ValueError('Selecione uma unidade cadastrada na planilha.')
        self.domains[company] = domain
        self.history.append([datetime.now().isoformat(timespec='seconds'), 'DOMINIO', '', company, '', domain])

    def analyze(self):
        data = self.effective()
        result = Analysis(data, list(self.base_issues))
        for p in self.normalizations():
            result.issues.append(Issue(p['kind'], p['row'], p['col'],
                f"Normalização de {p['category']} aguardando confirmação na aba Correções em lote."))
        def add(k, r, c, msg, severity='Pendente'):
            result.issues.append(Issue(k, r, c, msg, severity))
        for kind, records in data.items():
            if not records:
                add(kind, 0, None, 'Aba sem registros. Confira se esta carga se aplica.', 'Aviso')
            required = [i for i, h in enumerate(self.headers[kind]) if '*' in h]
            if kind == 'USERS':
                required = [0, 2, 3, 6, 9]
            if kind == 'CUST':
                required = sorted(set(required + [1, 2]))
            for record in records:
                row, v = record.row, record.values
                for c in required:
                    if not v[c]:
                        add(kind, row, c, 'Campo obrigatório vazio. Deseja decidir agora?')
                for c, options in ENUMS[kind].items():
                    if v[c] and v[c] not in options:
                        add(kind, row, c, 'Valor aceito: ' + ', '.join(options), 'Erro')
                if kind == 'EMPLOYER':
                    for c in (4, 8):
                        if v[c] and not email_valid(v[c]):
                            add(kind, row, c, 'Formato de e-mail inválido.', 'Erro')
                elif kind == 'USERS':
                    if v[2] and not re.fullmatch(r'\d{11}', str(v[2])):
                        add(kind, row, 2, 'CPF deve conter 11 dígitos; não completar zeros por suposição.', 'Erro')
                    if v[3] and not email_valid(v[3]):
                        add(kind, row, 3, 'Formato de e-mail inválido.', 'Erro')
                    if v[4] and not isinstance(v[4], datetime):
                        add(kind, row, 4, 'Data inválida. Informe DD/MM/AAAA ou deixe o campo opcional vazio.', 'Erro')
                    elif isinstance(v[4], datetime) and v[4].date() > date.today():
                        add(kind, row, 4, 'Nascimento no futuro; confirme a data.', 'Erro')
                    src = {norm(k): v for k, v in record.source.items()}
                    if src.get(norm('Código de integração Casafruti')) is not None and src.get(norm('Código de integração Extrafruti')) is not None and not v[5]:
                        add(kind, row, 5, 'Há códigos de integração Casafruti e Extrafruti. Deseja escolher agora?')
                    if any(src.get(norm(k)) for k in ['CPF Usuário aprovador', 'Nome Usuário aprovador']) and not v[12]:
                        add(kind, row, 12, 'A origem identifica o aprovador por CPF/nome; o destino pede usuário. Deseja informar agora?')
        # Duplicate identity is a review, not an automatic merge or deletion.
        for group in self.duplicate_users(data):
            rows = ', '.join(str(r.row) for r in group['records'])
            for record in group['records']:
                add('USERS', record.row, 2, f"CPF repetido: {group['classification']}. Linhas {rows}. Compare na aba Duplicidades; nenhuma linha foi removida.", 'Erro')
        for kind, col, label in [('EMPLOYER', 1, 'CNPJ'), ('EXPENSES', 0, 'Código da despesa')]:
            counts = Counter(text(r.values[col]).casefold() for r in data[kind] if r.values[col])
            for r in data[kind]:
                if r.values[col] and counts[text(r.values[col]).casefold()] > 1:
                    add(kind, r.row, col, f'{label} repetido. Revise a identidade; nenhuma linha foi removida.', 'Erro')
        costs = Counter((text(r.values[1]), text(r.values[4])) for r in data['CUST'])
        for r in data['CUST']:
            if costs[(text(r.values[1]), text(r.values[4]))] > 1:
                add('CUST', r.row, 1, 'Identificador repetido na mesma empresa.', 'Erro')
        counts = Counter(text(r.values[3]).casefold() for r in data['USERS'] if r.values[3])
        reserved = {text(r.values[3]).casefold() for r in data['USERS'] if r.values[3]}
        company_refs = {}
        for r in data['EMPLOYER']:
            company_refs[text(r.values[1])] = text(r.values[1])
            if r.values[6]:
                company_refs[text(r.values[6])] = text(r.values[1])
        for r in data['USERS']:
            v = r.values
            if not v[3] or counts[text(v[3]).casefold()] < 2:
                continue
            add('USERS', r.row, 3, 'E-mail repetido. Revise a sugestão ou informe outro endereço.', 'Erro')
            company = company_refs.get(text(v[9]), text(v[9]))
            confirmed = company in self.domains
            domain = self.domains.get(company, text(v[3]).rsplit('@', 1)[-1].lower())
            cpf = document(v[2])
            proposed = ''
            note = 'CPF sem pontuação + domínio da empresa.'
            if re.fullmatch(r'[0-9]{11}', cpf) and valid_domain(domain):
                base = cpf
                proposed = base + '@' + domain
                if proposed.casefold() in reserved:
                    proposed = ''
                    note += ' Endereço já utilizado ou proposto; revise o CPF e o e-mail individualmente.'
                if proposed:
                    reserved.add(proposed.casefold())
            else:
                note = 'CPF deve conter 11 dígitos e o domínio deve ser válido; revise os dados antes de sugerir o endereço.'
            if not confirmed:
                note += ' Domínio original provisório; confirme a unidade e seu domínio antes de aceitar.'
            result.suggestions.append(Suggestion(r.row, text(v[0]), text(v[3]), proposed, company, domain, confirmed, note))
        return result

    def accept_email(self, row, proposed):
        analysis = self.analyze()
        suggestion = next((s for s in analysis.suggestions if s.row == row), None)
        if not suggestion or suggestion.proposed != proposed:
            raise ValueError('A sugestão mudou. Atualize a análise antes de confirmar.')
        if not suggestion.confirmed_domain:
            raise ValueError('Defina a unidade do usuário e confirme o domínio na tela Domínios.')
        if not proposed or not email_valid(proposed):
            raise ValueError('Informe manualmente um endereço válido.')
        if any(text(r.values[3]).casefold() == proposed.casefold() for r in analysis.records['USERS'] if r.row != row):
            raise ValueError('O endereço já está em uso nesta carga.')
        self.set_value('USERS', [row], 3, proposed)

    def accept_all_emails(self, preview, *, approve_displayed_domains=False):
        """Apply one confirmed snapshot atomically, including the last duplicate row."""
        current = self.analyze()
        if current.suggestions != preview:
            raise ValueError('A lista mudou. Abra a prévia novamente antes de confirmar.')
        eligible = [s for s in preview if (s.confirmed_domain or approve_displayed_domains) and email_valid(s.proposed)]
        occupied = {text(r.values[3]).casefold() for r in current.records['USERS'] if r.values[3]}
        for s in eligible:
            if s.proposed.casefold() in occupied:
                raise ValueError('Há colisão entre os endereços. Atualize a análise antes de aplicar.')
            occupied.add(s.proposed.casefold())
        # Validate the entire batch before any mutation. Do not reanalyze between rows.
        for s in eligible:
            self.set_value('USERS', [s.row], 3, s.proposed)
            if not s.confirmed_domain:
                self.history.append([datetime.now().isoformat(timespec='seconds'), 'USERS', s.row,
                                     'Domínio da sugestão aprovado neste lote', '', s.domain])
        return len(eligible), len(preview) - len(eligible)

    def choices(self, kind, row, col):
        if col in ENUMS[kind]:
            return list(ENUMS[kind][col])
        if COMPANY_COL.get(kind) == col:
            return [f'{r.values[1]} | {r.values[0]}' for r in self.effective()['EMPLOYER']]
        if kind == 'USERS' and col == 5:
            record = next(r for r in self.records[kind] if r.row == row)
            return [f'{text(v)} | {k}' for k, v in record.source.items() if norm(k).startswith('codigodeintegracao') and v is not None]
        return []

    def save_session(self, path):
        if Path(path).resolve() in [self.source, *self.templates.values()]:
            raise ValueError('A revisão deve ser salva em um arquivo separado da origem e dos modelos.')
        decisions = copy.deepcopy(self.decisions)
        for key, cells in decisions.items():
            if key.startswith('USERS:'):
                cells.pop('8', None)  # Password overrides never persisted in a review session.
        payload = {'version': self.VERSION, 'fingerprints': self.fingerprints,
                   'decisions': decisions, 'domains': self.domains, 'history': self.history}
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')

    def load_session(self, path):
        p = json.loads(Path(path).read_text(encoding='utf8'))
        if p.get('version') != self.VERSION or p.get('fingerprints') != self.fingerprints:
            raise ValueError('Esta revisão pertence a outra origem ou a outros modelos. Carregue os mesmos arquivos.')
        # Validate all imported edits before mutating the current project.
        for key, cells in p['decisions'].items():
            kind, row = key.split(':')
            if kind not in self.records or int(row) not in {r.row for r in self.records[kind]}:
                raise ValueError('Registro inválido na revisão.')
            if any(not 0 <= int(c) < WIDTHS[kind] for c in cells):
                raise ValueError('Coluna inválida na revisão.')
        if any(not valid_domain(domain) for domain in p['domains'].values()):
            raise ValueError('Domínio inválido na revisão.')
        self.decisions, self.domains, self.history = p['decisions'], p['domains'], p.get('history', [])

    def export(self, destination, *, draft=False):
        if file_hash(self.source) != self.fingerprints['source']:
            raise ValueError('A origem foi alterada. Carregue-a novamente antes de exportar.')
        for kind, path in self.templates.items():
            if file_hash(path) != self.fingerprints[kind]:
                raise ValueError(f'O modelo {path.name} mudou. Carregue novamente.')
        analysis = self.analyze()
        if analysis.blocking and not draft:
            raise ValueError('Há pendências. Resolva-as ou exporte explicitamente como rascunho.')
        parent = Path(destination).resolve()
        parent.mkdir(parents=True, exist_ok=True)
        # Unique batch + atomic directory move: no original or prior export is overwritten.
        name = ('RASCUNHO_' if analysis.blocking or draft else 'CARGAS_') + datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        staging = Path(tempfile.mkdtemp(prefix='.validador_', dir=parent))
        final = parent / name
        try:
            for kind, template in self.templates.items():
                wb = openpyxl.load_workbook(template)
                sheet = wb.active
                for output_row, record in enumerate(analysis.records[kind], 2):
                    for col, value in enumerate(record.values, 1):
                        cell = sheet.cell(output_row, col)
                        if output_row > 2:
                            cell._style = copy.copy(sheet.cell(2, col)._style)
                        safe_value(cell, value)
                        cell.number_format = 'dd/mm/yyyy' if isinstance(value, datetime) else '@'
                wb.save(staging / f'DEFAULT_{kind}.xlsx')
                wb.close()
                # Reopen and verify exact contract and values, including leading zeroes.
                check = openpyxl.load_workbook(staging / f'DEFAULT_{kind}.xlsx')
                assert check.sheetnames == [self.template_sheets[kind]]
                assert [check.active.cell(1, c + 1).value for c in range(WIDTHS[kind])] == self.headers[kind]
                for output_row, record in enumerate(analysis.records[kind], 2):
                    for col, value in enumerate(record.values, 1):
                        assert check.active.cell(output_row, col).value == (None if value == '' else value)
                check.close()
            self._report(analysis, staging / 'REVISAO.xlsx')
            self.save_session(staging / 'revisao.json')
            (staging / 'LEIA-ME.txt').write_text(
                ('RASCUNHO: existem escolhas ou correções pendentes. Não importar como carga final.\n' if analysis.blocking or draft else 'Validações locais concluídas; não foi realizado teste de importação no Paytrack.\n') +
                '\nOrigem: ' + self.source.name + '\n' +
                '\n'.join(f'{LABELS[k]}: {len(analysis.records[k])}' for k in KINDS) +
                f'\nPendências: {len(analysis.blocking)}\n' +
                'A exportação mantém os cabeçalhos e abas dos modelos. Consulte REVISAO.xlsx para dados sem destino, decisões e sugestões.\n' +
                'Os e-mails só mudam após decisão explícita. Sugestão não comprova a existência da caixa postal.\n', encoding='utf8')
            staging.rename(final)
            return final
        except Exception:
            shutil.rmtree(staging)
            raise

    def _report(self, analysis, path):
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        def sheet(name, headers, rows):
            ws = wb.create_sheet(name)
            for ri, row in enumerate([headers] + list(rows), 1):
                for ci, value in enumerate(row, 1):
                    cell = ws.cell(ri, ci)
                    safe_value(cell, value)
                    cell.number_format = '@'
                    cell.alignment = Alignment(vertical='top', wrap_text=True)
                    if ri == 1:
                        cell.font = Font(bold=True, color='FFFFFF')
                        cell.fill = PatternFill('solid', fgColor='244E75')
            ws.freeze_panes = 'A2'
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                width = min(65, max(15, max(len(str(c.value or '')) for c in col) + 2))
                ws.column_dimensions[col[0].column_letter].width = width
            for row in ws:
                lines = max((len(str(c.value or '')) // max(1, int(ws.column_dimensions[c.column_letter].width) - 2) + 1) for c in row)
                ws.row_dimensions[row[0].row].height = max(22, lines * 16)
        sheet('Pendências', ['Aba', 'Linha origem', 'Campo destino', 'Situação', 'Motivo'],
              [[SHEETS[i.kind], i.row or '', self.headers[i.kind][i.col] if i.col is not None else '', i.severity, i.message] for i in analysis.issues])
        sheet('E-mails', ['Linha origem', 'Nome', 'E-mail atual', 'Sugestão', 'Unidade', 'Domínio confirmado', 'Observação'],
              [[s.row, s.name, s.original, s.proposed, s.company, 'S' if s.confirmed_domain else 'N', s.note] for s in analysis.suggestions])
        sheet('Decisões', ['Quando', 'Carga', 'Linha origem', 'Campo', 'Anterior', 'Decisão'], self.history)
        # Preserve all source fields except passwords for auditability, even those without destination.
        extra = []
        for kind, records in self.records.items():
            for r in records:
                for k, v in r.source.items():
                    if v is not None and norm(k) != 'senha':
                        extra.append([SHEETS[kind], r.row, k, str(v) if isinstance(v, (datetime, date)) else v])
        sheet('Dados de origem', ['Aba', 'Linha origem', 'Campo', 'Valor original'], extra)
        sheet('Rastreabilidade', ['Carga', 'Linha origem', 'Linha destino'],
              [[kind, r.row, i + 2] for kind, records in analysis.records.items() for i, r in enumerate(records)])
        sheet('Regras', ['Regra', 'Comportamento'], [
            ['Ambiguidade', 'Perguntar se o usuário deseja decidir agora; adiar mantém a pendência.'],
            ['E-mail repetido', 'CPF com 11 dígitos, sem pontuação, com domínio confirmado da unidade. Colisões exigem revisão manual; nenhum sufixo é acrescentado ao CPF.'],
            ['Exportação', 'Pendências permitem somente rascunho explícito. Nenhuma linha é removida automaticamente.'],
            ['Escopo', 'Layout e validações locais. Sem consulta ao ERP, sem verificação de caixa postal ou importação no Paytrack.'],
            ['Documentos', 'CPF: formato com 11 dígitos. Não consulta situação cadastral nem valida dígitos verificadores nesta versão.'],
            ['Políticas', 'Campos de política sem coluna no DEFAULT_EXPENSES são preservados em Dados de origem.'],
            ['Fonte', self.source.name],
        ])
        wb.save(path)
        wb.close()
