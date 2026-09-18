import { redirect } from "next/navigation";
import { getStages } from "@/lib/content";

export default async function SmProcess() {
  const stages = await getStages("sm");
  redirect(`/processos/sm/${stages[0].id}`);
}
