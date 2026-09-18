import { redirect } from "next/navigation";
import { smStages } from "@/data/sm-process";

export default function SmProcess() {
  redirect(`/processos/sm/${smStages[0].id}`);
}
