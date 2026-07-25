import * as React from "react";
import { cn } from "../cn";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="presentation"
      className={cn("animate-pulse rounded-md bg-muted/40 motion-reduce:animate-none", className)}
      {...props}
    />
  );
}
