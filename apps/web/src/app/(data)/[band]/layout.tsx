import { RememberBand } from "@/components/remember-band";
import { DEFAULT_BAND_SLUG } from "@/lib/config";
import { getBands, resolveBandPage } from "@/lib/data";

// Prerender every active band. Cache Components requires at least one param, so
// fall back to the default band when the registry cannot be read (e.g. a build
// without Supabase credentials); other bands are rendered on first request.
export async function generateStaticParams() {
  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return [{ band: DEFAULT_BAND_SLUG }];
  }
  return bandsState.bands.map((band) => ({ band: band.slug }));
}

export default async function BandLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ band: string }>;
}) {
  // Resolving here, above the pages' Suspense boundaries, makes an unknown band a
  // real 404 response; once a fallback has streamed, the status is already 200.
  const { band } = await params;
  await resolveBandPage(band);

  return (
    <>
      <RememberBand band={band} />
      {children}
    </>
  );
}
