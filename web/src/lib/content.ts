import "server-only";
import { supabaseServer } from "./supabase-server";
import { Stage, Template, ModuleInfo, Owner } from "@/data/types";

type StageRow = {
  id: string; order: number; title: string; short_description: string; owner: Owner;
  participants: string[] | null; sla: string | null; content: string[] | null; checklist: string[] | null;
  warnings: string[] | null; template_ids: string[] | null; module_ids: string[] | null;
};

function mapStage(row: StageRow): Stage {
  return {
    id: row.id,
    order: row.order,
    title: row.title,
    shortDescription: row.short_description,
    owner: row.owner,
    participants: row.participants && row.participants.length ? (row.participants as Owner[]) : undefined,
    sla: row.sla ?? undefined,
    content: row.content ?? [],
    checklist: row.checklist && row.checklist.length ? row.checklist : undefined,
    warnings: row.warnings && row.warnings.length ? row.warnings : undefined,
    templateIds: row.template_ids && row.template_ids.length ? row.template_ids : undefined,
    moduleIds: row.module_ids && row.module_ids.length ? row.module_ids : undefined,
  };
}

export async function getStages(segment: "sm" | "le"): Promise<Stage[]> {
  const { data, error } = await supabaseServer.from("process_stages").select("*").eq("segment", segment).order("order");
  if (error) throw new Error(error.message);
  return (data as StageRow[]).map(mapStage);
}

export async function getStage(segment: "sm" | "le", id: string): Promise<Stage | undefined> {
  const { data, error } = await supabaseServer.from("process_stages").select("*").eq("segment", segment).eq("id", id).maybeSingle();
  if (error) throw new Error(error.message);
  return data ? mapStage(data as StageRow) : undefined;
}

export async function getTemplates(): Promise<Template[]> {
  const { data, error } = await supabaseServer.from("process_templates").select("*").order("id");
  if (error) throw new Error(error.message);
  return (data ?? []).map((t) => ({ id: t.id as string, title: t.title as string, url: (t.url as string | null) ?? undefined }));
}

export async function getTemplate(id: string): Promise<Template | undefined> {
  const { data } = await supabaseServer.from("process_templates").select("*").eq("id", id).maybeSingle();
  return data ? { id: data.id as string, title: data.title as string, url: (data.url as string | null) ?? undefined } : undefined;
}

export async function getModules(): Promise<ModuleInfo[]> {
  const { data, error } = await supabaseServer.from("process_modules").select("*").order("id");
  if (error) throw new Error(error.message);
  return (data ?? []).map((m) => ({
    id: m.id as string,
    title: m.title as string,
    content: (m.content as string[] | null) ?? [],
    templateIds: (m.template_ids as string[] | null)?.length ? (m.template_ids as string[]) : undefined,
  }));
}

export async function getModule(id: string): Promise<ModuleInfo | undefined> {
  const { data } = await supabaseServer.from("process_modules").select("*").eq("id", id).maybeSingle();
  if (!data) return undefined;
  return {
    id: data.id as string,
    title: data.title as string,
    content: (data.content as string[] | null) ?? [],
    templateIds: (data.template_ids as string[] | null)?.length ? (data.template_ids as string[]) : undefined,
  };
}
