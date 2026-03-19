import Link from "next/link";

import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PredictionTable } from "@/components/prediction-table";
import { SectionCard } from "@/components/section-card";
import { SetlistTable } from "@/components/setlist-table";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getExplorerSnapshot } from "@/lib/data";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
    date?: string;
  }>;
};

export default async function ExplorerPage({ searchParams }: Props) {
  const params = await searchParams;
  const state = await getExplorerSnapshot(params.band, params.model, params.date);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the historical explorer route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Explorer query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No historical prediction dates"
        body="The explorer route is wired up, but no prediction history was found for the selected band/model."
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Historical Explorer" eyebrow="Parity View">
        <FilterLinks
          pathname="/explorer"
          band={state.band}
          model={state.model}
          date={state.explorer.selectedDate}
        />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-8">
        <h1 className="font-headline text-3xl font-semibold text-on-surface">
          {BAND_CONFIG[state.band].displayName} · {MODEL_CONFIG[state.model].displayName}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant">
          The explorer now has a website-native data path for available dates, a selected show date,
          and the paired prediction/setlist payload needed for the final parity experience.
        </p>
      </section>

      <SectionCard title="Available Prediction Dates" eyebrow="Navigator">
        <div className="flex flex-wrap gap-2">
          {state.explorer.availableDates.slice(0, 20).map((date) => (
            <Link
                key={date}
                href={`/explorer?band=${state.band}&model=${state.model}&date=${date}`}
                className={`rounded-full border px-3 py-1.5 font-headline text-xs uppercase tracking-[0.14rem] transition ${
                  date === state.explorer.selectedDate
                    ? "border-primary bg-primary-container text-white"
                    : "border-outline-variant bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                }`}
              >
                {date}
            </Link>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Predictions" eyebrow={state.explorer.selectedDate ?? "No date"}>
          <PredictionTable
            rows={state.explorer.predictions?.predictions ?? []}
            mode={state.model}
          />
        </SectionCard>
        <SectionCard title="Setlist" eyebrow={state.explorer.selectedDate ?? "No date"}>
          {state.explorer.setlist ? (
            <SetlistTable songs={state.explorer.setlist.songs} />
          ) : (
            <DataState
              title="No setlist found"
              body="A prediction date was available, but the matching setlist payload was not found yet."
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
