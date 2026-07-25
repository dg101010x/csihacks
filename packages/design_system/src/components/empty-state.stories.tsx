import type { Meta, StoryObj } from "@storybook/react";
import { Inbox } from "lucide-react";
import { EmptyState } from "./empty-state";
import { Button } from "./button";

const meta: Meta<typeof EmptyState> = {
  title: "Phase A/Empty state",
  component: EmptyState,
};
export default meta;
type Story = StoryObj<typeof EmptyState>;

export const NoInterventions: Story = {
  args: {
    icon: Inbox,
    title: "No interventions right now",
    description: "Relief hasn't detected an obligation collision for this household.",
  },
};

export const WithAction: Story = {
  args: {
    icon: Inbox,
    title: "No connected accounts",
    description: "Connect a Plaid Sandbox account or use the synthetic Wells Fargo demo data.",
    action: <Button size="sm">Connect an account</Button>,
  },
};
