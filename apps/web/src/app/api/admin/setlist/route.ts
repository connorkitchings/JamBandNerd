import { createHash } from "node:crypto";

import { type SupabaseClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

import { guardAdmin } from "@/lib/admin/auth-request";
import { isAdminBand } from "@/lib/admin/bands";
import { parseSetlistText, type ParsedSong } from "@/lib/admin/setlist-parser";
import { getServiceRoleClient } from "@/lib/supabase/server";

class NoSongsParsedError extends Error {
  constructor() {
    super("No songs parsed from setlist text");
  }
}

export async function POST(request: NextRequest) {
  const gate = guardAdmin(request);
  if (gate) {
    return gate;
  }

  let body: Record<string, unknown>;
  try {
    const parsed: unknown = await request.json();
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Body must be an object");
    }
    body = parsed as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { band, showDate, venueName, city, state, setlistText, showId } = body;

  if (
    typeof band !== "string" ||
    typeof showDate !== "string" ||
    typeof setlistText !== "string" ||
    !band ||
    !showDate ||
    !setlistText
  ) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }
  if (!isAdminBand(band)) {
    return NextResponse.json({ error: "Unsupported band" }, { status: 400 });
  }
  const venue = typeof venueName === "string" ? venueName : "";
  const cityValue = typeof city === "string" ? city : "";
  const stateValue = typeof state === "string" ? state : "";

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
        : await ensureShow(supabase, band, showDate, venue, cityValue, stateValue);

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
    // Raw Supabase text stays in the server log; the parse failure is
    // actionable input feedback, everything else gets a fixed message.
    if (error instanceof NoSongsParsedError) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }
    return NextResponse.json({ error: "Failed to save setlist" }, { status: 500 });
  }
}

// Delete every setlist row for one show but keep the show row itself. Recovery
// path for a bad manual entry: clear, then re-submit. Mirrors the per-show
// behavior of scripts/admin/repair_wsp_setlists_range.py.
export async function DELETE(request: NextRequest) {
  const gate = guardAdmin(request);
  if (gate) {
    return gate;
  }

  const band = request.nextUrl.searchParams.get("band");
  const showId = request.nextUrl.searchParams.get("showId");
  if (!band || !showId) {
    return NextResponse.json({ error: "band and showId are required" }, { status: 400 });
  }
  if (!isAdminBand(band)) {
    return NextResponse.json({ error: "Unsupported band" }, { status: 400 });
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
    console.error("Error clearing setlist:", error);
    return NextResponse.json({ error: "Failed to clear setlist" }, { status: 500 });
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

  const { data: existing, error: lookupError } = await supabase
    .from(showsTable)
    .select("show_id")
    .eq("show_date", showDate)
    .eq("venue_name", venueName)
    .limit(1)
    .maybeSingle();

  if (lookupError) {
    throw lookupError;
  }

  if (existing) {
    return existing.show_id;
  }

  const showId = generateShowId(showDate, venueName);

  const row = {
    show_id: showId,
    show_date: showDate,
    venue_name: venueName,
    city,
    state,
    source_hash: null,
  };

  const { error: upsertError } = await supabase
    .from(showsTable)
    .upsert(row, { onConflict: "show_id" });
  if (upsertError) {
    throw upsertError;
  }

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
    throw new NoSongsParsedError();
  }

  const payload = parsed.map((song) => ({
    show_id: showId,
    set_number: song.set_number,
    song_position: song.song_position,
    song_name: song.song_name,
    is_segue: song.is_segue,
    song_notes: song.song_notes,
  }));

  const { error } = await supabase
    .from(setsTable)
    .upsert(payload, { onConflict: "show_id,set_number,song_position" });
  if (error) {
    throw error;
  }

  return parsed;
}
