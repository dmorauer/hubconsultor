import Link from "next/link";
import { notFound } from "next/navigation";
import { getModule } from "@/data/modules";
import { TemplateList } from "@/components/central-implantacao/StageParts";

export default async function ModulePage({ params }: { params: Promise<{ modulo: string }> }) {
  const { modulo } = await params;
  const mod = getModule(modulo);
  if (!mod) notFound();

  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Módulos {"> "}{mod.title}</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 16 }}>{mod.title}</h1>
      <div className="ci-card">
        <h2>O que saber</h2>
        {mod.content.map((paragraph, i) => <p key={i}>{paragraph}</p>)}
      </div>
      {mod.templateIds && <TemplateList ids={mod.templateIds} />}
    </>
  );
}
