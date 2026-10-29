import { revalidateTag } from "next/cache";

import { getBands } from "@/lib/data";
import { handleRevalidateRequest } from "@/lib/revalidate-request";

// Only POST is exported, so Next answers every other method with 405.
export async function POST(request: Request) {
  return handleRevalidateRequest(request, {
    secret: process.env.REVALIDATE_SECRET,
    getBandSlugs: async () => {
      const bands = await getBands();
      return bands.status === "ready" ? bands.bands.map((band) => band.slug) : null;
    },
    // `{ expire: 0 }` expires immediately, so the first visitor after the
    // pipeline run gets fresh data rather than a stale-while-revalidate hit.
    revalidate: (tag) => revalidateTag(tag, { expire: 0 }),
  });
}
