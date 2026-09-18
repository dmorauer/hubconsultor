import { ModuleInfo } from "./types";

export const modules: ModuleInfo[] = [
  {
    id: "expense",
    title: "Expense",
    content: ["Solicitar as cargas iniciais do cliente com o e-mail padrão de solicitação de cargas."],
    templateIds: ["tpl-cargas-expense"],
  },
  {
    id: "travel",
    title: "Travel",
    content: [
      "Solicitar os requisitos com o e-mail padrão de implantação do Travel Tech.",
      "No SM, o formulário de requisitos é enviado pelo HubSpot: selecionar o contato e preencher o \"Papel do contato\" (ex.: responsável pela implantação) e a \"Data para disparo da pesquisa\".",
      "Se o projeto tiver Travel, é obrigatório manter uma observação atualizada no HubSpot com o status de: Contrato (enviado/assinado), Aditivo (se o cliente usa cartão de crédito — foto recebida e aditivo assinado), Forma de pagamento (por serviço) e Locação (se utiliza e como está o acordo tripartite).",
    ],
    templateIds: ["tpl-requisitos-travel"],
  },
  {
    id: "vcn",
    title: "VCN",
    content: ["Solicitar os requisitos com o e-mail padrão \"Passo 1. Implantação VCN\"."],
    templateIds: ["tpl-implantacao-vcn"],
  },
  {
    id: "cartao-paytrack",
    title: "Cartão Paytrack",
    content: ["Solicitar os requisitos com o e-mail padrão de implantação do Paytrack Card."],
    templateIds: ["tpl-implantacao-cartao"],
  },
  {
    id: "carteira-digital",
    title: "Carteira Digital",
    content: ["Solicitar os documentos necessários com o e-mail padrão de solicitação de documentos da Carteira Digital."],
    templateIds: ["tpl-carteira-digital"],
  },
  {
    id: "conciliacao",
    title: "Conciliação",
    content: ["Módulo de conciliação, implantado seguindo o processo padrão do serviço contratado."],
  },
  {
    id: "integracoes",
    title: "Integrações",
    content: [
      "Tipos de condução documentados: projeto novo com integração em primeira onda; projeto novo com integração em segunda onda; projeto de base.",
      "Etapas internas: sprint, cronograma, reunião de briefing/alinhamento, reunião de escopo, levantamento de requisitos técnicos e alocação na sprint.",
    ],
  },
];

export function getModule(id: string): ModuleInfo | undefined {
  return modules.find((m) => m.id === id);
}
