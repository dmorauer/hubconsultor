import Link from "next/link";
import { getStages, getTemplates } from "@/lib/content";

export default async function CentralImplantacao() {
  const [smStages, leStages, templates] = await Promise.all([getStages("sm"), getStages("le"), getTemplates()]);

  return (
    <>
      <h1 style={{ color: "var(--heading)", fontSize: 30, marginBottom: 6 }}>Central de Implantação</h1>
      <p style={{ marginBottom: 26 }}>Processos, responsabilidades e materiais para conduzir implantações Paytrack.</p>

      <div className="ci-grid-2">
        <Link href="/processos/sm" className="ci-segment-card">
          <h2>Small &amp; Medium</h2>
          <p>Implantações conduzidas pelo consultor, do recebimento ao go live. {smStages.length} etapas mapeadas.</p>
          <span className="ci-owner-badge ci-owner-consultor">Acessar processo →</span>
        </Link>
        <Link href="/processos/le" className="ci-segment-card">
          <h2>Large Enterprise</h2>
          <p>Implantações com atuação conjunta entre Gerente de Projetos e Consultor. {leStages.length} etapas mapeadas.</p>
          <span className="ci-owner-badge ci-owner-gp">Acessar processo →</span>
        </Link>
      </div>

      <div className="ci-card">
        <h2>Atalhos</h2>
        <ul>
          <li><Link href="/processos/sm/recebimento">Como recebo meus projetos? (SM)</Link></li>
          <li><Link href="/processos/le/recebimento">Como recebo meus projetos? (LE)</Link></li>
          <li><Link href="/processos/templates">Templates de e-mail ({templates.length})</Link></li>
          <li><Link href="/processos/boas-praticas">Boas práticas no atendimento</Link></li>
        </ul>
      </div>
    </>
  );
}
