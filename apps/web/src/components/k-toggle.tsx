"use client";

export type KSelection = 10 | 25 | 50;

type Props = {
  currentK: KSelection;
  onChange: (k: KSelection) => void;
};

const kOptions: Array<{ value: KSelection; label: string }> = [
  { value: 10, label: "Top 10" },
  { value: 25, label: "Top 25" },
  { value: 50, label: "Top 50" },
];

export function KToggle({ currentK, onChange: setK }: Props) {
  return (
    <>
      <select
        aria-label="Prediction group"
        className="min-h-11 w-full rounded-md border border-line bg-surface-2 px-3 text-sm font-semibold text-on-surface md:hidden"
        onChange={(event) => setK(Number(event.target.value) as KSelection)}
        value={currentK}
      >
        {kOptions.map(({ value, label }) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <div
        aria-label="Prediction group"
        className="hidden gap-1 rounded-md border border-line bg-surface-2 p-1 md:inline-flex"
        role="group"
      >
        {kOptions.map(({ value, label }) => (
          <button
            key={value}
            aria-pressed={currentK === value}
            className={`touch-manipulation min-h-11 rounded-md px-4 text-sm font-semibold transition-colors ${
              currentK === value
                ? "bg-accent text-on-accent"
                : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
            }`}
            onClick={() => setK(value)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
    </>
  );
}
