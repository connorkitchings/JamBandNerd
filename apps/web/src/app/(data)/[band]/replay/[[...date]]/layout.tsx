import { notFound } from "next/navigation";

import { isShowDate } from "@/lib/band-routes";

export default async function ReplayLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ date?: string[] }>;
}) {
  // `/<band>/replay` or `/<band>/replay/<YYYY-MM-DD>`; anything else is a 404.
  // Checked in a layout so it runs above the Suspense boundaries and yields a real 404 status.
  const { date } = await params;
  if (date && (date.length > 1 || !isShowDate(date[0]))) {
    notFound();
  }

  return children;
}
