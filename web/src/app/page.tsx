"use client";

import { ChangeEvent, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import { Conversion, exportDefaults, parseWorkbook } from "@/lib/conversion";

type LoadKey = "EMPLOYER" | "CUST" | "EXPENSES" | "USERS";
type User = { row: number; name: string; cpf: string; email: string; sexo: string; ativo: string };
type Fix = { id: string; row: number; field: keyof Pick<User, "cpf" | "sexo" | "ativo">; before: string; after: string; reason: string };
type Issue = { row: number; field: string; reason: string; severity: "Erro" | "Pendente" };
type History = { before: User[]; label: string };

const loads: Record<LoadKey, { label: string; aliases: string[] }> = {
  EMPLOYER: { label: "Unidades de negócio", aliases: ["empresas", "empresa", "unidades de negocio"] },
  CUST: { label: "Centros de custo", aliases: ["centros de custo", "centro de custo"] },
  EXPENSES: { label: "Tipos de despesa", aliases: ["tipos de despesa", "despesas"] },
  USERS: { label: "Usuários", aliases: ["colaboradores", "usuarios"] },
};
const norm = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const digits = (value: unknown) => String(value ?? "").replace(/\D/g, "");
const find = (headers: unknown[], label: string) => headers.findIndex((header) => norm(header).includes(norm(label)));
const valueAt = (row: unknown[], index: number) => index < 0 ? "" : String(row[index] ?? "").trim();

function normalizeSex(value: string) { const current = value.trim(); const first = current.charAt(0).toUpperCase(); return first === "M" || first === "F" ? first : current; }
function normalizeActive(value: string) { const current = value.trim(); if (!current) return "S"; return current.toUpperCase().startsWith("S") ? "S" : current.toUpperCase().startsWith("N") ? "N" : current; }
function validEmail(value: string) { return /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(value); }

export default function Home() {
  const [fileName, setFileName] = useState(""); const [loadRows, setLoadRows] = useState<Record<LoadKey, number>>({ EMPLOYER: 0, CUST: 0, EXPENSES: 0, USERS: 0 });
  const [users, setUsers] = useState<User[]>([]); const [history, setHistory] = useState<History[]>([]); const [error, setError] = useState(""); const [analyzing, setAnalyzing] = useState(false);
  const [conversion, setConversion] = useState<Conversion | null>(null); const [exporting, setExporting] = useState(false);
  const [integrationPattern, setIntegrationPattern] = useState("0.{EXTRAFRUTI}.1.{CASAFRUTI}");
  const fixes = useMemo<Fix[]>(() => users.flatMap((user) => {
    const proposal: Fix[] = []; const cpf = digits(user.cpf);
    if (cpf && cpf.length < 11) proposal.push({ id: `${user.row}-cpf`, row: user.row, field: "cpf", before: user.cpf, after: cpf.padStart(11, "0"), reason: "CPF será completado com zeros à esquerda." });
    const sexo = normalizeSex(user.sexo); if (sexo && sexo !== user.sexo) proposal.push({ id: `${user.row}-sexo`, row: user.row, field: "sexo", before: user.sexo, after: sexo, reason: "Sexo será normalizado para M ou F." });
    const ativo = normalizeActive(user.ativo); if (ativo !== user.ativo) proposal.push({ id: `${user.row}-ativo`, row: user.row, field: "ativo", before: user.ativo || "(vazio)", after: ativo, reason: "Ativo será normalizado para S ou N." });
    return proposal;
  }), [users]);
  const issues = useMemo<Issue[]>(() => {
    const repeated = new Set(users.filter((user) => user.email).map((user) => user.email.toLowerCase()).filter((email, _, all) => all.filter((current) => current === email).length > 1));
    return users.flatMap((user) => {
      const list: Issue[] = []; const cpf = digits(user.cpf);
      if (!user.name) list.push({ row: user.row, field: "Nome", reason: "Campo obrigatório vazio.", severity: "Pendente" });
      if (!cpf) list.push({ row: user.row, field: "CPF", reason: "Campo obrigatório vazio.", severity: "Pendente" });
      else if (cpf.length > 11) list.push({ row: user.row, field: "CPF", reason: "CPF possui mais de 11 dígitos; ele não será cortado.", severity: "Erro" });
      if (!user.email) list.push({ row: user.row, field: "E-mail", reason: "Campo obrigatório vazio.", severity: "Pendente" });
      else if (!validEmail(user.email)) list.push({ row: user.row, field: "E-mail", reason: "Formato de e-mail inválido.", severity: "Erro" });
      else if (repeated.has(user.email.toLowerCase())) list.push({ row: user.row, field: "E-mail", reason: "E-mail repetido. A sugestão precisa ser confirmada antes de alterar.", severity: "Erro" });
      if (user.sexo && !["M", "F"].includes(normalizeSex(user.sexo))) list.push({ row: user.row, field: "Sexo", reason: "Valor não identificado como M ou F.", severity: "Pendente" });
      return list;
    });
  }, [users]);

  async function analyzeFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return;
    setError(""); setAnalyzing(true); setFileName(file.name);
    try {
      const buffer = await file.arrayBuffer(); const workbook = XLSX.read(buffer, { type: "array" }); const nextConversion = parseWorkbook(buffer); const counts = { EMPLOYER: nextConversion.EMPLOYER.length, CUST: nextConversion.CUST.length, EXPENSES: nextConversion.EXPENSES.length, USERS: nextConversion.USERS.length };
      const userSheet = workbook.SheetNames.find((name) => loads.USERS.aliases.includes(norm(name))); if (!userSheet) throw new Error("Aba de Colaboradores não encontrada.");
      const rows = XLSX.utils.sheet_to_json<unknown[]>(workbook.Sheets[userSheet], { header: 1, defval: "" }); const [headers = [], ...data] = rows;
      const indexes = { name: find(headers, "Nome"), cpf: find(headers, "CPF"), email: find(headers, "E-mail"), sexo: find(headers, "Sexo"), ativo: find(headers, "Ativo") };
      if (indexes.name < 0 || indexes.cpf < 0 || indexes.email < 0) throw new Error("Aba de Colaboradores sem os cabeçalhos Nome, CPF e E-mail.");
      setLoadRows(counts); setConversion(nextConversion); setUsers(data.filter((row) => row.some((cell) => String(cell).trim())).map((row, index) => ({ row: index + 2, name: valueAt(row, indexes.name), cpf: valueAt(row, indexes.cpf), email: valueAt(row, indexes.email), sexo: valueAt(row, indexes.sexo), ativo: valueAt(row, indexes.ativo) }))); setHistory([]);
    } catch (caught) { setUsers([]); setError(caught instanceof Error ? caught.message : "Não foi possível ler esta planilha."); }
    finally { setAnalyzing(false); }
  }
  function applyFixes() { if (!fixes.length || !window.confirm(`Aplicar ${fixes.length} correção(ões) propostas?`)) return; setHistory((current) => [...current, { before: users, label: `${fixes.length} correção(ões) em lote` }]); setUsers((current) => current.map((user) => fixes.filter((fix) => fix.row === user.row).reduce((next, fix) => ({ ...next, [fix.field]: fix.after }), user))); }
  function undo() { const last = history.at(-1); if (!last) return; setUsers(last.before); setHistory((current) => current.slice(0, -1)); }
  const integrationRows = useMemo(() => (conversion?.USERS ?? []).flatMap((record) => { const extra = record.source["Código de integração Extrafruti"] ?? ""; const casa = record.source["Código de integração Casafruti"] ?? ""; if (!extra && !casa) return []; return [{ row: record.sourceRow, extra, casa, current: record.values[5], proposal: integrationPattern.replace("{EXTRAFRUTI}", extra).replace("{CASAFRUTI}", casa) }]; }), [conversion, integrationPattern]);
  function applyIntegrations() { if (!conversion || !integrationRows.length || !integrationPattern.includes("{")) return; if (!window.confirm(`Aplicar ${integrationRows.length} código(s) de integração com este formato?`)) return; setConversion((current) => { if (!current) return current; const next = structuredClone(current); integrationRows.forEach((proposal) => { const record = next.USERS.find((item) => item.sourceRow === proposal.row); if (record) record.values[5] = proposal.proposal; }); return next; }); }
  async function exportFiles() { if (!conversion || exporting) return; setExporting(true); try { const adjusted = structuredClone(conversion); adjusted.USERS.forEach((record) => { const user = users.find((item) => item.row === record.sourceRow); if (user) { record.values[1] = user.sexo; record.values[2] = user.cpf; record.values[6] = user.ativo; } }); await exportDefaults(adjusted); } catch (caught) { setError(caught instanceof Error ? caught.message : "Não foi possível exportar as cargas."); } finally { setExporting(false); } }
  const ready = Object.values(loadRows).filter(Boolean).length - Object.values(loadRows).filter((count) => count && (issues.length > 0)).length;

  return <main><section className="hero"><span className="brand">PAYTRACK</span><h1>Validador de cargas</h1><p>Analise planilhas, confira as sugestões e decida antes de exportar.</p></section>
    <section className="upload-card"><div><h2>Planilha do cliente</h2><p>O arquivo é processado somente no navegador e não é armazenado.</p></div><label className="upload-button">{analyzing ? "Analisando…" : "Selecionar planilha .xlsx"}<input type="file" accept=".xlsx" onChange={analyzeFile} disabled={analyzing} /></label></section>{error && <p className="error">{error}</p>}
    {users.length > 0 && <><section className="summary"><div><strong>{fileName}</strong><span>Arquivo em análise</span></div><div><strong>{issues.length}</strong><span>Erros e pendências</span></div><div><strong>{fixes.length}</strong><span>Correções propostas</span></div></section>
      <section className="table-card"><div className="table-title"><div><h2>Prontidão por carga</h2><p>Pendências em Usuários não bloqueiam a análise das outras cargas.</p></div><span className="local">Processamento local</span></div><div className="table-scroll"><table><thead><tr><th>Carga</th><th>Registros</th><th>Prontidão</th></tr></thead><tbody>{(Object.keys(loads) as LoadKey[]).map((key) => <tr key={key}><td>{loads[key].label}</td><td>{loadRows[key]}</td><td><span className={`badge ${loadRows[key] ? (key === "USERS" && issues.length ? "pending" : "ready") : "pending"}`}>{loadRows[key] ? (key === "USERS" && issues.length ? "Com pendências" : "Pronta") : "Sem registros"}</span></td></tr>)}</tbody></table></div></section>
      <section className="table-card review"><div className="table-title"><div><h2>Correções em lote</h2><p>Confira o antes e depois. Nenhuma correção é aplicada sem sua confirmação.</p></div><div className="actions"><button onClick={undo} disabled={!history.length}>Desfazer última</button><button className="primary" onClick={applyFixes} disabled={!fixes.length}>Aplicar {fixes.length} correções</button></div></div><div className="table-scroll"><table><thead><tr><th>Linha</th><th>Campo</th><th>Antes</th><th>Proposta</th><th>Motivo</th></tr></thead><tbody>{fixes.length ? fixes.map((fix) => <tr key={fix.id}><td>{fix.row}</td><td>{fix.field.toUpperCase()}</td><td>{fix.before}</td><td>{fix.after}</td><td>{fix.reason}</td></tr>) : <tr><td colSpan={5}>Não há normalizações pendentes.</td></tr>}</tbody></table></div></section>
      <section className="table-card review"><div className="table-title"><div><h2>Pendências</h2><p>Revise as informações antes de gerar a carga final.</p></div></div><div className="table-scroll"><table><thead><tr><th>Situação</th><th>Linha</th><th>Campo</th><th>Motivo</th></tr></thead><tbody>{issues.length ? issues.map((issue, index) => <tr key={`${issue.row}-${index}`}><td><span className={`badge ${issue.severity === "Erro" ? "danger" : "pending"}`}>{issue.severity}</span></td><td>{issue.row}</td><td>{issue.field}</td><td>{issue.reason}</td></tr>) : <tr><td colSpan={4}>Nenhuma pendência local em Usuários.</td></tr>}</tbody></table></div></section>
      {integrationRows.length > 0 && <section className="table-card review"><div className="table-title"><div><h2>Códigos de integração</h2><p>Defina o formato antes de preencher os códigos de origem Casafruti e Extrafruti.</p></div><div className="actions"><input className="pattern" value={integrationPattern} onChange={(event) => setIntegrationPattern(event.target.value)} /><button className="primary" onClick={applyIntegrations}>Aplicar sugestões</button></div></div><div className="table-scroll"><table><thead><tr><th>Linha</th><th>Extrafruti</th><th>Casafruti</th><th>Sugestão</th></tr></thead><tbody>{integrationRows.map((item) => <tr key={item.row}><td>{item.row}</td><td>{item.extra || "—"}</td><td>{item.casa || "—"}</td><td>{item.proposal}</td></tr>)}</tbody></table></div></section>}
      <section className="export-card"><div><h2>Exportar cargas</h2><p>Gera os quatro arquivos DEFAULT no navegador. As decisões feitas nesta tela ainda não são enviadas ao Paytrack.</p></div><button className="primary" onClick={exportFiles} disabled={exporting}>{exporting ? "Gerando arquivos…" : "Exportar DEFAULTs"}</button></section>
      {history.length > 0 && <p className="notice">Última decisão: {history.at(-1)?.label}. Você pode desfazê-la antes de trocar de planilha.</p>}</>}
  </main>;
}
