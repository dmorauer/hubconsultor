import { Template } from "./types";

// Nomes exatamente como documentados nos processos internos (LE/SM). Nenhuma URL foi
// inventada — quando o processo não traz um link utilizável, o template fica marcado
// como pendente de configuração.
export const templates: Template[] = [
  { id: "tpl-primeiro-contato-sm", title: "1. Template - Etapas de projeto SM - primeiro contato" },
  { id: "tpl-apresentacao-consultor-le", title: "Apresentação do Consultor LE" },
  { id: "tpl-cargas-expense", title: "Solicitação de cargas do Expense" },
  { id: "tpl-requisitos-travel", title: "[Projetos] Requisitos para implantação do Travel Tech" },
  { id: "tpl-implantacao-vcn", title: "[Projetos] Passo 1. Implantação VCN" },
  { id: "tpl-implantacao-cartao", title: "Implantação Paytrack Card" },
  { id: "tpl-carteira-digital", title: "[Projetos] Solicitação de documentos da Carteira Digital" },
  { id: "tpl-kickoff-formalizacao", title: "2. Template Etapa 1 - Formalização - Kick-off" },
  { id: "tpl-termo-escopo", title: "3. Template - Envio do Termo de escopo" },
  { id: "tpl-homologacao", title: "4. Template Etapa 3 - Homologação" },
  { id: "tpl-aceite-homologacao", title: "2. Template Etapa 3 - Aceite da Homologação" },
  { id: "tpl-treinamento-adm", title: "4.1 Template Etapa 3 - Homologação (Treinamento ADM)" },
  { id: "tpl-treinamento-usuarios", title: "4.2 Template Etapa 3 - Homologação (Formalização do Treinamento usuários)" },
  { id: "tpl-go-live", title: "5. Template etapa 4 - Go live" },
  { id: "tpl-status-report-atrasado", title: "Status Report ATRASADO" },
  { id: "tpl-status-report-reprogramado", title: "Status Report - Cronograma Reprogramado" },
  { id: "tpl-status-report-no-prazo", title: "Status Report - Cronograma no PRAZO" },
];

export function getTemplate(id: string): Template | undefined {
  return templates.find((t) => t.id === id);
}
