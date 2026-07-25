import type { Meta, StoryObj } from "@storybook/react";
import { StatusBadge } from "./status-badge";
import { createStatusDescriptor } from "../accessibility";

const meta: Meta = {
  title: "Phase A/Status indicators",
};
export default meta;
type Story = StoryObj;

export const AllTones: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <StatusBadge descriptor={createStatusDescriptor({ tone: "neutral", label: "Awaiting review", icon: "circle" })} />
      <StatusBadge descriptor={createStatusDescriptor({ tone: "positive", label: "Confirmed improvement", icon: "check-circle" })} />
      <StatusBadge descriptor={createStatusDescriptor({ tone: "caution", label: "Upcoming uncertainty", icon: "alert-triangle" })} />
      <StatusBadge descriptor={createStatusDescriptor({ tone: "risk", label: "Reserve violation projected", icon: "alert-octagon" })} />
    </div>
  ),
};

export const ApprovalProbabilityUnavailable: Story = {
  name: "Approval likelihood unavailable (Section 21.4)",
  render: () => (
    <StatusBadge
      descriptor={createStatusDescriptor({ tone: "neutral", label: "Approval likelihood unavailable", icon: "circle" })}
    />
  ),
};
