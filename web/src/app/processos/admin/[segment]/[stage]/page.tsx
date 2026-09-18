import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { auth } from "@/auth";
import { getStage } from "@/lib/content";
import { updateStage } from "@/lib/content-actions";

export default async function AdminStageEditPage({ params }: { params: Promise<{ segment: string; stage: string }> }) {
  const { segment, stage: stageId } = await params;
  if (segment !== "sm" && segment !== "le") notFound();

  const session = await auth();
  if (session?.user?.role !== "owner") redirect("/processos");

  const stage = await getStage(segment, stageId);
  if (!stage) notFound();

  const action = updateStage.bind(null, segment, stageId);

  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos/admin">Central de Implantação {">"} Administração</Link> {"> "}{stage.title}</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 6 }}>Editar etapa — {stage.title}</h1>
      <p style={{ marginBottom: 20 }}>Segmento {segment.toUpperCase()}, etapa {stage.order}. Salvar aqui atualiza a tela imediatamente para todo mundo.</p>

      <form action={action} className="ci-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>Título</div>
          <input name="title" defaultValue={stage.title} className="pattern" style={{ width: "100%" }} required />
        </label>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>Descrição curta</div>
          <input name="shortDescription" defaultValue={stage.shortDescription} className="pattern" style={{ width: "100%" }} />
        </label>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>SLA</div>
          <input name="sla" defaultValue={stage.sla ?? ""} className="pattern" style={{ width: "100%" }} placeholder="Ex.: 2 dias úteis" />
        </label>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>O que acontece nesta etapa (um parágrafo por linha)</div>
          <textarea name="content" defaultValue={stage.content.join("\n")} rows={6} className="pattern" style={{ width: "100%", fontFamily: "inherit" }} required />
        </label>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>Checklist (um item por linha)</div>
          <textarea name="checklist" defaultValue={(stage.checklist ?? []).join("\n")} rows={4} className="pattern" style={{ width: "100%", fontFamily: "inherit" }} />
        </label>
        <label>
          <div style={{ marginBottom: 6, fontWeight: 700, color: "var(--heading)" }}>Avisos / atenção (um por linha)</div>
          <textarea name="warnings" defaultValue={(stage.warnings ?? []).join("\n")} rows={3} className="pattern" style={{ width: "100%", fontFamily: "inherit" }} />
        </label>
        <div className="actions">
          <button type="submit" className="primary">Salvar alteração</button>
          <Link href={`/processos/${segment}/${stage.id}`} className="ci-nav-link" style={{ color: "var(--heading)", border: "1px solid var(--button-border)" }}>Ver etapa</Link>
        </div>
      </form>
    </>
  );
}
