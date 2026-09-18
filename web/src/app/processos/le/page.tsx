import Link from "next/link";

export default function LeProcess() {
  return (
    <>
      <nav className="ci-breadcrumb"><Link href="/processos">Central de Implantação</Link> {"> "}Large Enterprise</nav>
      <div className="ci-card">
        <h2>Large Enterprise — em construção</h2>
        <p>O processo LE (Large Enterprise) tem uma divisão de responsabilidades diferente do SM: o Gerente de Projetos conduz a proposta, o alinhamento inicial e o kick off, e só depois faz o handoff para o consultor.</p>
        <p>Essa etapa da Central de Implantação ainda não foi construída — o processo <Link href="/processos/sm">Small &amp; Medium</Link> já está disponível.</p>
      </div>
    </>
  );
}
