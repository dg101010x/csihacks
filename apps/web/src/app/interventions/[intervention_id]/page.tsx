import { RouteStub } from "@/components/route-stub";

export default async function InterventionDetailPage({
  params,
}: {
  params: Promise<{ intervention_id: string }>;
}) {
  const { intervention_id } = await params;

  return (
    <RouteStub
      phase={`Route: /interventions/${intervention_id} — comparison and approval (Section 17, Phase C)`}
      title="Intervention comparison"
      description="OutcomeComparison, CostDisclosure, ApprovalRequirement, ConsumerApprovalPanel, AlternativeSelector (Section 21.5)."
    />
  );
}
