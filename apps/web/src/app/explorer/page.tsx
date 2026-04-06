import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    date?: string;
    model?: string;
  }>;
};

export default async function ExplorerRedirectPage({ searchParams }: Props) {
  const params = await searchParams;
  const nextParams = new URLSearchParams();

  if (params.band) {
    nextParams.set("band", params.band);
  }

  if (params.date) {
    nextParams.set("date", params.date);
  }

  redirect(`/replay${nextParams.size > 0 ? `?${nextParams.toString()}` : ""}`);
}
