import { RouteStub } from "@/components/route-stub";

export default async function ProviderCasePage({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = await params;

  return (
    <RouteStub
      phase={`Route: /provider/cases/${case_id} — individual provider review (Section 17, Phase D)`}
      title="Case review"
      description="Consumer impact, provider impact, supporting provider rule, and approve / reject / request information actions (Section 16.2)."
    />
  );
}
