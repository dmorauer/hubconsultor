import Link from "next/link";
import { Owner, ownerLabels } from "@/data/types";
import { getTemplate } from "@/data/templates";
import { getModule } from "@/data/modules";

export function OwnerBadge({ owner }: { owner: Owner }) {
  return <span className={`ci-owner-badge ci-owner-${owner}`}>{ownerLabels[owner]}</span>;
}

export function ChecklistCard({ items }: { items: string[] }) {
  return (
    <div className="ci-card">
      <h2>Checklist desta etapa</h2>
      <div className="ci-checklist">
        {items.map((item) => (
          <label key={item}><input type="checkbox" disabled /> {item}</label>
        ))}
      </div>
    </div>
  );
}

export function WarningCard({ text }: { text: string }) {
  return (
    <div className="ci-warning">
      <strong>Atenção</strong>
      {text}
    </div>
  );
}

export function TemplateList({ ids }: { ids: string[] }) {
  if (!ids.length) return null;
  return (
    <div className="ci-card">
      <h2>Templates relacionados</h2>
      <ul>
        {ids.map((id) => {
          const template = getTemplate(id);
          if (!template) return null;
          return <li key={id}>{template.title}{!template.url && <span style={{ color: "var(--muted)" }}> — link a configurar</span>}</li>;
        })}
      </ul>
    </div>
  );
}

export function ModuleChips({ ids }: { ids: string[] }) {
  if (!ids.length) return null;
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "0 0 20px" }}>
      {ids.map((id) => {
        const mod = getModule(id);
        if (!mod) return null;
        return <Link key={id} href={`/processos/modulos/${id}`} className="ci-module-chip">{mod.title}</Link>;
      })}
    </div>
  );
}
