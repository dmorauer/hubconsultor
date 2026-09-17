import * as XLSX from "xlsx";

export type Kind = "EMPLOYER" | "CUST" | "EXPENSES" | "USERS";
export type RecordRow = { sourceRow: number; values: string[]; source: Record<string, string> };
export type Conversion = Record<Kind, RecordRow[]>;

const definitions: Record<Kind, { sheet: string; required: string[]; width: number }> = {
  EMPLOYER: { sheet: "Empresas", required: ["Nome", "CNPJ"], width: 14 },
  CUST: { sheet: "Centros de Custo", required: ["Código Centro de custo", "Nome centro de Custo"], width: 5 },
  EXPENSES: { sheet: "Tipos de Despesa", required: ["Nome da Despesa"], width: 6 },
  USERS: { sheet: "Colaboradores", required: ["Nome completo", "CPF", "E-mail", "Ativo (S ou N)"], width: 23 },
};
export const labels: Record<Kind, string> = { EMPLOYER: "Unidades de negócio", CUST: "Centros de custo", EXPENSES: "Tipos de despesa", USERS: "Usuários" };

const norm = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const text = (value: unknown) => String(value ?? "").trim();
const digits = (value: unknown) => text(value).replace(/\D/g, "");
const yesNo = (value: unknown) => { const v = text(value).toUpperCase(); return v === "SIM" ? "S" : v === "NÃO" || v === "NAO" ? "N" : v; };
const document = (value: unknown, length: number) => { const valueDigits = digits(value); return valueDigits ? valueDigits.padStart(length, "0") : ""; };

function value(headers: unknown[], row: unknown[], label: string) {
  const index = headers.findIndex((header) => norm(header) === norm(label));
  return index < 0 ? "" : text(row[index]);
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
      if (kind === "EMPLOYER") values = [value(headers,row,"Nome"), document(value(headers,row,"CNPJ"),14), value(headers,row,"Nome para contato"), value(headers,row,"Telefone"), value(headers,row,"E-mail"), value(headers,row,"Moeda (BRL, EUR, USD)"), value(headers,row,"Código de integração"), "", "", "", "", "", "", digits(value(headers,row,"CEP")), value(headers,row,"Logradouro"), value(headers,row,"Número"), value(headers,row,"Bairro"), value(headers,row,"Cidade"), value(headers,row,"Estado"), value(headers,row,"País")];
      else if (kind === "CUST") values = ["", value(headers,row,"Código Centro de custo"), value(headers,row,"Nome centro de Custo"), "", value(headers,row,"Empresa(CNPJ)")];
      else if (kind === "EXPENSES") values = ["", value(headers,row,"Nome da Despesa"), "", "", "", value(headers,row,"Item de Orçamento"), "", "", "", "", "", "", "", "", "", ""];
      else values = [value(headers,row,"Nome completo"), value(headers,row,"Sexo (M ou F)"), document(value(headers,row,"CPF"),11), value(headers,row,"E-mail"), value(headers,row,"Data de nascimento"), value(headers,row,"Código de integração"), yesNo(value(headers,row,"Ativo (S ou N)")), value(headers,row,"Usuário"), value(headers,row,"Senha"), value(headers,row,"Empresa (CNPJ)"), value(headers,row,"Centro de custo (Cód. no ERP)"), value(headers,row,"Descrição centro de custo"), "", ""];
      return [{ sourceRow: index + 2, values, source }];
    });
  });
  return result;
}

export async function exportDefaults(conversion: Conversion) {
  for (const kind of Object.keys(definitions) as Kind[]) {
    const response = await fetch(`/DEFAULT_${kind}.xlsx`); if (!response.ok) throw new Error(`Modelo DEFAULT_${kind}.xlsx não encontrado.`);
    const workbook = XLSX.read(await response.arrayBuffer(), { type: "array" }); const worksheet = workbook.Sheets[workbook.SheetNames[0]];
    conversion[kind].forEach((record, index) => record.values.forEach((cell, column) => { if (cell) XLSX.utils.sheet_add_aoa(worksheet, [[cell]], { origin: { r: index + 1, c: column } }); }));
    XLSX.writeFile(workbook, `DEFAULT_${kind}.xlsx`, { bookType: "xlsx", compression: true });
  }
}
