import * as XLSX from "xlsx";
import JSZip from "jszip";

export type Kind = "EMPLOYER" | "CUST" | "EXPENSES" | "USERS";
export type RecordRow = { sourceRow: number; values: string[]; source: Record<string, string> };
export type Conversion = Record<Kind, RecordRow[]>;
export type HierarchyNode = { sourceRow: number; root: string; parent: string; parentDescription: string; id: string; description: string; active: string; company: string; allowanceId: string; travelerCpf: string; approverCpf: string };
export type HierarchyMode = "HIERARQUIA" | "HIERARQUIA_COLABORADORES" | "HIERARQUIA_APROVADORES";
export type HierarchyIssue = { sourceRow: number; field: string; reason: string; severity: "Erro" | "Pendente" };

const definitions: Record<Kind, { sheet: string; required: string[]; width: number }> = {
  EMPLOYER: { sheet: "Empresas", required: ["Nome", "CNPJ"], width: 14 },
  CUST: { sheet: "Centros de Custo", required: ["Código Centro de custo", "Nome centro de Custo"], width: 5 },
  EXPENSES: { sheet: "Tipos de Despesa", required: ["Nome da Despesa"], width: 6 },
  USERS: { sheet: "Colaboradores", required: ["Nome completo", "CPF", "E-mail", "Ativo (S ou N)"], width: 23 },
};
export const labels: Record<Kind, string> = { EMPLOYER: "Unidades de negócio", CUST: "Centros de custo", EXPENSES: "Tipos de despesa", USERS: "Usuários" };
export const outputHeaders: Record<Kind, string[]> = {
  EMPLOYER: ["Nome", "CNPJ", "Contato", "Telefone", "E-mail", "Moeda", "Código de integração", "Contato suporte", "E-mail suporte", "Telefone suporte", "Celular suporte", "WhatsApp suporte", "Unidade faturamento", "CEP", "Logradouro", "Número", "Bairro", "Cidade", "Estado", "País"],
  CUST: ["Identificador pai", "Identificador", "Descrição", "Ativo", "Empresa"],
  EXPENSES: ["Código", "Descrição PT-BR", "Descrição EN", "Descrição ES", "Quantificação", "Item orçamento", "Cotável", "Data final", "Ativo", "Trajeto", "Integração", "Nota", "Imagem", "Região", "Anexo", "Justificativa"],
  USERS: ["Nome completo", "Sexo", "CPF", "E-mail", "Nascimento", "Código integração", "Ativo", "Usuário", "Senha", "Empresa", "Centro custo", "Descrição centro", "Aprovador gestor", "Aprovador valores"],
};

const norm = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const text = (value: unknown) => String(value ?? "").trim();
const digits = (value: unknown) => text(value).replace(/\D/g, "");
const yesNo = (value: unknown) => { const v = text(value).toUpperCase(); if (!v) return "S"; return v.startsWith("S") ? "S" : v.startsWith("N") ? "N" : v; };
const compactDocument = (value: unknown, length: number) => { const valueDigits = digits(value); return valueDigits ? valueDigits.padStart(length, "0") : ""; };

function value(headers: unknown[], row: unknown[], label: string) {
  const index = headers.findIndex((header) => norm(header) === norm(label));
  return index < 0 ? "" : text(row[index]);
}

export function parseHierarchyWorkbook(buffer: ArrayBuffer): HierarchyNode[] {
  const workbook = XLSX.read(buffer, { type: "array", raw: false }); const sheet = workbook.Sheets[workbook.SheetNames[0]];
  if (!sheet) throw new Error("A planilha de hierarquia não possui uma aba utilizável.");
  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: "" }); const [headers = [], ...data] = rows;
  const required = ["identificador_raiz", "identificador_pai", "identificador", "descricao", "ativo", "empresa"];
  required.forEach((header) => { if (!headers.some((cell) => norm(cell) === norm(header))) throw new Error(`Hierarquia: coluna obrigatória ausente: ${header}.`); });
  return data.flatMap((row, index) => {
    if (!row.some((cell) => text(cell))) return [];
    return [{ sourceRow: index + 2, root: value(headers, row, "identificador_raiz"), parent: value(headers, row, "identificador_pai"), parentDescription: value(headers, row, "descricao_pai"), id: value(headers, row, "identificador"), description: value(headers, row, "descricao"), active: value(headers, row, "ativo") || "S", company: value(headers, row, "empresa"), allowanceId: value(headers, row, "identificador_alcada"), travelerCpf: compactDocument(value(headers, row, "cpf_colaborador"), 11), approverCpf: digits(value(headers, row, "cpf_aprovador")) }];
  });
}

export function getHierarchyIssues(nodes: HierarchyNode[]): HierarchyIssue[] {
  const repeated = new Set(nodes.map((node) => `${norm(node.root)}:${norm(node.id)}`).filter((key, _, all) => key && all.filter((current) => current === key).length > 1));
  const known = new Set(nodes.map((node) => `${norm(node.root)}:${norm(node.id)}`));
  return nodes.flatMap((node) => {
    const issues: HierarchyIssue[] = [];
    if (!node.root) issues.push({ sourceRow: node.sourceRow, field: "identificador_raiz", reason: "A hierarquia raiz deve ser informada e já existir no Paytrack.", severity: "Erro" });
    if (!node.id) issues.push({ sourceRow: node.sourceRow, field: "identificador", reason: "Identificador obrigatório vazio.", severity: "Erro" });
    if (!node.description) issues.push({ sourceRow: node.sourceRow, field: "descricao", reason: "Descrição obrigatória vazia.", severity: "Erro" });
    if (node.id && norm(node.id) === norm(node.root)) issues.push({ sourceRow: node.sourceRow, field: "identificador", reason: "O identificador não pode ser igual ao identificador_raiz.", severity: "Erro" });
    if (repeated.has(`${norm(node.root)}:${norm(node.id)}`)) issues.push({ sourceRow: node.sourceRow, field: "identificador", reason: "Identificador repetido dentro da mesma raiz; o Sincronizador consolida essas linhas.", severity: "Pendente" });
    if (node.parent && !known.has(`${norm(node.root)}:${norm(node.parent)}`)) issues.push({ sourceRow: node.sourceRow, field: "identificador_pai", reason: `Pai ${node.parent} não está neste arquivo. Confirme que ele já existe na raiz no Paytrack.`, severity: "Pendente" });
    return issues;
  });
}

export function parseWorkbook(buffer: ArrayBuffer): Conversion {
  const workbook = XLSX.read(buffer, { type: "array", cellDates: true });
  const result = {} as Conversion;
  (Object.keys(definitions) as Kind[]).forEach((kind) => {
    const definition = definitions[kind]; const sheet = workbook.Sheets[definition.sheet];
    if (!sheet) throw new Error(`Aba ausente na origem: ${definition.sheet}.`);
    const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: "" }); const [headers = [], ...data] = rows;
    definition.required.forEach((header) => { if (!headers.some((cell) => norm(cell) === norm(header))) throw new Error(`${definition.sheet}: coluna obrigatória ausente: ${header}.`); });
    result[kind] = data.flatMap((row, index) => {
      if (!row.slice(0, definition.width).some((cell) => text(cell))) return [];
      const source = Object.fromEntries(headers.map((header, column) => [text(header), text(row[column])]));
      if (kind === "EXPENSES" && text(row[0]).toUpperCase().startsWith("OBS.:")) return [];
      let values: string[];
      if (kind === "EMPLOYER") values = [value(headers,row,"Nome"), compactDocument(value(headers,row,"CNPJ"),14), value(headers,row,"Nome para contato"), value(headers,row,"Telefone"), value(headers,row,"E-mail"), value(headers,row,"Moeda (BRL, EUR, USD)"), value(headers,row,"Código de integração"), "", "", "", "", "", "", digits(value(headers,row,"CEP")), value(headers,row,"Logradouro"), value(headers,row,"Número"), value(headers,row,"Bairro"), value(headers,row,"Cidade"), value(headers,row,"Estado"), value(headers,row,"País")];
      else if (kind === "CUST") values = ["", value(headers,row,"Código Centro de custo"), value(headers,row,"Nome centro de Custo"), "", value(headers,row,"Empresa(CNPJ)")];
      else if (kind === "EXPENSES") values = ["", value(headers,row,"Nome da Despesa"), "", "", "", value(headers,row,"Item de Orçamento"), "", "", "", "", "", "", "", "", "", ""];
      else { const email = value(headers,row,"E-mail"); const username = value(headers,row,"Usuário") || email; values = [value(headers,row,"Nome completo"), value(headers,row,"Sexo (M ou F)"), compactDocument(value(headers,row,"CPF"),11), email, value(headers,row,"Data de nascimento"), value(headers,row,"Código de integração"), yesNo(value(headers,row,"Ativo (S ou N)")), username, value(headers,row,"Senha"), value(headers,row,"Empresa (CNPJ)"), value(headers,row,"Centro de custo (Cód. no ERP)"), value(headers,row,"Descrição centro de custo"), "", ""]; }
      return [{ sourceRow: index + 2, values, source }];
    });
  });
  return result;
}

export async function exportDefaults(conversion: Conversion) {
  const zip = new JSZip();
  for (const kind of Object.keys(definitions) as Kind[]) {
    const response = await fetch(`/DEFAULT_${kind}.xlsx`); if (!response.ok) throw new Error(`Modelo DEFAULT_${kind}.xlsx não encontrado.`);
    const workbook = XLSX.read(await response.arrayBuffer(), { type: "array" }); const worksheet = workbook.Sheets[workbook.SheetNames[0]];
    conversion[kind].forEach((record, index) => record.values.forEach((cell, column) => { if (cell) XLSX.utils.sheet_add_aoa(worksheet, [[cell]], { origin: { r: index + 1, c: column } }); }));
    zip.file(`DEFAULT_${kind}.xlsx`, XLSX.write(workbook, { bookType: "xlsx", type: "array", compression: true }));
  }
  const url = URL.createObjectURL(await zip.generateAsync({ type: "blob", compression: "DEFLATE" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = "CARGAS_PAYTRACK.zip"; anchor.click(); URL.revokeObjectURL(url);
}

const csvCell = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
const sourceValue = (source: Record<string, string>, label: string) => Object.entries(source).find(([header]) => norm(header) === norm(label))?.[1] ?? "";
function hierarchyCsv(hierarchy: HierarchyNode[], hierarchyMode: HierarchyMode) {
  const baseHeaders = ["identificador_raiz", "identificador_pai", "descricao_pai", "identificador", "descricao", "ativo", "empresa"];
  const linkHeader = hierarchyMode === "HIERARQUIA_COLABORADORES" ? "cpf_colaborador" : hierarchyMode === "HIERARQUIA_APROVADORES" ? "cpf_aprovador" : "";
  const headers = linkHeader ? [...baseHeaders, linkHeader, "identificador_alcada"] : [...baseHeaders, "identificador_alcada"];
  const rows = hierarchy.map((node) => { const base = [node.root, node.parent, node.parentDescription, node.id, node.description, node.active, node.company]; return linkHeader ? [...base, hierarchyMode === "HIERARQUIA_COLABORADORES" ? node.travelerCpf : node.approverCpf, node.allowanceId] : [...base, node.allowanceId]; });
  return [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
}

export function exportHierarchyCsv(hierarchy: HierarchyNode[], hierarchyMode: HierarchyMode) {
  const url = URL.createObjectURL(new Blob([hierarchyCsv(hierarchy, hierarchyMode)], { type: "text/csv;charset=utf-8" })); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${hierarchyMode}.csv`; anchor.click(); URL.revokeObjectURL(url);
}

export async function exportSynchronizer(conversion: Conversion, hierarchy: HierarchyNode[], hierarchyMode: HierarchyMode) {
  const zip = new JSZip();
  const headers = ["nome", "sexo", "cpf", "email", "data_nascimento", "codigo_integracao", "ativo", "usuario", "senha", "empresa", "cargo", "nome_mae", "telefone", "rg", "cnh", "data_validade_cnh", "centro_custo_codigo_pai", "centro_custo_codigo", "centro_custo_descricao", "banco", "agencia", "conta"];
  const users = conversion.USERS.map((record) => [record.values[0], record.values[1], record.values[2], record.values[3], record.values[4], record.values[5], record.values[6], record.values[7], record.values[8], record.values[9], sourceValue(record.source, "Cargo"), sourceValue(record.source, "Nome da mãe"), sourceValue(record.source, "Telefone"), sourceValue(record.source, "RG"), sourceValue(record.source, "CNH"), sourceValue(record.source, "Data de validade da CNH"), sourceValue(record.source, "Centro de custo (Cód. pai no ERP)"), record.values[10], record.values[11], sourceValue(record.source, "Banco"), sourceValue(record.source, "Agência"), sourceValue(record.source, "Conta")]);
  zip.file("COLABORADORES.csv", [headers, ...users].map((row) => row.map(csvCell).join(",")).join("\r\n"));
  if (hierarchy.length) zip.file(`${hierarchyMode}.csv`, hierarchyCsv(hierarchy, hierarchyMode));

  const hierarchyIssues = getHierarchyIssues(hierarchy);
  const hierarchyErrorCount = hierarchyIssues.filter((i) => i.severity === "Erro").length;
  const hierarchyPendingCount = hierarchyIssues.filter((i) => i.severity === "Pendente").length;

  const summaryContent = [
    "RESUMO DO RELATÓRIO DE REVISÃO E DECISÕES APLICADAS",
    "---------------------------------------------------",
    `Data da exportação: ${new Date().toLocaleString("pt-BR")}`,
    "",
    "1. REGISTROS EXPORTADOS",
    `   - Colaboradores: ${conversion.USERS.length} registro(s)`,
    `   - Unidades de Negócio (Empresas): ${conversion.EMPLOYER.length} registro(s)`,
    `   - Centros de Custo: ${conversion.CUST.length} registro(s)`,
    `   - Tipos de Despesa: ${conversion.EXPENSES.length} registro(s)`,
    `   - Hierarquia (${hierarchyMode}): ${hierarchy.length} nó(s)`,
    "",
    "2. RESUMO DE PENDÊNCIAS E REVISÕES",
    `   - Pendências de Hierarquia: ${hierarchyIssues.length} (${hierarchyErrorCount} erro(s), ${hierarchyPendingCount} aviso(s)/pendência(s))`,
    "",
    "3. DECISÕES E REGISTROS EXPORTADOS",
    "   - Os arquivos CSV foram gerados e sanitizados para importação/sincronização no Paytrack.",
    "   - Para hierarquias, confirme a estrutura da árvore visualmente ou pelo arquivo exportado.",
    ""
  ].join("\r\n");

  zip.file("RESUMO_REVISAO.txt", summaryContent);
  zip.file("LEIA-ME.txt", `Arquivos preparados para o Sincronizador Paytrack.\r\n\r\nEnvie cada CSV diretamente para /sincronizador/<seu_email>/ no Google Drive.\r\nMantenha os nomes exatos: COLABORADORES.csv e HIERARQUIA.csv.\r\nSelecione no Paystore o tipo correspondente a cada arquivo.\r\nConsulte RESUMO_REVISAO.txt para o resumo das pendências e registros exportados.\r\n`);
  const url = URL.createObjectURL(await zip.generateAsync({ type: "blob", compression: "DEFLATE" })); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "CARGAS_SINCRONIZADOR_PAYTRACK.zip"; anchor.click(); URL.revokeObjectURL(url);
}
