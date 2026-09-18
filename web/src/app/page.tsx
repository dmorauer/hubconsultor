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
    title: "Processos internos",
    description: "Passo a passo do processo de implantação (LE e SM): recebimento do projeto, cronograma, homologação, go live e boas práticas.",
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
