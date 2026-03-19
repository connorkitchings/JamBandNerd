import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { SectionCard } from "@/components/section-card";
import { SetlistTable } from "@/components/setlist-table";
import { BAND_CONFIG } from "@/lib/config";
import { getLastShowSetlist } from "@/lib/data";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
  }>;
};

export default async function LastShowPage({ searchParams }: Props) {
  const params = await searchParams;
  const state = await getLastShowSetlist(params.band);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the last-show route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Last-show query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No last show available"
        body="No completed show with setlist data was found for the selected band."
      />
    );
  }

  const venue =
    typeof state.setlist.showDetails?.venue_name === "string"
      ? state.setlist.showDetails.venue_name
      : "Venue unavailable";
  const showDate =
    typeof state.setlist.showDetails?.show_date === "string"
      ? state.setlist.showDetails.show_date
      : "Unknown date";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Last Show" eyebrow="Parity View">
        <FilterLinks pathname="/last-show" band={state.band} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-gradient-to-r from-surface to-surface-container p-8">
        <p className="text-sm text-on-surface-variant">{BAND_CONFIG[state.band].displayName}</p>
        <h1 className="mt-2 font-headline text-3xl font-semibold text-on-surface">{venue}</h1>
        <p className="mt-2 text-sm text-on-surface-variant">{showDate}</p>
      </section>

      <SectionCard title="Setlist" eyebrow="Completed Show">
        <SetlistTable songs={state.setlist.songs} />
      </SectionCard>
    </div>
  );
}
