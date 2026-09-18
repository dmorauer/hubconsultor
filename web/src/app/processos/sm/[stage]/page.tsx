import StageDetail from "@/components/central-implantacao/StageDetail";

export default async function SmStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage } = await params;
  return <StageDetail segment="sm" stageId={stage} />;
}
