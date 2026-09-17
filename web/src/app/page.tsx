"use client";

import { ChangeEvent, useMemo, useState } from "react";
import * as XLSX from "xlsx";

type LoadKey = "EMPLOYER" | "CUST" | "EXPENSES" | "USERS";
type LoadStatus = "Pronta" | "Com pendências" | "Sem registros";
const loads: Record<LoadKey, { label: string; expected: string[] }> = {
  EMPLOYER: { label: "Unidades de negócio", expected: ["CNPJ", "Nome"] },
  CUST: { label: "Centros de custo", expected: ["Código Centro de custo", "Nome centro de Custo"] },
  EXPENSES: { label: "Tipos de despesa", expected: ["Descrição", "Tipo"] },
  USERS: { label: "Usuários", expected: ["Nome", "CPF", "E-mail"] },
};
function normalized(value: unknown) { return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, ""); }
function locateSheet(names: string[], key: LoadKey) {
  const aliases: Record<LoadKey, string[]> = { EMPLOYER: ["empresas", "empresa", "unidades de negocio"], CUST: ["centros de custo", "centro de custo"], EXPENSES: ["tipos de despesa", "despesas"], USERS: ["colaboradores", "usuarios"] };
  return names.find((name) => aliases[key].includes(normalized(name)));
}
type Result = { key: LoadKey; sheet?: string; records: number; status: LoadStatus; pending: number; detail: string };

export default function Home() {
  const [fileName, setFileName] = useState(""); const [results, setResults] = useState<Result[]>([]); const [error, setError] = useState(""); const [analyzing, setAnalyzing] = useState(false);
  const summary = useMemo(() => results.reduce((total, item) => total + item.pending, 0), [results]);
  async function analyzeFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    setError(""); setAnalyzing(true); setFileName(file.name);
    try {
      const workbook = XLSX.read(await file.arrayBuffer(), { type: "array", cellDates: true });
      setResults((Object.keys(loads) as LoadKey[]).map((key) => {
        const sheet = locateSheet(workbook.SheetNames, key);
        if (!sheet) return { key, records: 0, status: "Sem registros" as const, pending: 0, detail: "Aba não encontrada na planilha." };
        const rows = XLSX.utils.sheet_to_json<unknown[]>(workbook.Sheets[sheet], { header: 1, defval: "" }); const [headers = [], ...data] = rows;
        const actual = headers.map(normalized); const missing = loads[key].expected.filter((header) => !actual.some((value) => value.includes(normalized(header))));
        const records = data.filter((row) => row.some((value) => String(value).trim())).length; const pending = missing.length + (records === 0 ? 1 : 0);
        return { key, sheet, records, pending, status: pending ? "Com pendências" as const : "Pronta" as const, detail: missing.length ? `Cabeçalho(s) a conferir: ${missing.join(", ")}.` : records ? "Estrutura inicial reconhecida." : "Aba sem registros." };
      }));
    } catch { setResults([]); setError("Não foi possível ler esta planilha. Envie um arquivo .xlsx válido."); } finally { setAnalyzing(false); }
  }
  return <main>
    <section className="hero"><span className="brand">PAYTRACK</span><h1>Validador de cargas</h1><p>Analise planilhas, revise pendências e prepare as cargas no padrão de importação.</p></section>
    <section className="upload-card"><div><h2>Planilha do cliente</h2><p>O arquivo é processado no navegador nesta versão. Ele não é armazenado.</p></div><label className="upload-button">{analyzing ? "Analisando…" : "Selecionar planilha .xlsx"}<input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={analyzeFile} disabled={analyzing} /></label></section>
    {error && <p className="error">{error}</p>}
    {results.length > 0 && <><section className="summary"><div><strong>{fileName}</strong><span>Arquivo em análise</span></div><div><strong>{summary}</strong><span>Pendências iniciais</span></div><div><strong>{results.filter((item) => item.status === "Pronta").length}</strong><span>Cargas prontas</span></div></section>
      <section className="table-card"><div className="table-title"><div><h2>Prontidão por carga</h2><p>Cada carga é avaliada separadamente.</p></div><span className="local">Processamento local</span></div><div className="table-scroll"><table><thead><tr><th>Carga</th><th>Aba encontrada</th><th>Registros</th><th>Prontidão</th><th>Pendências</th><th>Detalhes</th></tr></thead><tbody>{results.map((result) => <tr key={result.key}><td>{loads[result.key].label}</td><td>{result.sheet ?? "—"}</td><td>{result.records}</td><td><span className={`badge ${result.status === "Pronta" ? "ready" : "pending"}`}>{result.status}</span></td><td>{result.pending}</td><td>{result.detail}</td></tr>)}</tbody></table></div></section>
      <p className="notice">A migração web começou com a leitura local e a prontidão por carga. As regras de correção, revisão, exportação e sessão do aplicativo Python serão migradas para as próximas telas.</p></>}
  </main>;
}
