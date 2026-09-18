import StageDetail from "@/components/central-implantacao/StageDetail";

export default async function LeStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage } = await params;
  return <StageDetail segment="le" stageId={stage} />;
}
