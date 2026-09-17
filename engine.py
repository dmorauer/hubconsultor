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
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

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

def mapped_value(mapping, label):
    """Find headers even when an uploaded workbook has damaged accent bytes."""
    target = norm(label)
    if target in mapping:
        return mapping[target]
    candidates = [value for key, value in mapping.items()
                  if SequenceMatcher(None, target, key).ratio() >= .82]
    return candidates[0] if len(candidates) == 1 else None

def fix_encoding(val):
    if not isinstance(val, str) or not val:
        return val
    if any(c in val for c in ('Ã', 'Â', 'É', 'Ç', 'Õ', 'Á', 'Ê', 'À', 'Í', 'Ú', 'â', 'ê', 'î', 'ô', 'û')):
        try:
            raw_bytes = val.encode('latin1')
            decoded = raw_bytes.decode('utf-8')
            if '\ufffd' not in decoded and decoded != val:
                return decoded
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return val

def text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return fix_encoding(str(value).strip())

def document(value):
    return re.sub(r'[.\-/\s]', '', text(value))

def is_valid_cpf(cpf):
    cpf = document(cpf)
    if not re.fullmatch(r'\d{11}', cpf):
        return False
    if cpf == cpf[0] * 11:
        return False
    s1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = 11 - (s1 % 11)
    if d1 >= 10:
        d1 = 0
    if int(cpf[9]) != d1:
        return False
    s2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = 11 - (s2 % 11)
    if d2 >= 10:
        d2 = 0
    if int(cpf[10]) != d2:
        return False
    return True

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


def shared_strings_compatible(path):
    """Convert OpenPyXL inline strings to the shared-string format expected by Paytrack."""
    path = Path(path)
    main_ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    type_ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
    q = lambda namespace, name: f'{{{namespace}}}{name}'
    with ZipFile(path) as archive:
        files = {entry.filename: archive.read(entry.filename) for entry in archive.infolist()}
    shared, positions, total = [], {}, 0
    for name, data in list(files.items()):
        if not name.startswith('xl/worksheets/') or not name.endswith('.xml'):
            continue
        root = ET.fromstring(data)
        changed = False
        for cell in root.findall(f'.//{q(main_ns, "c")}'):
            if cell.get('t') != 'inlineStr':
                continue
            inline = cell.find(q(main_ns, 'is'))
            value = ''.join(inline.itertext()) if inline is not None else ''
            if not value:
                # Keep template placeholders empty. Converting them to a shared
                # empty string changes their meaning when OpenPyXL reopens them.
                cell.attrib.pop('t', None)
                for child in list(cell):
                    cell.remove(child)
                changed = True
                continue
            index = positions.setdefault(value, len(shared))
            if index == len(shared):
                shared.append(value)
            cell.set('t', 's')
            for child in list(cell):
                cell.remove(child)
            ET.SubElement(cell, q(main_ns, 'v')).text = str(index)
            total += 1
            changed = True
        if changed:
            files[name] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    if not total:
        return
    table = ET.Element(q(main_ns, 'sst'), {'count': str(total), 'uniqueCount': str(len(shared))})
    for value in shared:
        item = ET.SubElement(table, q(main_ns, 'si'))
        text_node = ET.SubElement(item, q(main_ns, 't'))
        if value[:1].isspace() or value[-1:].isspace():
            text_node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        text_node.text = value
    files['xl/sharedStrings.xml'] = ET.tostring(table, encoding='utf-8', xml_declaration=True)
    content_types = ET.fromstring(files['[Content_Types].xml'])
    if not any(item.get('PartName') == '/xl/sharedStrings.xml' for item in content_types):
        ET.SubElement(content_types, q(type_ns, 'Override'), {
            'PartName': '/xl/sharedStrings.xml',
            'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml',
        })
    files['[Content_Types].xml'] = ET.tostring(content_types, encoding='utf-8', xml_declaration=True)
    relations_name = 'xl/_rels/workbook.xml.rels'
    relations = ET.fromstring(files[relations_name])
    if not any(item.get('Type', '').endswith('/sharedStrings') for item in relations):
        ids = {item.get('Id') for item in relations}
        number = 1
        while f'rId{number}' in ids:
            number += 1
        ET.SubElement(relations, q(rel_ns, 'Relationship'), {
            'Id': f'rId{number}',
            'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings',
            'Target': 'sharedStrings.xml',
        })
    files[relations_name] = ET.tostring(relations, encoding='utf-8', xml_declaration=True)
    temporary = path.with_suffix('.shared-strings.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    temporary.replace(path)

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

    def readiness_by_kind(self):
        """Local readiness is independent for each output file."""
        readiness = {}
        for kind, records in self.records.items():
            issues = [issue for issue in self.issues if issue.kind == kind]
            errors = sum(issue.severity == 'Erro' for issue in issues)
            pending = sum(issue.severity == 'Pendente' for issue in issues)
            warnings = sum(issue.severity == 'Aviso' for issue in issues)
            if not records:
                status, detail = 'Sem registros', 'Não há registros nesta carga para exportar.'
            elif errors or pending:
                status = 'Com pendências'
                detail = f'{errors} erro(s) e {pending} pendência(s) local(is) para revisar.'
            elif warnings:
                status, detail = 'Pronta com avisos', f'{warnings} aviso(s) local(is); não impedem a exportação.'
            else:
                status, detail = 'Pronta', 'Sem erros ou pendências locais.'
            readiness[kind] = dict(status=status, detail=detail, errors=errors,
                                   pending=pending, warnings=warnings, records=len(records))
        return readiness

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
                header_names = [text(c.value) for c in sheet[1] if c.value is not None]
                header_counts = Counter(norm(h) for h in header_names)
                for h_norm, count in header_counts.items():
                    if count > 1:
                        dup_names = [h for h in header_names if norm(h) == h_norm]
                        self.base_issues.append(Issue(kind, 0, None, f'Colunas duplicadas/conflito no cabeçalho: {", ".join(dup_names)}. Confira a estrutura.', 'Aviso'))
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
                            col = mapped_value(cols, label)
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
                        # The two legacy columns are components of one destination field.
                        # Keep it blank until the person reviewing chooses the concatenation.
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
        if (kind == 'USERS' and col == 2) or (kind == 'EMPLOYER' and col == 1):
            digits = re.sub(r'[^0-9]', '', value)
            return digits.zfill(11 if kind == 'USERS' else 14) if digits else ''
        if kind == 'USERS' and col == 1:
            v_norm = norm(value)
            if v_norm in ('m', 'masculino'):
                return 'M'
            if v_norm in ('f', 'feminino'):
                return 'F'
            return text(value).strip()
        if kind == 'EMPLOYER' and col == 13:
            return document(value)
        if col in ENUMS[kind]:
            return {'SIM': 'S', 'NÃO': 'N', 'NAO': 'N'}.get(value.upper(), value.upper())
        if kind == 'EMPLOYER' and col == 19:
            return 'BRA' if value.upper() == 'BRASIL' else value.upper()
        if kind == 'CUST' and col == 4:
            return document(value).zfill(14) if re.fullmatch(r'[0-9.\-/\s]+', value) and document(value) else value
        if kind == 'USERS' and col == 9:
            return document(value).zfill(14) if re.fullmatch(r'[0-9.\-/\s]+', value) and document(value) else value
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
                    elif kind == 'USERS' and col == 1:
                        if text(before) != after and after in ('M', 'F'):
                            category = 'Sexo'
                    elif (kind == 'USERS' and col in (2, 9)) or (kind == 'EMPLOYER' and col in (1, 13)) or (kind == 'CUST' and col == 4):
                        if str(before) != after and after:
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

    def integration_suggestions(self, rows, pattern='0.{EXTRAFRUTI}.1.{CASAFRUTI}'):
        if not pattern.strip() or any(c in pattern for c in '\r\n') or pattern.startswith('='):
            raise ValueError('Informe um formato de integração válido, em uma única linha.')
        remainder = pattern.replace('{EXTRAFRUTI}', '').replace('{CASAFRUTI}', '')
        if '{' in remainder or '}' in remainder or not any(token in pattern for token in ('{EXTRAFRUTI}', '{CASAFRUTI}')):
            raise ValueError('Use {EXTRAFRUTI} e/ou {CASAFRUTI} para representar os códigos de cada pessoa.')
        records = self.effective()['USERS']
        selected_rows = set(rows)
        proposals = []
        occupied = defaultdict(list)
        for record in records:
            if record.row not in selected_rows and text(record.values[5]):
                occupied[text(record.values[5]).casefold()].append(record.row)
        for record in records:
            if record.row not in rows:
                continue
            source = {norm(k): v for k, v in record.source.items()}
            extra = text(mapped_value(source, 'Código de integração Extrafruti'))
            casa = text(mapped_value(source, 'Código de integração Casafruti'))
            used = [value for token, value in (('{EXTRAFRUTI}', extra), ('{CASAFRUTI}', casa)) if token in pattern]
            valid = bool(used) and any(used) and all(not any(c in value for c in '\r\n') and not value.startswith('=') for value in used if value)
            complete = all(used)
            proposals.append(dict(row=record.row, name=text(record.values[0]),
                extra=extra, casa=casa, before=record.values[5],
                after=pattern.replace('{EXTRAFRUTI}', extra).replace('{CASAFRUTI}', casa) if valid else '',
                complete=complete,
                note='Pronto para confirmar' if valid and complete else
                     'Proposta parcial: um dos códigos está vazio. Confira ou altere o formato antes de confirmar.' if valid else
                     'Revise na origem: não há código ou há fórmula ou quebra de linha.'))
        proposed_rows = defaultdict(list)
        for proposal in proposals:
            if proposal['after']:
                proposed_rows[proposal['after'].casefold()].append(proposal['row'])
        for proposal in proposals:
            key = proposal['after'].casefold()
            conflicts = sorted(set(occupied.get(key, []) + proposed_rows.get(key, [])) - {proposal['row']}) if proposal['after'] else []
            proposal['duplicate'] = bool(conflicts)
            if conflicts:
                proposal['note'] = 'Código de integração duplicado nas linhas ' + ', '.join(map(str, conflicts)) + '. Não será aplicado; revise os códigos na origem ou o formato.'
        return proposals

    def accept_integration_suggestions(self, preview, pattern='0.{EXTRAFRUTI}.1.{CASAFRUTI}'):
        current = self.integration_suggestions([p['row'] for p in preview], pattern)
        if not preview or preview != current or any(not p['after'] or p['duplicate'] for p in preview):
            raise ValueError('A proposta mudou, é inválida ou gera código duplicado. Reabra a revisão.')
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
        previous = self.domains.get(company, '')
        self.domains[company] = domain
        self.history.append([datetime.now().isoformat(timespec='seconds'), 'DOMINIO', '', company, previous, domain])

    def reversible_history(self):
        """Return the user decisions that can be restored to their prior value."""
        entries = []
        for index, entry in enumerate(self.history):
            when, kind, row, field, before, after = entry
            reversible = kind == 'DOMINIO' or (kind in KINDS and row not in ('', None) and field in self.headers[kind])
            entries.append(dict(index=index, when=when, kind=kind, row=row, field=field,
                                before=before, after=after, reversible=reversible))
        return entries

    def undo_history(self, indexes):
        """Undo selected current decisions, preserving the original source workbook."""
        selected = sorted({int(index) for index in indexes}, reverse=True)
        if not selected or any(index < 0 or index >= len(self.history) for index in selected):
            raise ValueError('Selecione decisões válidas para desfazer.')
        entries = self.reversible_history()
        for index in selected:
            entry = entries[index]
            if not entry['reversible']:
                raise ValueError('A seleção contém um registro informativo que não representa uma alteração reversível.')
            if entry['kind'] == 'DOMINIO':
                if self.domains.get(entry['field'], '') != entry['after']:
                    raise ValueError('Uma decisão mais recente alterou este domínio. Atualize a lista antes de desfazer.')
                continue
            key = f"{entry['kind']}:{entry['row']}"
            col = self.headers[entry['kind']].index(entry['field'])
            current = self.decisions.get(key, {}).get(str(col), self.original_values[key][col])
            if self.coerce(entry['kind'], col, current) != self.coerce(entry['kind'], col, entry['after']):
                raise ValueError('Uma decisão mais recente alterou este campo. Atualize a lista antes de desfazer.')
        for index in selected:
            entry = entries[index]
            if entry['kind'] == 'DOMINIO':
                if entry['before']:
                    self.domains[entry['field']] = entry['before']
                else:
                    self.domains.pop(entry['field'], None)
                continue
            key = f"{entry['kind']}:{entry['row']}"
            col = self.headers[entry['kind']].index(entry['field'])
            if entry['before'] == '(origem)':
                self.decisions.get(key, {}).pop(str(col), None)
                if not self.decisions.get(key):
                    self.decisions.pop(key, None)
            else:
                self.decisions.setdefault(key, {})[str(col)] = entry['before']
        self.history = [entry for index, entry in enumerate(self.history) if index not in selected]

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
                    if v[1] and not re.fullmatch(r'[0-9]{14}', str(v[1])):
                        add(kind, row, 1, 'CNPJ deve conter exatamente 14 dígitos; valores maiores não são cortados.', 'Erro')
                    for c in (4, 8):
                        if v[c] and not email_valid(v[c]):
                            add(kind, row, c, 'Formato de e-mail inválido.', 'Erro')
                elif kind == 'USERS':
                    if v[2]:
                        if not re.fullmatch(r'\d{11}', str(v[2])):
                            add(kind, row, 2, 'CPF deve conter exatamente 11 dígitos; valores maiores não são cortados.', 'Erro')
                        elif not is_valid_cpf(v[2]):
                            add(kind, row, 2, 'CPF inválido (dígitos verificadores incorretos). Confirme o documento.', 'Erro')
                    if v[3] and not email_valid(v[3]):
                        add(kind, row, 3, 'Formato de e-mail inválido.', 'Erro')
                    if v[4] and not isinstance(v[4], datetime):
                        add(kind, row, 4, 'Data inválida. Informe DD/MM/AAAA ou deixe o campo opcional vazio.', 'Erro')
                    elif isinstance(v[4], datetime) and v[4].date() > date.today():
                        add(kind, row, 4, 'Nascimento no futuro; confirme a data.', 'Erro')
                    src = {norm(k): value for k, value in record.source.items()}
                    casa = mapped_value(src, 'Código de integração Casafruti')
                    extra = mapped_value(src, 'Código de integração Extrafruti')
                    if (text(casa) or text(extra)) and not v[5]:
                        add(kind, row, 5, 'Há código(s) de integração Casafruti e/ou Extrafruti. Revise a concatenação sugerida.')
                    approver_cpf = document(src.get('cpfusuarioaprovador', ''))
                    if approver_cpf and v[2] and document(v[2]) == approver_cpf:
                        add(kind, row, 12, 'Possível autoaprovação detectada: o CPF do usuário e do aprovador são iguais. Revise.', 'Aviso')
                    if any(src.get(norm(k)) for k in ['CPF Usuário aprovador', 'Nome Usuário aprovador']) and not v[12]:
                        add(kind, row, 12, 'A origem identifica o aprovador por CPF/nome; o destino pede usuário. Deseja informar agora?')

        # References between tabs are deliberately pending reviews: a company or
        # cost center absent from this file can already exist in Paytrack.
        def reference_keys(value):
            raw = text(value)
            if not raw:
                return set()
            digits = document(raw)
            return {raw.casefold(), digits} if digits else {raw.casefold()}

        company_by_reference = defaultdict(list)
        for company in data['EMPLOYER']:
            for value in (company.values[1], company.values[6]):
                for key in reference_keys(value):
                    company_by_reference[key].append(company)

        def companies_for(value):
            matches = []
            for key in reference_keys(value):
                matches.extend(company_by_reference.get(key, []))
            return list({record.row: record for record in matches}.values())

        costs_by_code = defaultdict(list)
        costs_by_description = defaultdict(list)
        for cost in data['CUST']:
            if text(cost.values[1]):
                costs_by_code[text(cost.values[1]).casefold()].append(cost)
            if text(cost.values[2]):
                costs_by_description[norm(cost.values[2])].append(cost)

        for user in data['USERS']:
            values = user.values
            company_value = values[9]
            company_matches = companies_for(company_value)
            if text(company_value):
                if not company_matches:
                    add('USERS', user.row, 9,
                        'Empresa não localizada nesta carga. Ela pode já existir no Paytrack; confirme o CNPJ ou código de integração.',
                        'Pendente')
                elif len(company_matches) > 1:
                    add('USERS', user.row, 9,
                        'Empresa ambígua nesta carga. Há mais de uma unidade com essa referência; confirme o CNPJ ou código de integração.',
                        'Pendente')

            code, description = text(values[10]), text(values[11])
            if not code and not description:
                continue
            candidates = []
            if code:
                candidates.extend(costs_by_code.get(code.casefold(), []))
            if description:
                candidates.extend(costs_by_description.get(norm(description), []))
            candidates = list({record.row: record for record in candidates}.values())
            if not candidates:
                add('USERS', user.row, 10 if code else 11,
                    'Centro de custo não localizado nesta carga. Ele pode já existir no Paytrack; confirme o código ou descrição.',
                    'Pendente')
                continue
            if len(company_matches) == 1:
                expected_company = company_matches[0]
                compatible = [cost for cost in candidates
                              if expected_company in companies_for(cost.values[4])]
                if not compatible:
                    add('USERS', user.row, 10 if code else 11,
                        'Centro de custo localizado, mas vinculado a outra empresa nesta carga. Pode já existir no Paytrack; confirme o vínculo.',
                        'Pendente')
                elif code and description and not any(
                        text(cost.values[1]).casefold() == code.casefold() and norm(cost.values[2]) == norm(description)
                        for cost in compatible):
                    add('USERS', user.row, 10,
                        'Código e descrição do centro de custo não correspondem ao mesmo cadastro nesta carga. Confirme antes de importar.',
                        'Pendente')
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
        integration_counts = Counter(text(r.values[5]).casefold() for r in data['USERS'] if r.values[5])
        for record in data['USERS']:
            if record.values[5] and integration_counts[text(record.values[5]).casefold()] > 1:
                add('USERS', record.row, 5, 'Código de integração repetido. Revise os códigos de origem ou o formato de concatenação; nenhum sufixo foi criado.', 'Erro')
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

    def recommendation_batch(self, categories, pattern, approve_domains=False):
        candidates = []
        def add(category, kind, row, col, before, after):
            if isinstance(after, datetime):
                after = after.strftime('%Y-%m-%d')
            candidates.append(dict(category=category, kind=kind, row=row, col=col, before=before, after=after))
        for p in self.normalizations():
            if p['category'] not in categories:
                continue
            expected = 11 if p['kind'] == 'USERS' and p['col'] == 2 else 14 if (p['kind'], p['col']) in [('EMPLOYER', 1), ('USERS', 9), ('CUST', 4)] else None
            if expected and not re.fullmatch(r'[0-9]{%d}' % expected, text(p['after'])):
                continue
            add(p['category'], p['kind'], p['row'], p['col'], p['before'], p['after'])
        if 'E-mails' in categories:
            for s in self.analyze().suggestions:
                if email_valid(s.proposed) and (s.confirmed_domain or approve_domains):
                    # Email replacement supersedes whitespace-only normalization for the same cell.
                    candidates = [p for p in candidates if (p['kind'], p['row'], p['col']) != ('USERS', s.row, 3)]
                    add('E-mails', 'USERS', s.row, 3, s.original, s.proposed)
        if 'Preenchimento' in categories:
            proposals = self.catalog_suggestions()
            counts = Counter((p['kind'], p['row']) for p in proposals)
            for p in proposals:
                if counts[p['kind'], p['row']] == 1 and 'semelhante' not in p['reason'] and 'por código ou nome' not in p['reason']:
                    for col, value in p['changes'].items():
                        add('Preenchimento', p['kind'], p['row'], col, p['before'][col], value)
        if 'Integração' in categories:
            rows = [r.row for r in self.effective()['USERS'] if not text(r.values[5])]
            for p in self.integration_suggestions(rows, pattern):
                if p['after'] and p['complete'] and not p['duplicate']:
                    add('Integração', 'USERS', p['row'], 5, p['before'], p['after'])
        counts = Counter((p['kind'], p['row'], p['col']) for p in candidates)
        return [p for p in candidates if counts[p['kind'], p['row'], p['col']] == 1]

    def accept_recommendation_batch(self, preview, categories, pattern, approve_domains=False):
        if not preview or preview != self.recommendation_batch(categories, pattern, approve_domains):
            raise ValueError('As recomendações mudaram. Atualize a prévia antes de confirmar.')
        decisions, history = copy.deepcopy(self.decisions), copy.deepcopy(self.history)
        try:
            for p in preview:
                self.set_value(p['kind'], [p['row']], p['col'], p['after'])
                self.history[-1][4] = p['before']
            if approve_domains and any(p['category'] == 'E-mails' for p in preview):
                self.history.append([datetime.now().isoformat(timespec='seconds'), 'USERS', '', 'Domínios exibidos aprovados no lote geral', '', 'Confirmado pelo usuário'])
        except Exception:
            self.decisions, self.history = decisions, history
            raise
        return len(preview)

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
                output_file = staging / f'DEFAULT_{kind}.xlsx'
                wb.save(output_file)
                wb.close()
                shared_strings_compatible(output_file)
                # Reopen and verify exact contract and values, including leading zeroes.
                check = openpyxl.load_workbook(output_file)
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
