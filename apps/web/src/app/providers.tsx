"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { MswProvider } from "@/mocks/msw-provider";

/**
 * Server state (Section 25.1: accounts, forecasts, intervention cases,
 * provider policies, audit records, integration status) all flow through
 * TanStack Query. Local interface state and workflow state are handled
 * elsewhere per Section 25.2-25.3.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <MswProvider>{children}</MswProvider>
    </QueryClientProvider>
  );
}
