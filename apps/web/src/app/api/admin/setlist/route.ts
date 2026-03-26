import { createHash } from "node:crypto";

import { type SupabaseClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

import { getServiceRoleClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  const adminPassword = process.env.ADMIN_PASSWORD;

  if (!adminPassword) {
    return NextResponse.json(
      { error: "Admin not configured" },
      { status: 500 },
    );
  }

  const providedPassword = authHeader?.replace("Bearer ", "");

  if (!providedPassword || providedPassword !== adminPassword) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 },
    );
  }

  const body = await request.json();
  const { band, showDate, venueName, city, state, setlistText } = body;

  if (!band || !showDate || !venueName || !city || !state || !setlistText) {
    return NextResponse.json(
      { error: "Missing required fields" },
      { status: 400 },
    );
  }

  const supabase = getServiceRoleClient();
  if (!supabase) {
    return NextResponse.json(
      { error: "Database not configured" },
      { status: 500 },
    );
  }

  try {
    const showId = await ensureShow(
      supabase,
      band,
      showDate,
      venueName,
      city,
      state,
    );
    await upsertSetlistRows(supabase, band, showId, setlistText);

    return NextResponse.json({
      success: true,
      showId,
      message: `Setlist added for ${band} on ${showDate}`,
    });
  } catch (error) {
    console.error("Error adding setlist:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to add setlist" },
      { status: 500 },
    );
  }
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
): Promise<void> {
  const setsTable = `${band}_setlists_raw`;
  const parsed = parseSetlistText(setlistText);

  if (parsed.length === 0) {
    throw new Error("No songs parsed from setlist text");
  }

  const payload = parsed.map((song: { set_number: number; song_position: number; song_name: string; is_segue: boolean; song_notes: string }) => ({
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
}

function parseSetlistText(text: string): Array<{
  set_number: number;
  song_position: number;
  song_name: string;
  is_segue: boolean;
  song_notes: string;
}> {
  const rows: Array<{
    set_number: number;
    song_position: number;
    song_name: string;
    is_segue: boolean;
    song_notes: string;
  }> = [];

  const lines = text.split("\n").map((ln) => ln.trim()).filter(Boolean);

  for (const line of lines) {
    let setNumber: number | null = null;
    let songsPart: string | null = null;

    const setMatch = line.match(/^Set\s*(\d+)\s+(.*)$/i);
    if (setMatch) {
      setNumber = parseInt(setMatch[1], 10);
      songsPart = setMatch[2];
    } else {
      const encoreMatch = line.match(/^Encore\s+(.*)$/i);
      if (encoreMatch) {
        setNumber = 99;
        songsPart = encoreMatch[1];
      }
    }

    if (setNumber === null || songsPart === null) {
      continue;
    }

    const items = songsPart.split(",").map((s) => s.trim()).filter(Boolean);
    let pos = 1;

    for (const item of items) {
      const parts = item.split(">").map((p) => p.trim()).filter(Boolean);

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i].replace(/[\u2018\u2019]/g, "'").trim();

        rows.push({
          set_number: setNumber,
          song_position: pos,
          song_name: part,
          is_segue: i < parts.length - 1,
          song_notes: "",
        });
        pos++;
      }
    }
  }

  return rows;
}
