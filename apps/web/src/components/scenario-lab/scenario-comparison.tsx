"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, chartTokens } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import type { ScenarioResult } from "@/domain/types";

/**
 * Section 8 — baseline and simulated values shown together, plus explicit
 * metric deltas (lowest balance, days below reserve, missed obligation /
 * negative balance probability, added cost, time to recovery).
 */
export function ScenarioComparison({ result }: { result: ScenarioResult }) {
  const { baseline, active, deltas } = result;
  const chartData = active.points.map((point, i) => ({
    date: point.date,
    baseline: baseline.points[i]?.median_balance_cents ?? null,
    active: point.median_balance_cents,
  }));

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Baseline vs. simulated</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                <CartesianGrid stroke={chartTokens.gridLine} vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatDate} stroke={chartTokens.axisLabel} tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={(v: number) => formatCents(v)} stroke={chartTokens.axisLabel} tick={{ fontSize: 12 }} width={84} />
                <Tooltip formatter={(v: number) => formatCents(v)} labelFormatter={(l: string) => formatDate(l)} />
                <ReferenceLine y={active.reserve_cents} stroke={chartTokens.reserveLine} strokeDasharray="4 4" />
                <Line dataKey="baseline" name="Baseline" stroke={chartTokens.baselineTrajectory} strokeWidth={2} strokeDasharray="5 4" dot={false} />
                <Line dataKey="active" name="Simulated" stroke={chartTokens.modifiedTrajectory} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-2 flex gap-4 text-xs text-muted-foreground">
            <li className="flex items-center gap-1.5">
              <span className="h-0.5 w-4" style={{ backgroundColor: chartTokens.baselineTrajectory }} aria-hidden="true" />
              Baseline
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-0.5 w-4" style={{ backgroundColor: chartTokens.modifiedTrajectory }} aria-hidden="true" />
              Simulated
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What changed</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
            <Delta label="Lowest projected balance" value={formatCents(deltas.lowest_balance_delta_cents)} negative={deltas.lowest_balance_delta_cents < 0} />
            <Delta label="Days below reserve" value={`${deltas.days_below_reserve_delta > 0 ? "+" : ""}${deltas.days_below_reserve_delta}`} negative={deltas.days_below_reserve_delta > 0} />
            <Delta
              label="Missed obligation probability"
              value={`${deltas.missed_obligation_probability_delta > 0 ? "+" : ""}${Math.round(deltas.missed_obligation_probability_delta * 100)}pp`}
              negative={deltas.missed_obligation_probability_delta > 0}
            />
            <Delta
              label="Negative balance probability"
              value={`${deltas.negative_balance_probability_delta > 0 ? "+" : ""}${Math.round(deltas.negative_balance_probability_delta * 100)}pp`}
              negative={deltas.negative_balance_probability_delta > 0}
            />
            <Delta label="Added intervention cost" value={formatCents(deltas.added_intervention_cost_cents)} negative={deltas.added_intervention_cost_cents > 0} />
            <Delta label="Time to recovery" value={deltas.recovery_date ? formatDate(deltas.recovery_date) : "—"} negative={false} />
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}

function Delta({ label, value, negative }: { label: string; value: string; negative: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={`font-mono text-lg font-semibold tabular-nums ${negative ? "text-risk" : "text-foreground"}`}>{value}</dd>
    </div>
  );
}
