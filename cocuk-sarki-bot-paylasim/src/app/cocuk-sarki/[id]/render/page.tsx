import { ProductionWorkspace } from "@/components/project/production-workspace";

type PageProps = { params: Promise<{ id: string }> };

export default async function ProductionPage({ params }: PageProps) {
  const { id } = await params;
  return <ProductionWorkspace projectId={id} />;
}
