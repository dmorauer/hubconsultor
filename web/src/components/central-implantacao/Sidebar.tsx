"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Stage, ModuleInfo } from "@/data/types";

export default function Sidebar({ isOwner, smStages, leStages, modules }: { isOwner: boolean; smStages: Stage[]; leStages: Stage[]; modules: ModuleInfo[] }) {
  const pathname = usePathname();
  const segment: "sm" | "le" | null = pathname.startsWith("/processos/sm") ? "sm" : pathname.startsWith("/processos/le") ? "le" : null;
  const stages = segment === "sm" ? smStages : segment === "le" ? leStages : [];

  return (
    <aside className="ci-sidebar">
      <div className="ci-brand">Central de Implantação</div>
      <Link href="/" className="ci-nav-link">← Início do portal</Link>
      <Link href="/processos" className={`ci-nav-link ${pathname === "/processos" ? "active" : ""}`}>Visão geral</Link>

      <div className="ci-nav-label">Processos</div>
      <Link href="/processos/sm" className={`ci-nav-link ${segment === "sm" ? "active" : ""}`}>Small &amp; Medium</Link>
      <Link href="/processos/le" className={`ci-nav-link ${segment === "le" ? "active" : ""}`}>Large Enterprise</Link>

      {segment && stages.length > 0 && (
        <>
          <div className="ci-nav-label">Etapas</div>
          {stages.map((stage) => (
            <Link key={stage.id} href={`/processos/${segment}/${stage.id}`} className={`ci-nav-link ${pathname === `/processos/${segment}/${stage.id}` ? "active" : ""}`}>
              {stage.order}. {stage.title}
            </Link>
          ))}
        </>
      )}

      <div className="ci-nav-label">Módulos</div>
      {modules.map((mod) => (
        <Link key={mod.id} href={`/processos/modulos/${mod.id}`} className={`ci-nav-link ${pathname === `/processos/modulos/${mod.id}` ? "active" : ""}`}>{mod.title}</Link>
      ))}

      <div className="ci-nav-label">Recursos</div>
      <Link href="/processos/templates" className={`ci-nav-link ${pathname === "/processos/templates" ? "active" : ""}`}>Templates de e-mail</Link>
      <Link href="/processos/boas-praticas" className={`ci-nav-link ${pathname === "/processos/boas-praticas" ? "active" : ""}`}>Boas práticas</Link>

      {isOwner && (
        <>
          <div className="ci-nav-label">Administração</div>
          <Link href="/processos/admin" className={`ci-nav-link ${pathname.startsWith("/processos/admin") ? "active" : ""}`}>Gerenciar conteúdo</Link>
        </>
      )}
    </aside>
  );
}
