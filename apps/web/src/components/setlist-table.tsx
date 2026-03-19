import type { SetlistSong } from "@/lib/data";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  songs: SetlistSong[];
};

export function SetlistTable({ songs }: Props) {
  return (
    <ResponsiveTableFrame
      minWidthClassName="min-w-[520px] divide-y divide-outline-variant/30"
      testId="setlist-table"
    >
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Set</th>
            <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Position</th>
            <th className={TABLE_HEAD_CLASS}>Song</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
          {songs.map((song, index) => (
            <tr key={`${song.setNumber}-${song.position}-${index}`} className={index % 2 === 1 ? "bg-surface-container-low/40" : ""}>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>{song.setNumber ?? "—"}</td>
              <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-on-surface-variant`}>
                {song.position ?? "—"}
              </td>
              <td className={`${TABLE_CELL_CLASS} font-headline font-medium text-on-surface`}>
                {song.songName}
              </td>
            </tr>
          ))}
        </tbody>
    </ResponsiveTableFrame>
  );
}
