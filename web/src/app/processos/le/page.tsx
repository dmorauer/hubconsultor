import { redirect } from "next/navigation";
import { getStages } from "@/lib/content";

export default async function LeProcess() {
  const stages = await getStages("le");
  redirect(`/processos/le/${stages[0].id}`);
}
