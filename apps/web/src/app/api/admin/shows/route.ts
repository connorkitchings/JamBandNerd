import { NextRequest, NextResponse } from "next/server";

import { guardAdmin } from "@/lib/admin/auth-request";
import { isAdminBand } from "@/lib/admin/bands";
import { getServiceRoleClient } from "@/lib/supabase/server";

// Read-only: list existing shows on a date so the admin can attach a setlist
// to the correct show_id instead of creating a duplicate row.
export async function GET(request: NextRequest) {
  const gate = guardAdmin(request);
  if (gate) {
    return gate;
  }

  const band = request.nextUrl.searchParams.get("band");
  const showDate = request.nextUrl.searchParams.get("date");
  if (!band || !showDate) {
    return NextResponse.json({ error: "band and date are required" }, { status: 400 });
  }

  if (!isAdminBand(band)) {
    return NextResponse.json({ error: "Unsupported band" }, { status: 400 });
  }

  const supabase = getServiceRoleClient();
  if (!supabase) {
    return NextResponse.json({ error: "Database not configured" }, { status: 500 });
  }

  const showsTable = `${band}_shows_raw`;
  const setlistsTable = `${band}_setlists_raw`;

  const { data: shows, error } = await supabase
    .from(showsTable)
    .select("show_id, show_date, venue_name, city, state, source_url")
    .eq("show_date", showDate)
    .order("show_id");

  if (error) {
    console.error("Error listing admin shows:", error);
    return NextResponse.json({ error: "Failed to load shows" }, { status: 500 });
  }

  // Attach the current setlist row count per show so the UI can flag shows that
  // already have data (and would be overwritten by a re-submit).
  const countResults = await Promise.all(
    (shows ?? []).map(async (show) => {
      const { count, error: countError } = await supabase
        .from(setlistsTable)
        .select("*", { count: "exact", head: true })
        .eq("show_id", show.show_id);
      return { show, count, countError };
    }),
  );

  const failed = countResults.find((result) => result.countError);
  if (failed) {
    console.error("Error counting setlist rows:", failed.countError);
    return NextResponse.json({ error: "Failed to load shows" }, { status: 500 });
  }

  return NextResponse.json({
    shows: countResults.map(({ show, count }) => ({ ...show, setlistRowCount: count ?? 0 })),
  });
}
