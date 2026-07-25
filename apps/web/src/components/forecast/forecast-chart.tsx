"use client";

import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button, chartTokens, cn } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import type { ForecastEnvelope, ForecastPoint, RiskWindow } from "@/domain/types";

type RangeDays = 7 | 14 | 30;

/**
 * Section 6.2 / Section 7 of the redesign brief — the shared daily forecast
 * chart used by both Command Center (summary) and Timeline (full view).
 * Replaces the old 3-point CashFlowTimeline (see ui_audit.md): every day in
 * the horizon is plotted, income/obligation events are markers on the line,
 * risk windows are shaded regions, and there is always an accessible table
 * alternative (Section 27 of the platform spec / Section 9 of this brief).
 */
export function ForecastChart({
  envelope,
  riskWindows,
  height = 320,
  defaultRange = 30,
  onSelectPoint,
}: {
  envelope: ForecastEnvelope;
  riskWindows: RiskWindow[];
  height?: number;
  defaultRange?: RangeDays;
  onSelectPoint?: (point: ForecastPoint) => void;
}) {
  const [range, setRange] = useState<RangeDays>(defaultRange);
  const [showTable, setShowTable] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  const points = envelope.points.slice(0, range);
  const chartData = points.map((point) => ({
    ...point,
    band_base: point.lower_balance_cents,
    band_range: point.upper_balance_cents - point.lower_balance_cents,
  }));
  const visibleWindows = riskWindows.filter((w) => points.some((p) => p.date === w.start_date));

  return (
    <section aria-label="Financial forecast" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="group" aria-label="Forecast range" className="flex gap-1">
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
        <ForecastTable points={points} reserveCents={envelope.reserve_cents} />
      ) : (
        <>
          <div style={{ height }} role="img" aria-label={chartSummary(points, envelope.reserve_cents, riskWindows)}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                <CartesianGrid stroke={chartTokens.gridLine} vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatDate} stroke={chartTokens.axisLabel} tick={{ fontSize: 12 }} />
                <YAxis
                  tickFormatter={(v: number) => formatCents(v)}
                  stroke={chartTokens.axisLabel}
                  tick={{ fontSize: 12 }}
                  width={84}
                />
                <Tooltip content={<ForecastTooltip />} />

                {visibleWindows.map((w) => (
                  <ReferenceArea
                    key={w.id}
                    x1={w.start_date}
                    x2={w.end_date}
                    fill={chartTokens.riskRegion}
                    stroke={chartTokens.riskRegionBorder}
                    strokeOpacity={0.4}
                  />
                ))}

                <ReferenceLine
                  y={envelope.reserve_cents}
                  stroke={chartTokens.reserveLine}
                  strokeDasharray="4 4"
                  label={{ value: "Essential reserve", position: "insideTopLeft", fontSize: 11, fill: chartTokens.reserveLine }}
                />
                <ReferenceLine y={0} stroke={chartTokens.riskRegionBorder} strokeDasharray="2 2" />

                <Area
                  dataKey="band_base"
                  stackId="band"
                  stroke="none"
                  fill="transparent"
                  isAnimationActive={!reducedMotion}
                  legendType="none"
                  tooltipType="none"
                />
                <Area
                  dataKey="band_range"
                  stackId="band"
                  stroke="none"
                  fill={chartTokens.uncertaintyBand}
                  isAnimationActive={!reducedMotion}
                  tooltipType="none"
                />

                <Line
                  dataKey="median_balance_cents"
                  stroke={chartTokens.modifiedTrajectory}
                  strokeWidth={2}
                  isAnimationActive={!reducedMotion}
                  dot={({ key, ...dotProps }) => (
                    <EventDot key={key} {...omitR(dotProps)} onSelectPoint={onSelectPoint} />
                  )}
                  activeDot={(props: unknown) => {
                    const { key, ...dotProps } = props as { key?: string; r?: number };
                    return <EventDot key={key} {...omitR(dotProps)} onSelectPoint={onSelectPoint} minRadius={5} />;
                  }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <ChartLegend />
        </>
      )}
    </section>
  );
}

/** Strips Recharts' own default `r` (always ~3, its Line dot default) so it
 * can never shadow EventDot's own hasEvent-based sizing. */
function omitR<T extends { r?: number }>(props: T): Omit<T, "r"> {
  const { r: _r, ...rest } = props;
  void _r;
  return rest;
}

function EventDot(props: {
  cx?: number;
  cy?: number;
  payload?: ForecastPoint;
  onSelectPoint?: (point: ForecastPoint) => void;
  /** Minimum radius for the active (hovered) dot — distinct from Recharts'
   * own incoming `r` (always ~3, its Line default), which we deliberately
   * ignore so event days can render larger regardless of that default. */
  minRadius?: number;
}) {
  const { cx, cy, payload, onSelectPoint, minRadius } = props;
  if (cx == null || cy == null || !payload) return <g />;
  const hasIncome = payload.events.some((e) => e.direction === "inflow");
  const hasOutflow = payload.events.some((e) => e.direction === "outflow");
  const hasEvent = hasIncome || hasOutflow;
  const radius = Math.max(minRadius ?? 0, hasEvent ? 5 : 2.5);

  return (
    <circle
      cx={cx}
      cy={cy}
      r={radius}
      fill={hasOutflow ? chartTokens.riskRegionBorder : hasIncome ? chartTokens.improvementMarker : chartTokens.modifiedTrajectory}
      stroke="var(--color-surface)"
      strokeWidth={hasEvent ? 1.5 : 0}
      style={{ cursor: onSelectPoint ? "pointer" : undefined }}
      onClick={() => onSelectPoint?.(payload)}
    />
  );
}

function ForecastTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ForecastPoint }> }) {
  if (!active || !payload?.[0]) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{formatDate(point.date)}</p>
      <p className="font-mono tabular-nums text-foreground">{formatCents(point.median_balance_cents)}</p>
      <p className="text-muted-foreground">
        Range {formatCents(point.lower_balance_cents)} – {formatCents(point.upper_balance_cents)}
      </p>
      {point.events.length > 0 && (
        <ul className="mt-1 border-t border-border pt-1">
          {point.events.map((event) => (
            <li key={event.event_id} className={event.direction === "inflow" ? "text-positive" : "text-foreground"}>
              {event.merchant_name}: {event.direction === "inflow" ? "+" : "-"}
              {formatCents(event.amount_cents)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ChartLegend() {
  const items = [
    { color: chartTokens.modifiedTrajectory, label: "Median forecast" },
    { color: chartTokens.uncertaintyBand, label: "Uncertainty range" },
    { color: chartTokens.improvementMarker, label: "Income event" },
    { color: chartTokens.riskRegionBorder, label: "Obligation event" },
    { color: chartTokens.riskRegion, label: "Risk window" },
  ];
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

function chartSummary(points: ForecastPoint[], reserveCents: number, riskWindows: RiskWindow[]): string {
  if (riskWindows.length === 0) {
    return `Balance stays above the ${formatCents(reserveCents)} essential reserve through ${formatDate(points.at(-1)?.date ?? "")}.`;
  }
  const first = riskWindows[0]!;
  return `Balance is projected to fall below the ${formatCents(reserveCents)} essential reserve starting ${formatDate(first.start_date)}. ${first.description}`;
}

function ForecastTable({ points, reserveCents }: { points: ForecastPoint[]; reserveCents: number }) {
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
            <th scope="col" className="px-3 py-2">Events</th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.date} className="border-b border-border last:border-0">
              <td className="px-3 py-2 font-mono tabular-nums">{formatDate(point.date)}</td>
              <td className="px-3 py-2 font-mono tabular-nums">{formatCents(point.lower_balance_cents)}</td>
              <td
                className={cn(
                  "px-3 py-2 font-mono tabular-nums font-medium",
                  point.median_balance_cents < reserveCents ? "text-risk" : "text-foreground",
                )}
              >
                {formatCents(point.median_balance_cents)}
              </td>
              <td className="px-3 py-2 font-mono tabular-nums">{formatCents(point.upper_balance_cents)}</td>
              <td className="px-3 py-2 font-mono tabular-nums">{Math.round(point.reserve_violation_probability * 100)}%</td>
              <td className="px-3 py-2 text-muted-foreground">
                {point.events.length === 0 ? "—" : point.events.map((e) => e.merchant_name).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
