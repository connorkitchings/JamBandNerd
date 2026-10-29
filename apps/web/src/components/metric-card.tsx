type MetricTone = "default" | "accent" | "teal";

const VALUE_TONE: Record<MetricTone, string> = {
  default: "text-on-surface",
  accent: "text-accent-text",
  teal: "text-teal",
};

type MetricCardProps = {
  label: string;
  value: string;
  hint?: string;
  tone?: MetricTone;
};

export function MetricCard({ label, value, hint, tone = "default" }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${VALUE_TONE[tone]}`}>{value}</p>
      {hint ? <p className="mt-1 text-sm text-on-surface-variant">{hint}</p> : null}
    </div>
  );
}
