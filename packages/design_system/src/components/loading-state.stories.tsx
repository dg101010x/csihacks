import type { Meta, StoryObj } from "@storybook/react";
import { LoadingState } from "./loading-state";
import { Skeleton } from "./skeleton";

const meta: Meta = {
  title: "Phase A/Loading states",
};
export default meta;
type Story = StoryObj;

export const Spinner: Story = {
  render: () => <LoadingState label="Loading forecast…" />,
};

export const SkeletonCard: Story = {
  render: () => (
    <div className="flex w-80 flex-col gap-3 rounded-lg border border-border p-4">
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-5/6" />
      <Skeleton className="h-8 w-24" />
    </div>
  ),
};
