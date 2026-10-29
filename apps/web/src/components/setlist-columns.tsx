import type { SetlistSong } from "@/lib/data";
import { formatSetLabel } from "@/lib/format";
import { normalizeSongName } from "@/lib/song-board-core";
import {
  ResponsiveTableFrame,
  StatusMark,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
  TABLE_ROW_HEAD_CLASS,
} from "@/components/responsive-table";

type Props = {
  songs: SetlistSong[];
  /** Normalized names of predicted songs; adds a Predicted column when provided. */
  highlightSongs?: Set<string>;
};

/** Actual setlist as a single table in play order; sets are labelled per row. */
export function SetlistColumns({ songs, highlightSongs }: Props) {
  return (
    <ResponsiveTableFrame
      caption="Actual setlist"
      minWidthClassName="min-w-[320px]"
      testId="setlist-columns"
    >
      <thead className="bg-surface-2">
        <tr>
          <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Set</th>
          <th scope="col" className={TABLE_HEAD_CLASS}>Song</th>
          {highlightSongs ? (
            <th scope="col" className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Predicted</th>
          ) : null}
        </tr>
      </thead>
      <tbody className="text-on-surface">
        {songs.map((song, index) => (
          <tr key={`${song.setNumber}-${song.position ?? index}-${song.songName}`}>
            <td className={`${TABLE_CELL_CLASS} whitespace-nowrap text-on-surface-variant`}>
              {formatSetLabel(song.setNumber)}
            </td>
            <th scope="row" className={TABLE_ROW_HEAD_CLASS}>
              {song.songName}
            </th>
            {highlightSongs ? (
              <td className={TABLE_CELL_CLASS}>
                <StatusMark
                  on={highlightSongs.has(normalizeSongName(song.songName))}
                  onLabel="Yes"
                  offLabel="No"
                />
              </td>
            ) : null}
          </tr>
        ))}
      </tbody>
    </ResponsiveTableFrame>
  );
}
