import type { SetlistSong } from "@/lib/data";

type Props = {
  songs: SetlistSong[];
};

export function SetlistTable({ songs }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-outline-variant/30">
      <table className="min-w-[520px] divide-y divide-outline-variant/30 text-left text-sm">
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Set</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Position</th>
            <th className="px-4 py-3 font-label text-[10px] font-medium uppercase tracking-[0.18rem]">Song</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {songs.map((song, index) => (
            <tr key={`${song.setNumber}-${song.position}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className="px-4 py-3">{song.setNumber ?? "—"}</td>
              <td className="px-4 py-3 text-on-surface-variant">{song.position ?? "—"}</td>
              <td className="px-4 py-3 font-headline font-medium text-on-surface">{song.songName}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
