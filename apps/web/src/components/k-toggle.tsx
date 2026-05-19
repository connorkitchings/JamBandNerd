"use client";

import { useRouter, useSearchParams } from "next/navigation";

type Props = {
  currentK: 10 | 25 | 50;
};

function getKTextColor(k: 10 | 25 | 50) {
  return k === 10 ? "text-primary" : k === 25 ? "text-tertiary" : "text-[#c084fc]";
}

export function KToggle({ currentK }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const kOptions: Array<{ value: 10 | 25 | 50; label: string }> = [
    { value: 10, label: "Top 10" },
    { value: 25, label: "Top 25" },
    { value: 50, label: "Top 50" },
  ];

  function setK(k: 10 | 25 | 50) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("k", String(k));
    router.push(`?${params}`, { scroll: false });
  }

  function handleKeyDown(e: React.KeyboardEvent, k: 10 | 25 | 50) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setK(k);
    }
  }

  return (
    <>
      <select
        aria-label="Prediction group"
        className={`h-10 w-full rounded-xl border border-outline-variant/20 bg-surface/55 px-3 font-label text-[10px] uppercase tracking-wider focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none md:hidden ${getKTextColor(currentK)}`}
        onChange={(event) => setK(Number(event.target.value) as 10 | 25 | 50)}
        value={currentK}
      >
        {kOptions.map(({ value, label }) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <div className="hidden rounded-xl border border-outline-variant/15 bg-surface/45 p-1 md:inline-flex">
        {kOptions.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setK(value)}
            onKeyDown={(e) => handleKeyDown(e, value)}
            className={`touch-manipulation min-h-9 rounded-lg px-3 py-1.5 font-label text-[10px] uppercase tracking-wider transition-colors focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
              currentK === value
                ? `bg-primary/18 ${getKTextColor(value)} ring-1 ring-primary/35`
                : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
            }`}
            aria-pressed={currentK === value}
          >
            {label}
          </button>
        ))}
      </div>
    </>
  );
}
