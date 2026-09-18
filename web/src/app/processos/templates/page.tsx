import Link from "next/link";
import { templates } from "@/data/templates";

export default function TemplatesPage() {
  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Templates de e-mail</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 16 }}>Templates de e-mail</h1>
      <div className="ci-card">
        <ul>
          {templates.map((tpl) => (
            <li key={tpl.id}>{tpl.title}{!tpl.url && <span style={{ color: "var(--muted)" }}> — link a configurar</span>}</li>
          ))}
        </ul>
      </div>
    </>
  );
}
