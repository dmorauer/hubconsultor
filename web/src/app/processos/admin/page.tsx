import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { smStages } from "@/data/sm-process";
import { leStages } from "@/data/le-process";
import { templates } from "@/data/templates";
import { modules } from "@/data/modules";

export default async function AdminPage() {
  const session = await auth();
  if (session?.user?.role !== "owner") redirect("/processos");

  const sections = [
    { title: "Etapas — Small & Medium", count: smStages.length, href: "/processos/sm" },
    { title: "Etapas — Large Enterprise", count: leStages.length, href: "/processos/le" },
    { title: "Templates de e-mail", count: templates.length, href: "/processos/templates" },
    { title: "Módulos", count: modules.length, href: "/processos/modulos/expense" },
  ];

  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Administração</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 6 }}>Gerenciar conteúdo</h1>
      <p style={{ marginBottom: 20 }}>Visível só para a conta owner. Aqui é onde as telas da Central de Implantação vão passar a ser editáveis.</p>

      <div className="ci-warning" style={{ marginBottom: 20 }}>
        <strong>Ainda não editável</strong>
        Hoje o conteúdo abaixo vem de arquivos em <code>web/src/data/</code>, versionados no código — não existe edição pela interface ainda. Para isso funcionar de verdade (editar e salvar sem precisar de deploy), falta criar uma tabela no Supabase e trocar essas páginas para ler de lá. Essa é a próxima etapa, se você quiser seguir.
      </div>

      <div className="ci-card">
        <h2>Conteúdo mapeado</h2>
        <ul>
          {sections.map((section) => (
            <li key={section.title}><Link href={section.href}>{section.title}</Link> — {section.count} itens</li>
          ))}
        </ul>
      </div>
    </>
  );
}
