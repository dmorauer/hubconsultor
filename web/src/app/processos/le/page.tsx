import { redirect } from "next/navigation";
import { leStages } from "@/data/le-process";

export default function LeProcess() {
  redirect(`/processos/le/${leStages[0].id}`);
}
