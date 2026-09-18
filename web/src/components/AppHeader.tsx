"use client";

import Link from "next/link";
import { signOut } from "next-auth/react";
import { useEffect, useState } from "react";

type AppHeaderProps = {
  title: string;
  subtitle: string;
  backHref?: string;
  backLabel?: string;
};

export default function AppHeader({ title, subtitle, backHref, backLabel }: AppHeaderProps) {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch { /* localStorage unavailable */ }
  }

  return (
    <section className="hero">
      <div className="hero-content">
        <span className="brand">PAYTRACK CENTER</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="hero-actions">
        {backHref && <Link className="back-button" href={backHref}>{backLabel ?? "← Início"}</Link>}
        <button className="theme-toggle" onClick={toggleTheme} aria-label="Alternar tema claro/escuro">{theme === "dark" ? "Claro" : "Escuro"}</button>
        <button className="logout-button" onClick={() => signOut({ callbackUrl: "/login" })}>Sair</button>
      </div>
    </section>
  );
}
