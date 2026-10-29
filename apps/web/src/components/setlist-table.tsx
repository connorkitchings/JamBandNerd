import type { SetlistSong } from "@/lib/data";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_ROW_HEAD_CLASS,
} from "@/components/responsive-table";
import { formatSetLabel } from "@/lib/format";

type Props = {
  songs: SetlistSong[];
};

export function SetlistTable({ songs }: Props) {
  const displayRows = songs.map((song, index) => {
    const displayPosition =
      songs
        .slice(0, index)
        .filter((entry) => entry.setNumber === song.setNumber).length + 1;

    return {
      ...song,
      displayPosition,
    };
  });

  return (
    <ResponsiveTableFrame
      caption="Setlist: set, position and song"
      minWidthClassName="min-w-[320px]"
      testId="setlist-table"
    >
      <thead className="bg-surface-2">
        <tr>
          <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Set</th>
          <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Position</th>
          <th scope="col" className={TABLE_HEAD_CLASS}>Song</th>
        </tr>
      </thead>
      <tbody className="text-on-surface">
        {displayRows.map((song, index) => (
          <tr key={`${song.setNumber}-${song.position}-${index}`}>
            <td className={`${TABLE_CELL_CLASS} whitespace-nowrap`}>
              {formatSetLabel(song.setNumber)}
            </td>
            <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-on-surface-variant`}>
              {song.displayPosition}
            </td>
            <th scope="row" className={TABLE_ROW_HEAD_CLASS}>
              {song.songName}
            </th>
          </tr>
        ))}
      </tbody>
    </ResponsiveTableFrame>
  );
}
