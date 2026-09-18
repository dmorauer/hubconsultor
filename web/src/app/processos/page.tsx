"use client";

import { useState } from "react";
import AppHeader from "@/components/AppHeader";

type Segment = "LE" | "SM";

const emailModules = [
  { modulo: "Expense (cargas iniciais)", email: "Solicitação de cargas do Expense" },
  { modulo: "Travel", email: "[Projetos] Requisitos para implantação do Travel Tech" },
  { modulo: "VCN", email: "[Projetos] Passo 1. Implantação VCN" },
  { modulo: "Cartão Paytrack", email: "Implantação Paytrack Card" },
  { modulo: "Carteira Digital", email: "[Projetos] Solicitação de documentos da Carteira Digital" },
];

const implantacaoSteps = [
  { titulo: "Kick off", detalhe: "Com ou sem integração. Formalizar com o e-mail \"2. Template Etapa 1 - Formalização - Kick-off\"." },
  { titulo: "Definição de escopo / Termo de escopo", detalhe: "Registrar todo o escopo no Termo de escopo e disponibilizar para aceite na base de produção do cliente. O aceite é obrigatório para seguir com a parametrização. E-mail: \"3. Template - Envio do Termo de escopo\"." },
  { titulo: "Parametrização", detalhe: "" },
  { titulo: "Apresentação da ferramenta", detalhe: "" },
  { titulo: "Homologação assistida", detalhe: "Liberar o acesso à base para o cliente testar. E-mail: \"4. Template Etapa 3 - Homologação\"." },
  { titulo: "Retorno dos testes", detalhe: "" },
  { titulo: "Termo de homologação", detalhe: "O aceite é obrigatório para o go live do projeto. E-mail: \"2. Template Etapa 3 - Aceite da Homologação\"." },
  { titulo: "Treinamento de administrador", detalhe: "E-mail: \"4.1 Template Etapa 3 - Homologação (Treinamento ADM)\"." },
  { titulo: "Treinamento de usuários", detalhe: "E-mail: \"4.2 Template Etapa 3 - Homologação (Formalização do Treinamento usuários)\"." },
  { titulo: "Go live", detalhe: "Formalizado pelo GP, com o e-mail \"5. Template etapa 4 - Go live\"." },
];

const modulos = ["Expense", "Cartão Paytrack", "Carteira Digital", "Travel", "VCN", "Conciliação", "Integração D+1", "Integração financeira / RH"];

const integracao = ["Projeto novo com integração em primeira onda", "Projeto novo com integração em segunda onda", "Projeto de base", "Sprint", "Cronograma", "Reunião de briefing / alinhamento", "Reunião de escopo", "Requisitos técnicos", "Alocação na sprint"];

const boasPraticas = ["Entendimento dos objetivos/dor do cliente", "Preocupação em repassar VALOR ao cliente além de usabilidade técnica", "Formalizações por e-mail", "Status report semanal", "Contato por WhatsApp", "Ligação"];

export default function Processos() {
  const [segment, setSegment] = useState<Segment>("LE");

  return (
    <main>
      <AppHeader title="Processos internos" subtitle="Passo a passo do processo de implantação, por segmento de cliente." backHref="/" />

      <section className="upload-card">
        <div>
          <h2>Segmento</h2>
          <p>O fluxo muda conforme o segmento do cliente — escolha para ver as diferenças abaixo.</p>
        </div>
        <div className="actions">
          <button className={segment === "LE" ? "primary" : ""} onClick={() => setSegment("LE")}>LE — Large Enterprise</button>
          <button className={segment === "SM" ? "primary" : ""} onClick={() => setSegment("SM")}>SM — Small/Medium</button>
        </div>
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>1. Como recebo meus projetos?</h2></div></div>
        <p>Somos notificados do início do projeto de duas formas: atribuição no ticket do Hubspot, e e-mail enviado pela gestão nos apresentando ao cliente.</p>
        {segment === "SM" && <p>Quando o time de vendas finaliza uma venda, cria-se um ticket no Hubspot para que o cliente chegue ao time de implantação como projeto vendido. O gestor da área é notificado e atribui o projeto a um consultor e a um gerente de projetos.</p>}
        <p><strong>SLA de resposta ao e-mail de apresentação: 2 dias úteis.</strong> {segment === "LE" ? "No LE, o GP responde." : "No SM, o consultor responde."}</p>
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>2. Recebi meu projeto, e agora?</h2></div></div>
        {segment === "LE" ? (
          <>
            <p><strong>O GP irá:</strong> analisar a proposta comercial; agendar um alinhamento interno com o time de vendas; agendar um alinhamento inicial com o cliente; criar o cronograma; conduzir o kick off.</p>
            <p><strong>Quando começa a atuação do consultor?</strong> Após a execução do kick off, o GP sinaliza ao consultor para que agende a definição de escopo com o cliente e solicite as cargas. O consultor responde o e-mail de apresentação (&quot;Apresentação do Consultor LE&quot;), propondo a agenda de definição de escopo.</p>
          </>
        ) : (
          <>
            <p><strong>Proposta:</strong> analisar os módulos contratados (checar o check amarelo, exceto mobilidade — normalmente vem zerado); analisar as formas de pagamento do travel; analisar o prazo de vigência. Havendo divergência, seguir o processo de devolutiva comercial formalizado.</p>
            <p><strong>Hubspot:</strong> verificar as propriedades preenchidas pelo vendas para entender o objetivo do cliente, e as observações do card.</p>
            <p><strong>Repasse de vendas:</strong> reunião com o vendedor para entender o histórico da venda.</p>
            <p><strong>Primeiro contato com o cliente:</strong> e-mail padrão respondido em cima do e-mail da coordenação (&quot;1. Template - Etapas de projeto SM - primeiro contato&quot;), sugerindo a agenda de kick off.</p>
          </>
        )}
        <p><strong>Solicitar os requisitos de cada módulo</strong> (e-mails padrão):</p>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Módulo</th><th>E-mail padrão</th></tr></thead>
            <tbody>{emailModules.map((item) => <tr key={item.modulo}><td>{item.modulo}</td><td>{item.email}</td></tr>)}</tbody>
          </table>
        </div>
        <p>Criar uma pasta para o cliente no Drive onde devem ser armazenadas todas as cargas e documentações do projeto.</p>
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>3. Cronograma (Smartsheet)</h2></div></div>
        {segment === "LE" ? (
          <p>É responsabilidade do consultor concluir as atividades executadas durante o projeto no cronograma, facilitando o acompanhamento do GP e do cliente. Alterações de data / reprogramação de atividades devem ser feitas pelo gerente de projetos.</p>
        ) : (
          <>
            <p>Criar o cronograma assim que conseguir agendar o kick off. Atenção ao criar:</p>
            <ul>
              <li><strong>Time do projeto:</strong> sempre preencher coordenador, consultor e GP.</li>
              <li><strong>ID do Hubspot:</strong> obrigatório — é o que faz rodar a integração Smartsheet ↔ Hubspot.</li>
              <li><strong>Potencial travel:</strong> preencher com o volume de viagens do Hubspot (campo &quot;[TRVL] Soma de todos os potenciais de volume travel&quot;). Se vazio, preencher com zero e mapear o volume com o cliente durante o levantamento travel.</li>
              <li><strong>BU:</strong> conforme a segmentação do cliente no Hubspot — usado nos filtros do BI da gestão.</li>
              <li><strong>Variância:</strong> indicador de atraso do cronograma (ex.: go live previsto 04/02, reprogramado para 05/02 → variância &quot;-1&quot;). Ao criar um cronograma novo a partir do modelo, redefinir as &quot;Referências iniciais&quot; para zerar a variância antes de editar as datas.</li>
              <li><strong>Tipo de projeto:</strong> Novo (sem integração, ou integração na primeira onda) · Novo - Integração segunda onda (integração fora do cronograma inicial) · Base · Base - Segunda onda (serviço que ficou pendente para uma segunda onda).</li>
              <li><strong>Hubspot:</strong> mover o card para &quot;Em andamento&quot; após a reunião de kick off.</li>
            </ul>
            <p>O Smartsheet deve ser mantido atualizado pelo consultor às quintas-feiras; a coordenação valida os cronogramas na sexta-feira à tarde.</p>
          </>
        )}
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>4. Processo de implantação</h2></div></div>
        <div className="issue-groups">
          {implantacaoSteps.map((step, index) => (
            <details key={step.titulo}>
              <summary><span className="badge ready">{index + 1}</span><strong>{step.titulo}</strong></summary>
              {step.detalhe && <p>{step.detalhe}</p>}
            </details>
          ))}
        </div>
      </section>

      <section className="table-card">
        <div className="table-title"><div><h2>5. Processos de implantação por módulo / serviço</h2></div></div>
        <ul>{modulos.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>

      <section className="table-card">
        <div className="table-title"><div><h2>6. Processos de integração</h2></div></div>
        <ul>{integracao.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>7. Processos internos durante o projeto</h2></div></div>
        <p><strong>Observações no Hubspot:</strong> manter uma observação de histórico do projeto, com o detalhamento dos contatos com o cliente e das ações realizadas (ex.: &quot;04/12 - Kick off realizado&quot;, &quot;05/12 - Recebi as cargas preenchidas ...&quot;).</p>
        <p>Se o projeto tiver travel, é <strong>obrigatório</strong> manter a observação atualizada com:</p>
        <ul>
          <li><strong>Contrato:</strong> se já foi enviado ao cliente e se está assinado.</li>
          <li><strong>Aditivo:</strong> se o cliente usa cartão de crédito, se a foto já foi recebida e se o aditivo está pendente ou assinado.</li>
          <li><strong>Forma de pagamento:</strong> qual a forma de pagamento de cada serviço.</li>
          <li><strong>Locação:</strong> se utiliza locação de veículos e como está o acordo tripartite (ex.: &quot;Localiza: CNPJ 11.111.111/0001-11 - Acordo 55555&quot;).</li>
        </ul>
        {segment === "SM" && (
          <p><strong>Status Report:</strong> a agenda de segunda-feira do consultor fica reservada para atividades internas, incluindo o status report dos projetos. Modelos disponíveis no Hubspot: &quot;Status Report ATRASADO&quot;, &quot;Status Report - Cronograma Reprogramado&quot;, &quot;Status Report - Cronograma no PRAZO&quot;.</p>
        )}
      </section>

      <section className="table-card">
        <div className="table-title"><div><h2>8. Boas práticas no atendimento e relacionamento com cliente</h2></div></div>
        <ul>{boasPraticas.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>

      <section className="table-card review">
        <div className="table-title"><div><h2>9. E se meu projeto for de base?</h2></div></div>
        <ul>
          <li>Se for um módulo (cartão, carteira ou travel): seguir o processo de implantação normal do módulo.</li>
          <li>Se for integração: seguir o processo padrão de integração.</li>
          <li>Se for treinamento de administrador / usuário: agendar um alinhamento com o cliente <em>antes</em> de agendar o treinamento, para entender o que ele espera — e formalizar por e-mail os tópicos combinados.</li>
        </ul>
      </section>

      <footer className="app-footer">
        <span>Paytrack Center</span>
        <span>Baseado nos processos internos de implantação LE e SM.</span>
      </footer>
    </main>
  );
}
