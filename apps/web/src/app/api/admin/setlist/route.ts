import { createHash } from "node:crypto";

import { type SupabaseClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

import { parseSetlistText, type ParsedSong } from "@/lib/admin/setlist-parser";
import { ADMIN_SESSION_COOKIE, verifyAdminSessionToken } from "@/lib/admin/session";
import { getServiceRoleClient } from "@/lib/supabase/server";

function isAuthenticated(request: NextRequest): boolean {
  const token = request.cookies.get(ADMIN_SESSION_COOKIE)?.value;
  return verifyAdminSessionToken(token, process.env.ADMIN_SESSION_SECRET);
}

function notConfigured() {
  return NextResponse.json({ error: "Admin not configured" }, { status: 503 });
}

// Read-only: list existing shows on a date so the admin can attach a setlist
// to the correct show_id instead of creating a duplicate row. Auth-gated by
// proxy.ts for the /api/admin/** prefix; re-checked here for defense in depth.
export async function GET(request: NextRequest) {
  if (!process.env.ADMIN_PASSWORD || !process.env.ADMIN_SESSION_SECRET) {
    return notConfigured();
  }
  if (!isAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
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

export async function POST(request: NextRequest) {
  if (!process.env.ADMIN_PASSWORD || !process.env.ADMIN_SESSION_SECRET) {
    return notConfigured();
  }
  if (!isAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { band, showDate, venueName, city, state, setlistText, showId } = body;

  if (!band || !showDate || !setlistText) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  const supabase = getServiceRoleClient();
  if (!supabase) {
    return NextResponse.json({ error: "Database not configured" }, { status: 500 });
  }

  try {
    // If the caller selected an existing show, trust that id. Otherwise resolve
    // or create by (date, venue) — the legacy path. Attaching to the wrong
    // show_id is the highest-risk failure mode, so the UI prefers selection.
    const resolvedShowId =
      typeof showId === "string" && showId.trim()
        ? showId
        : await ensureShow(supabase, band, showDate, venueName, city, state);

    const rows = await upsertSetlistRows(supabase, band, resolvedShowId, setlistText);

    return NextResponse.json({
      success: true,
      showId: resolvedShowId,
      rows,
      rowCount: rows.length,
      message: `${rows.length} song${rows.length === 1 ? "" : "s"} saved for ${band} on ${showDate}`,
    });
  } catch (error) {
    console.error("Error adding setlist:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to add setlist" },
      { status: 500 },
    );
  }
}

// Delete every setlist row for one show but keep the show row itself. Recovery
// path for a bad manual entry: clear, then re-submit. Mirrors the per-show
// behavior of scripts/admin/repair_wsp_setlists_range.py.
export async function DELETE(request: NextRequest) {
  if (!process.env.ADMIN_PASSWORD || !process.env.ADMIN_SESSION_SECRET) {
    return notConfigured();
  }
  if (!isAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const band = request.nextUrl.searchParams.get("band");
  const showId = request.nextUrl.searchParams.get("showId");
  if (!band || !showId) {
    return NextResponse.json({ error: "band and showId are required" }, { status: 400 });
  }

  const supabase = getServiceRoleClient();
  if (!supabase) {
    return NextResponse.json({ error: "Database not configured" }, { status: 500 });
  }

  const { error, count } = await supabase
    .from(`${band}_setlists_raw`)
    .delete({ count: "exact" })
    .eq("show_id", showId);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({
    success: true,
    showId,
    deleted: count ?? 0,
    message: `Cleared ${count ?? 0} setlist row${count === 1 ? "" : "s"} for show ${showId}`,
  });
}

async function ensureShow(
  supabase: SupabaseClient,
  band: string,
  showDate: string,
  venueName: string,
  city: string,
  state: string,
): Promise<string> {
  const showsTable = `${band}_shows_raw`;

  const { data: existing } = await supabase
    .from(showsTable)
    .select("show_id")
    .eq("show_date", showDate)
    .eq("venue_name", venueName)
    .limit(1)
    .single();

  if (existing) {
    return existing.show_id;
  }

  const showId = generateShowId(showDate, venueName);

  const row: Record<string, unknown> = {
    show_id: showId,
    show_date: showDate,
    venue_name: venueName,
    city: city,
    state: state,
  };

  if (band === "wsp") {
    row["source_hash"] = null;
  }

  await supabase.from(showsTable).upsert(row, { onConflict: "show_id" }).select();

  return showId;
}

function generateShowId(date: string, venue: string): string {
  const hash = createHash("md5").update(`${date}|${venue}`).digest("hex");
  return parseInt(hash.slice(0, 8), 16).toString();
}

async function upsertSetlistRows(
  supabase: SupabaseClient,
  band: string,
  showId: string,
  setlistText: string,
): Promise<ParsedSong[]> {
  const setsTable = `${band}_setlists_raw`;
  const parsed = parseSetlistText(setlistText);

  if (parsed.length === 0) {
    throw new Error("No songs parsed from setlist text");
  }

  const payload = parsed.map((song) => ({
    show_id: showId,
    set_number: song.set_number,
    song_position: song.song_position,
    song_name: song.song_name,
    is_segue: song.is_segue,
    song_notes: song.song_notes,
  }));

  await supabase
    .from(setsTable)
    .upsert(payload, { onConflict: "show_id,set_number,song_position" })
    .select();

  return parsed;
}
