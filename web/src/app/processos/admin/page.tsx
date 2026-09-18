import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { getStages, getTemplates, getModules } from "@/lib/content";

export default async function AdminPage() {
  const session = await auth();
  if (session?.user?.role !== "owner") redirect("/processos");

  const [smStages, leStages, templates, modules] = await Promise.all([getStages("sm"), getStages("le"), getTemplates(), getModules()]);

  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Administração</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 6 }}>Gerenciar conteúdo</h1>
      <p style={{ marginBottom: 20 }}>Visível só para a conta owner. O conteúdo abaixo já vem do Supabase — editar aqui atualiza o que todo mundo vê, sem precisar de deploy.</p>

      <div className="ci-card">
        <h2>Etapas — Small &amp; Medium</h2>
        <ul>
          {smStages.map((stage) => <li key={stage.id}>{stage.order}. {stage.title} — <Link href={`/processos/admin/sm/${stage.id}`}>Editar</Link></li>)}
        </ul>
      </div>

      <div className="ci-card">
        <h2>Etapas — Large Enterprise</h2>
        <ul>
          {leStages.map((stage) => <li key={stage.id}>{stage.order}. {stage.title} — <Link href={`/processos/admin/le/${stage.id}`}>Editar</Link></li>)}
        </ul>
      </div>

      <div className="ci-card">
        <h2>Templates de e-mail ({templates.length}) e módulos ({modules.length})</h2>
        <p>Ainda não editáveis pela interface — só as etapas, por enquanto.</p>
      </div>
    </>
  );
}
