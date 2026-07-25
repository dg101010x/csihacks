import type { Meta, StoryObj } from "@storybook/react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./card";
import { Button } from "./button";

const meta: Meta = {
  title: "Phase A/Card",
};
export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => (
    <Card className="w-96">
      <CardHeader>
        <CardTitle>Auto loan — split payment</CardTitle>
        <CardDescription>Reduces Thursday's obligation collision by $120.</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-foreground">
          Split the $240 payment into two $120 installments on Jul 27 and Aug 7. No added fee.
        </p>
      </CardContent>
      <CardFooter>
        <Button size="sm">Approve</Button>
        <Button size="sm" variant="ghost">
          Compare alternatives
        </Button>
      </CardFooter>
    </Card>
  ),
};
