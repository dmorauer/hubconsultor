import Link from "next/link";
import AppHeader from "@/components/AppHeader";

const menu = [
  {
    href: "/implantacao",
    title: "Implantação",
    description: "Validador de cargas: analise planilhas de clientes, revise sugestões e exporte para o Paytrack ou para o Sincronizador.",
  },
  {
    href: "/processos",
    title: "Central de Implantação",
    description: "Portal interativo do processo de implantação (Small & Medium e Large Enterprise): etapas, responsáveis, checklists, módulos e templates.",
  },
];

export default function Home() {
  return (
    <main>
      <AppHeader title="Bem-vindo(a)" subtitle="Escolha uma área para começar." />
      <section className="menu-grid">
        {menu.map((item) => (
          <Link key={item.href} href={item.href} className="menu-card">
            <h2>{item.title}</h2>
            <p>{item.description}</p>
          </Link>
        ))}
      </section>
      <footer className="app-footer">
        <span>Paytrack Center</span>
        <span>Portal interno para consultores de implantação.</span>
      </footer>
    </main>
  );
}
