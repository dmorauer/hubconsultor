import Link from "next/link";
import { notFound } from "next/navigation";
import { leStages, getLeStage } from "@/data/le-process";
import Timeline from "@/components/central-implantacao/Timeline";
import { ChecklistCard, ModuleChips, OwnerBadge, TemplateList, WarningCard } from "@/components/central-implantacao/StageParts";

export default async function LeStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage: stageId } = await params;
  const stage = getLeStage(stageId);
  if (!stage) notFound();

  const index = leStages.findIndex((s) => s.id === stage.id);
  const previous = leStages[index - 1];
  const next = leStages[index + 1];

  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}<Link href="/processos/le">Large Enterprise</Link></nav>
      <h1 style={{ color: "var(--heading)", fontSize: 26, marginBottom: 4 }}>Processo de Implantação — Large Enterprise</h1>
      <p style={{ marginBottom: 20 }}>O Gerente de Projetos conduz proposta, alinhamento e kick off; depois do handoff, o consultor assume a condução com o cliente.</p>

      <Timeline stages={leStages} activeId={stage.id} basePath="/processos/le" />

      <div className="ci-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div>
          <span className={`ci-owner-badge ci-owner-${stage.owner}`} style={{ marginBottom: 8, display: "inline-block" }}>{stage.order}</span>
          <h2 style={{ margin: "4px 0" }}>{stage.title}</h2>
          <p style={{ margin: 0 }}>{stage.shortDescription}</p>
        </div>
        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          {previous ? <Link href={`/processos/le/${previous.id}`} className="ci-nav-link" style={{ color: "var(--heading)", border: "1px solid var(--button-border)" }}>← Etapa anterior</Link> : <span />}
          {next && <Link href={`/processos/le/${next.id}`} className="ci-nav-link" style={{ background: "var(--yellow)", color: "var(--navy-deep)", fontWeight: 800 }}>Próxima etapa →</Link>}
        </div>
      </div>

      <div className="ci-grid-2">
        <div className="ci-card">
          <h2>O que acontece nesta etapa?</h2>
          {stage.content.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
        </div>
        {stage.checklist && <ChecklistCard items={stage.checklist} />}
      </div>

      <div className="ci-grid-2">
        <div className="ci-card">
          <h2>Responsável</h2>
          <p><OwnerBadge owner={stage.owner} /></p>
          {stage.participants && stage.participants.length > 0 && (
            <>
              <p style={{ marginBottom: 6 }}>Participantes:</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {stage.participants.map((p) => <OwnerBadge key={p} owner={p} />)}
              </div>
            </>
          )}
          {stage.sla && <p style={{ marginTop: 14 }}><strong style={{ color: "var(--heading)" }}>SLA:</strong> {stage.sla}</p>}
        </div>
        {stage.warnings && stage.warnings.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {stage.warnings.map((w, i) => <WarningCard key={i} text={w} />)}
          </div>
        )}
      </div>

      {stage.moduleIds && <ModuleChips ids={stage.moduleIds} />}
      {stage.templateIds && <TemplateList ids={stage.templateIds} />}
    </>
  );
}
