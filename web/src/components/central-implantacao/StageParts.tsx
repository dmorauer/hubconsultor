import Link from "next/link";
import { Owner, ownerLabels } from "@/data/types";
import { getTemplate, getModule } from "@/lib/content";

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

export async function TemplateList({ ids }: { ids: string[] }) {
  if (!ids.length) return null;
  const items = await Promise.all(ids.map(getTemplate));
  return (
    <div className="ci-card">
      <h2>Templates relacionados</h2>
      <ul>
        {items.map((template, index) => {
          if (!template) return null;
          return <li key={ids[index]}>{template.title}{!template.url && <span style={{ color: "var(--muted)" }}> — link a configurar</span>}</li>;
        })}
      </ul>
    </div>
  );
}

export async function ModuleChips({ ids }: { ids: string[] }) {
  if (!ids.length) return null;
  const items = await Promise.all(ids.map(getModule));
  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "0 0 20px" }}>
      {items.map((mod, index) => {
        if (!mod) return null;
        return <Link key={ids[index]} href={`/processos/modulos/${ids[index]}`} className="ci-module-chip">{mod.title}</Link>;
      })}
    </div>
  );
}
