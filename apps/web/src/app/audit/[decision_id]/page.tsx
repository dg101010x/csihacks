import { RouteStub } from "@/components/route-stub";

export default async function AuditReplayPage({
  params,
}: {
  params: Promise<{ decision_id: string }>;
}) {
  const { decision_id } = await params;

  return (
    <RouteStub
      phase={`Route: /audit/${decision_id} — immutable decision replay (Section 17, Phase E)`}
      title="Audit replay"
      description="AuditTimeline, InputSnapshotViewer, ForecastMetadata, CandidateActionViewer, RejectedActionViewer, ApprovalHistory, ReplayControls (Section 21.7). Replay must not modify the original case (Section 86)."
    />
  );
}
