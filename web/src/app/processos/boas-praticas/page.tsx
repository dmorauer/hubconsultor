import Link from "next/link";

const praticas = [
  "Entendimento dos objetivos/dor do cliente",
  "Preocupação em repassar VALOR ao cliente além de usabilidade técnica",
  "Formalizações por e-mail",
  "Status report semanal",
  "Contato por WhatsApp",
  "Ligação",
];

export default function BoasPraticasPage() {
  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Boas práticas</nav>
      <h1 style={{ color: "var(--heading)", fontSize: 24, marginBottom: 16 }}>Boas práticas no atendimento e relacionamento com o cliente</h1>
      <div className="ci-card">
        <ul>{praticas.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
    </>
  );
}
