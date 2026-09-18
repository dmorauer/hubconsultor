"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { smStages } from "@/data/sm-process";
import { leStages } from "@/data/le-process";

const modules = [
  { id: "expense", title: "Expense" },
  { id: "travel", title: "Travel" },
  { id: "vcn", title: "VCN" },
  { id: "cartao-paytrack", title: "Cartão Paytrack" },
  { id: "carteira-digital", title: "Carteira Digital" },
  { id: "integracoes", title: "Integrações" },
];

export default function Sidebar({ isOwner }: { isOwner: boolean }) {
  const pathname = usePathname();
  const segment: "sm" | "le" | null = pathname.startsWith("/processos/sm") ? "sm" : pathname.startsWith("/processos/le") ? "le" : null;

  return (
    <aside className="ci-sidebar">
      <div className="ci-brand">Central de Implantação</div>
      <Link href="/" className="ci-nav-link">← Início do portal</Link>
      <Link href="/processos" className={`ci-nav-link ${pathname === "/processos" ? "active" : ""}`}>Visão geral</Link>

      <div className="ci-nav-label">Processos</div>
      <Link href="/processos/sm" className={`ci-nav-link ${segment === "sm" ? "active" : ""}`}>Small &amp; Medium</Link>
      <Link href="/processos/le" className={`ci-nav-link ${segment === "le" ? "active" : ""}`}>Large Enterprise</Link>

      {segment === "sm" && (
        <>
          <div className="ci-nav-label">Etapas</div>
          {smStages.map((stage) => (
            <Link key={stage.id} href={`/processos/sm/${stage.id}`} className={`ci-nav-link ${pathname === `/processos/sm/${stage.id}` ? "active" : ""}`}>
              {stage.order}. {stage.title}
            </Link>
          ))}
        </>
      )}
      {segment === "le" && (
        <>
          <div className="ci-nav-label">Etapas</div>
          {leStages.map((stage) => (
            <Link key={stage.id} href={`/processos/le/${stage.id}`} className={`ci-nav-link ${pathname === `/processos/le/${stage.id}` ? "active" : ""}`}>
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
