import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
  }>;
};

export default async function PredictionsPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.band) query.set("band", params.band);
  if (params.model) query.set("model", params.model);
  redirect(`/${query.toString() ? `?${query}` : ""}`);
}
