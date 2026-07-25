"use client";

import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastResponseV1 } from "@relief/contracts";
import { Button, chartTokens, cn } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

type RangeDays = 7 | 14 | 30;

/**
 * Section 21.3 CashFlowTimeline. Supports 7/14/30 day views (Section 21.3
 * item 1-3), an uncertainty band, a reserve line, and — per Section 27 —
 * an alternate table representation, since the timeline must not be
 * chart-only.
 */
export function CashFlowTimeline({ forecast }: { forecast: ForecastResponseV1 }) {
  const [range, setRange] = useState<RangeDays>(30);
  const [showTable, setShowTable] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  const cutoff = new Date(forecast.daily_summary[0]?.event_date ?? 0);
  cutoff.setDate(cutoff.getDate() + range);
  const points = forecast.daily_summary.filter((point) => new Date(point.event_date) <= cutoff);
  const reserveCents = forecast.trajectories[0]?.essential_reserve_cents ?? 0;

  // Recharts has no built-in from-to band; stack a transparent base area up
  // to the lower bound, then a filled area for just the (upper - lower)
  // range on top of it, so the visible band spans lower..upper.
  const chartData = points.map((point) => ({
    ...point,
    band_base: point.lower_ending_balance_cents,
    band_range: point.upper_ending_balance_cents - point.lower_ending_balance_cents,
  }));

  return (
    <section aria-label="Cash flow timeline" className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div role="group" aria-label="Timeline range" className="flex gap-1">
          {([7, 14, 30] as const).map((days) => (
            <Button
              key={days}
              size="sm"
              variant={range === days ? "primary" : "ghost"}
              aria-pressed={range === days}
              onClick={() => setRange(days)}
            >
              {days}d
            </Button>
          ))}
        </div>
        <Button size="sm" variant="ghost" aria-pressed={showTable} onClick={() => setShowTable((v) => !v)}>
          {showTable ? "View as chart" : "View as table"}
        </Button>
      </div>

      {showTable ? (
        <TimelineTable points={points} reserveCents={reserveCents} />
      ) : (
        <div className="h-72 w-full" role="img" aria-label={timelineSummary(points, reserveCents)}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid stroke={chartTokens.gridLine} vertical={false} />
              <XAxis
                dataKey="event_date"
                tickFormatter={formatDate}
                stroke={chartTokens.axisLabel}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                tickFormatter={(value: number) => formatCents(value)}
                stroke={chartTokens.axisLabel}
                tick={{ fontSize: 12 }}
                width={80}
              />
              <Tooltip
                formatter={(value: number) => formatCents(value)}
                labelFormatter={(label: string) => formatDate(label)}
              />
              <ReferenceLine
                y={reserveCents}
                stroke={chartTokens.reserveLine}
                strokeDasharray="4 4"
                label={{ value: "Essential reserve", position: "insideTopLeft", fontSize: 11, fill: chartTokens.reserveLine }}
              />
              <Area
                dataKey="band_base"
                stackId="uncertainty-band"
                stroke="none"
                fill="transparent"
                isAnimationActive={!reducedMotion}
                legendType="none"
                tooltipType="none"
              />
              <Area
                dataKey="band_range"
                stackId="uncertainty-band"
                stroke="none"
                fill={chartTokens.uncertaintyBand}
                isAnimationActive={!reducedMotion}
                name="Uncertainty range"
              />
              <Line
                dataKey="median_ending_balance_cents"
                stroke={chartTokens.modifiedTrajectory}
                strokeWidth={2}
                dot={{ r: 3 }}
                isAnimationActive={!reducedMotion}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

function timelineSummary(
  points: ForecastResponseV1["daily_summary"],
  reserveCents: number,
): string {
  const violation = points.find((p) => p.reserve_violation_probability >= 0.5);
  if (!violation) {
    return `Balance stays above the ${formatCents(reserveCents)} essential reserve through ${formatDate(points.at(-1)?.event_date ?? "")}.`;
  }
  return `Balance is projected to fall below the ${formatCents(reserveCents)} essential reserve around ${formatDate(violation.event_date)}.`;
}

function TimelineTable({
  points,
  reserveCents,
}: {
  points: ForecastResponseV1["daily_summary"];
  reserveCents: number;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <caption className="sr-only">Daily balance forecast, table alternative to the chart above.</caption>
        <thead>
          <tr className="border-b border-border bg-secondary text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th scope="col" className="px-3 py-2">Date</th>
            <th scope="col" className="px-3 py-2">Lower</th>
            <th scope="col" className="px-3 py-2">Median</th>
            <th scope="col" className="px-3 py-2">Upper</th>
            <th scope="col" className="px-3 py-2">Reserve risk</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.event_date} className="border-b border-border last:border-0">
              <td className="px-3 py-2 font-mono tabular-nums">{formatDate(point.event_date)}</td>
              <td className="px-3 py-2 font-mono tabular-nums">{formatCents(point.lower_ending_balance_cents)}</td>
              <td
                className={cn(
                  "px-3 py-2 font-mono tabular-nums font-medium",
                  point.median_ending_balance_cents < reserveCents ? "text-risk" : "text-foreground",
                )}
              >
                {formatCents(point.median_ending_balance_cents)}
              </td>
              <td className="px-3 py-2 font-mono tabular-nums">{formatCents(point.upper_ending_balance_cents)}</td>
              <td className="px-3 py-2 font-mono tabular-nums">{Math.round(point.reserve_violation_probability * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
