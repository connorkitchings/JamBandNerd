"use client";

import { useRouter, useSearchParams } from "next/navigation";

type Props = {
  currentK: 10 | 25 | 50 | "all";
};

export function KToggle({ currentK }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const kOptions: Array<{ value: 10 | 25 | 50 | "all"; label: string }> = [
    { value: "all", label: "All" },
    { value: 10, label: "Top 10" },
    { value: 25, label: "Top 25" },
    { value: 50, label: "Top 50" },
  ];

  function setK(k: 10 | 25 | 50 | "all") {
    const params = new URLSearchParams(searchParams.toString());
    params.set("k", String(k));
    router.push(`?${params}`, { scroll: false });
  }

  function handleKeyDown(e: React.KeyboardEvent, k: 10 | 25 | 50 | "all") {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setK(k);
    }
  }

  return (
    <div className="flex gap-1">
      {kOptions.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => setK(value)}
          onKeyDown={(e) => handleKeyDown(e, value)}
          className={`touch-manipulation min-h-11 rounded px-3 py-1.5 font-label text-[10px] uppercase tracking-wider transition-colors ${
            currentK === value
              ? "bg-primary/20 text-primary ring-1 ring-primary/40"
              : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
          }`}
          aria-pressed={currentK === value}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
