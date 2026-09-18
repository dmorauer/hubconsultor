"use client";

import Link from "next/link";
import { signOut } from "next-auth/react";

type AppHeaderProps = {
  title: string;
  subtitle: string;
  backHref?: string;
  backLabel?: string;
};

export default function AppHeader({ title, subtitle, backHref, backLabel }: AppHeaderProps) {
  return (
    <section className="hero">
      <div className="hero-content">
        <span className="brand">PAYTRACK CENTER</span>
        {backHref && <Link className="back-link" href={backHref}>{backLabel ?? "← Início"}</Link>}
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <button className="logout-button" onClick={() => signOut({ callbackUrl: "/login" })}>Sair</button>
    </section>
  );
}
