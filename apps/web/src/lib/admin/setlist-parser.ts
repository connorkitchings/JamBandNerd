// Pure, framework-agnostic setlist text parser shared by the admin route
// handler (server) and the admin form preview (client). Has no node-only or
// browser-only dependencies, so it is safe to import from both runtimes.

export type ParsedSong = {
  set_number: number;
  song_position: number;
  song_name: string;
  is_segue: boolean;
  song_notes: string;
};

// Several WSP song titles contain commas. The Python normalizer
// (src/jambandnerd/data_collection/wsp/parser.py) protects these before
// splitting on commas; mirror that here so manual entry preserves them as a
// single song instead of fragmenting into multiple rows. Any case-insensitive
// match is rewritten to the canonical title so the stored song_name lines up
// with historical rows (prediction grouping is case-sensitive).
const SONGS_WITH_COMMAS = [
  "Baby, Let Me Follow You Down",
  "Baby, Let Me Hold Your Hand",
  "Lawyers, Guns, And Money",
  "Baby, Please Don't Go",
  "Weak Brain, Narrow Mind",
  "Man Smart, Woman Smarter",
  "Shake, Rattle, And Roll",
];

const COMMA_PLACEHOLDER = "||COMMA||";

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function protectCommas(text: string): string {
  let result = text;
  for (const song of SONGS_WITH_COMMAS) {
    const canonicalProtected = song.replace(/,/g, COMMA_PLACEHOLDER);
    result = result.replace(new RegExp(escapeRegExp(song), "gi"), canonicalProtected);
  }
  return result;
}

function restoreCommas(text: string): string {
  return text.split(COMMA_PLACEHOLDER).join(",");
}

function normalizeQuotes(text: string): string {
  return text.replace(/[\u2018\u2019]/g, "'");
}

export function parseSetlistText(text: string): ParsedSong[] {
  const rows: ParsedSong[] = [];

  const lines = text
    .split("\n")
    .map((ln) => ln.trim())
    .filter(Boolean);

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

    const protectedPart = protectCommas(songsPart);
    const items = protectedPart.split(",").map((s) => s.trim()).filter(Boolean);
    let pos = 1;

    for (const item of items) {
      const parts = item
        .split(">")
        .map((p) => restoreCommas(normalizeQuotes(p.trim())))
        .filter(Boolean);

      for (let i = 0; i < parts.length; i++) {
        rows.push({
          set_number: setNumber,
          song_position: pos,
          song_name: parts[i],
          is_segue: i < parts.length - 1,
          song_notes: "",
        });
        pos++;
      }
    }
  }

  return rows;
}
