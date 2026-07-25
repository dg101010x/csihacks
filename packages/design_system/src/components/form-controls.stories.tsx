import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./input";
import { Textarea } from "./textarea";
import { Checkbox } from "./checkbox";
import { FormField } from "./label";

const meta: Meta = {
  title: "Phase A/Form controls",
};
export default meta;
type Story = StoryObj;

export const TextInput: Story = {
  render: () => (
    <div className="w-80">
      <FormField id="due-date" label="Second payment date" hint="Used to reschedule the remaining balance.">
        <Input id="due-date" type="date" />
      </FormField>
    </div>
  ),
};

export const InputWithError: Story = {
  render: () => (
    <div className="w-80">
      <FormField id="amount" label="First payment amount" error="Must be less than the scheduled amount.">
        <Input id="amount" defaultValue="24000" aria-invalid />
      </FormField>
    </div>
  ),
};

export const TextareaControl: Story = {
  render: () => (
    <div className="w-80">
      <FormField id="rules" label="Constitution" hint="Describe what Relief should always protect.">
        <Textarea id="rules" rows={4} placeholder="Protect housing, groceries, medicine, and transportation." />
      </FormField>
    </div>
  ),
};

export const CheckboxControl: Story = {
  render: () => (
    <label className="flex items-center gap-2 text-sm text-foreground">
      <Checkbox id="confirm-subscription" defaultChecked />
      Ask me before pausing any subscription
    </label>
  ),
};

export const DisabledControls: Story = {
  render: () => (
    <div className="flex w-80 flex-col gap-3">
      <Input disabled defaultValue="Cannot edit while provider review is pending" />
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <Checkbox disabled />
        Locked during review
      </label>
    </div>
  ),
};
