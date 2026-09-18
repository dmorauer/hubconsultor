"use server";

import { revalidatePath } from "next/cache";
import { auth } from "@/auth";
import { supabaseServer } from "./supabase-server";

async function requireOwner() {
  const session = await auth();
  if (session?.user?.role !== "owner") throw new Error("Ação restrita à conta owner.");
}

function linesToArray(value: string): string[] {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

export async function updateStage(segment: "sm" | "le", id: string, formData: FormData) {
  await requireOwner();

  const title = String(formData.get("title") ?? "").trim();
  const shortDescription = String(formData.get("shortDescription") ?? "").trim();
  const sla = String(formData.get("sla") ?? "").trim();
  const content = linesToArray(String(formData.get("content") ?? ""));
  const checklist = linesToArray(String(formData.get("checklist") ?? ""));
  const warnings = linesToArray(String(formData.get("warnings") ?? ""));

  if (!title || !content.length) throw new Error("Título e descrição da etapa são obrigatórios.");

  const { error } = await supabaseServer
    .from("process_stages")
    .update({
      title,
      short_description: shortDescription,
      sla: sla || null,
      content,
      checklist,
      warnings,
    })
    .eq("segment", segment)
    .eq("id", id);

  if (error) throw new Error(error.message);

  revalidatePath(`/processos/${segment}/${id}`);
  revalidatePath(`/processos/admin/${segment}/${id}`);
}
