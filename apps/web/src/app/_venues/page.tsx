import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    venue?: string;
  }>;
};

export default async function LegacyVenueAnalyticsRedirectPage({
  searchParams,
}: Props) {
  const params = await searchParams;
  const nextParams = new URLSearchParams();

  if (params.band) {
    nextParams.set("band", params.band);
  }

  if (params.venue) {
    nextParams.set("venue", params.venue);
  }

  redirect(`/venues${nextParams.size > 0 ? `?${nextParams.toString()}` : ""}`);
}
