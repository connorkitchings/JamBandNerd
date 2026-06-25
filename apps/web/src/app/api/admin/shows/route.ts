import { NextRequest, NextResponse } from "next/server";

import { guardAdmin } from "@/lib/admin/auth-request";
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
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Attach the current setlist row count per show so the UI can flag shows that
  // already have data (and would be overwritten by a re-submit).
  const showsWithCounts = await Promise.all(
    (shows ?? []).map(async (show) => {
      const { count } = await supabase
        .from(setlistsTable)
        .select("*", { count: "exact", head: true })
        .eq("show_id", show.show_id);
      return { ...show, setlistRowCount: count ?? 0 };
    }),
  );

  return NextResponse.json({ shows: showsWithCounts });
}
