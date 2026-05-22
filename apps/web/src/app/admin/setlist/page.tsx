import { AdminSetlistForm } from "@/components/admin-setlist-form";
import { getBands } from "@/lib/data";

export default async function AdminSetlistPage() {
  const bandsResult = await getBands();
  const bands =
    bandsResult.status === "ready"
      ? bandsResult.bands.map((b) => ({ value: b.slug, label: b.displayName }))
      : [];

  if (bands.length === 0) {
    return (
      <div className="mx-auto max-w-xl space-y-4 py-12 text-center">
        <h1 className="font-headline text-3xl font-bold text-on-surface">
          Admin Unavailable
        </h1>
        <p className="text-sm text-on-surface-variant">
          Could not load the band registry. Check Supabase configuration.
        </p>
      </div>
    );
  }

  return <AdminSetlistForm bands={bands} />;
}
