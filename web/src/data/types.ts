export type Owner = "consultor" | "gp" | "cliente" | "vendas" | "coordenacao";
export type Segment = "sm" | "le";

export type Stage = {
  id: string;
  order: number;
  title: string;
  shortDescription: string;
  owner: Owner;
  participants?: Owner[];
  sla?: string;
  content: string[];
  checklist?: string[];
  warnings?: string[];
  templateIds?: string[];
  moduleIds?: string[];
};

export type Template = { id: string; title: string; url?: string };
export type ModuleInfo = { id: string; title: string; content: string[]; templateIds?: string[] };

export const ownerLabels: Record<Owner, string> = {
  consultor: "Consultor",
  gp: "Gerente de Projetos",
  cliente: "Cliente",
  vendas: "Vendas",
  coordenacao: "Coordenação",
};
