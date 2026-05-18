import type { SetlistSong } from "@/lib/data";
import { formatSetLabel } from "@/lib/format";

type Props = {
  songs: SetlistSong[];
};

type SetGroup = {
  key: string;
  label: string;
  songs: SetlistSong[];
};

function buildSetGroups(songs: SetlistSong[]) {
  const regularSets: SetGroup[] = [];
  const encoreSongs: SetlistSong[] = [];

  for (const song of songs) {
    if (song.setNumber === 99) {
      encoreSongs.push(song);
      continue;
    }

    const key = String(song.setNumber ?? "unknown");
    const existingSet = regularSets.find((setGroup) => setGroup.key === key);
    if (existingSet) {
      existingSet.songs.push(song);
      continue;
    }

    regularSets.push({
      key,
      label: `Set ${formatSetLabel(song.setNumber)}`,
      songs: [song],
    });
  }

  return { regularSets, encoreSongs };
}

function getGridClassName(setCount: number) {
  switch (setCount) {
    case 0:
    case 1:
      return "grid-cols-1";
    case 2:
      return "grid-cols-1 md:grid-cols-2";
    case 3:
      return "grid-cols-1 md:grid-cols-3";
    case 4:
      return "grid-cols-1 md:grid-cols-2 xl:grid-cols-4";
    default:
      return "grid-cols-1 md:grid-cols-2 xl:grid-cols-3";
  }
}

function SetGroupCard({
  label,
  songs,
}: {
  label: string;
  songs: SetlistSong[];
}) {
  return (
    <section className="rounded-[1.35rem] border border-outline-variant/20 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(17,23,35,0.56))] p-4 shadow-[0_16px_40px_rgba(0,0,0,0.16)]">
      <div className="flex items-center justify-between gap-3 border-b border-white/8 pb-3">
        <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
          {label}
        </p>
        <span className="rounded-full border border-white/10 bg-white/6 px-2.5 py-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
          {songs.length} songs
        </span>
      </div>
      <ol className="mt-4 space-y-2">
        {songs.map((song, index) => (
          <li
            key={`${label}-${song.position ?? index}-${song.songName}`}
            className="flex items-start gap-3 rounded-xl border border-white/8 bg-[rgba(255,255,255,0.03)] px-3 py-2.5 backdrop-blur-[2px]"
          >
            <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-white/8 text-center font-label text-[10px] uppercase tracking-[0.12em] text-on-surface-variant">
              {index + 1}
            </span>
            <span className="font-headline text-sm font-medium text-on-surface">
              {song.songName}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function SetlistColumns({ songs }: Props) {
  const { regularSets, encoreSongs } = buildSetGroups(songs);
  const groups = [...regularSets];

  if (encoreSongs.length > 0) {
    groups.push({
      key: "encore",
      label: "Encore",
      songs: encoreSongs,
    });
  }

  return (
    <div className={`grid gap-4 ${getGridClassName(groups.length)}`}>
      {groups.map((setGroup) => (
        <SetGroupCard
          key={setGroup.key}
          label={setGroup.label}
          songs={setGroup.songs}
        />
      ))}
    </div>
  );
}
