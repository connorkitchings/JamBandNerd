export type VenueIdentity = {
  venueName: string;
  city: string | null;
  region: string | null;
};

export type VenueShow = VenueIdentity & {
  showId: string;
  showDate: string;
};

export type VenueSetlistEntry = {
  showId: string;
  songName: string;
  setNumber: number | null;
  position: number | null;
};

export type VenueOption = VenueIdentity & {
  key: string;
  label: string;
  showCount: number;
  latestShowDate: string;
};

export type VenueSongStat = {
  songName: string;
  showCount: number;
  percentOfShows: number;
};

export type VenueShowSummary = {
  showId: string;
  showDate: string;
  songCount: number;
};

export type VenueAnalyticsSnapshot = VenueIdentity & {
  venueKey: string;
  label: string;
  showCount: number;
  firstShowDate: string;
  latestShowDate: string;
  uniqueSongs: number;
  averageSongsPerShow: number;
  topSongs: VenueSongStat[];
  recentShows: VenueShowSummary[];
};

function normalizeKeyPart(value: string | null | undefined): string {
  const normalized = (value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return normalized || "unknown";
}

function normalizeSongName(value: string): string {
  return value.trim().toLowerCase();
}

export function buildVenueKey(identity: VenueIdentity): string {
  return [
    normalizeKeyPart(identity.venueName),
    normalizeKeyPart(identity.city),
    normalizeKeyPart(identity.region),
  ].join("__");
}

export function buildVenueLabel(identity: VenueIdentity): string {
  const location = [identity.city, identity.region]
    .filter((value): value is string => Boolean(value))
    .join(", ");

  return location ? `${identity.venueName} • ${location}` : identity.venueName;
}

export function summarizeVenueOptions(shows: VenueShow[]): VenueOption[] {
  const grouped = new Map<
    string,
    {
      identity: VenueIdentity;
      showCount: number;
      latestShowDate: string;
    }
  >();

  for (const show of shows) {
    const identity: VenueIdentity = {
      venueName: show.venueName,
      city: show.city,
      region: show.region,
    };
    const key = buildVenueKey(identity);
    const existing = grouped.get(key);

    if (existing) {
      existing.showCount += 1;
      if (show.showDate > existing.latestShowDate) {
        existing.latestShowDate = show.showDate;
      }
      continue;
    }

    grouped.set(key, {
      identity,
      showCount: 1,
      latestShowDate: show.showDate,
    });
  }

  return [...grouped.entries()]
    .map(([key, value]) => ({
      key,
      label: buildVenueLabel(value.identity),
      venueName: value.identity.venueName,
      city: value.identity.city,
      region: value.identity.region,
      showCount: value.showCount,
      latestShowDate: value.latestShowDate,
    }))
    .sort((left, right) => {
      if (right.showCount !== left.showCount) {
        return right.showCount - left.showCount;
      }
      if (right.latestShowDate !== left.latestShowDate) {
        return right.latestShowDate.localeCompare(left.latestShowDate);
      }
      return left.label.localeCompare(right.label);
    });
}

function buildSetlistEntryKey(entry: VenueSetlistEntry, index: number): string {
  if (entry.position !== null) {
    return `${entry.showId}:${entry.setNumber ?? "na"}:${entry.position}`;
  }

  return `${entry.showId}:${normalizeSongName(entry.songName)}:${index}`;
}

export function buildVenueAnalyticsSnapshot(
  shows: VenueShow[],
  setlistEntries: VenueSetlistEntry[],
): VenueAnalyticsSnapshot {
  if (shows.length === 0) {
    throw new Error("Venue analytics require at least one show");
  }

  const sortedShows = shows.toSorted((left, right) =>
    left.showDate.localeCompare(right.showDate),
  );
  const venueIdentity: VenueIdentity = {
    venueName: sortedShows[0].venueName,
    city: sortedShows[0].city,
    region: sortedShows[0].region,
  };
  const venueKey = buildVenueKey(venueIdentity);
  const uniqueSongsByShow = new Map<string, Set<string>>();
  const songCountByShow = new Map<string, number>();
  const canonicalSongNames = new Map<string, string>();
  const seenEntries = new Set<string>();

  for (let index = 0; index < setlistEntries.length; index += 1) {
    const entry = setlistEntries[index];
    const key = buildSetlistEntryKey(entry, index);
    if (seenEntries.has(key)) {
      continue;
    }
    seenEntries.add(key);

    songCountByShow.set(entry.showId, (songCountByShow.get(entry.showId) ?? 0) + 1);

    const normalizedSongName = normalizeSongName(entry.songName);
    canonicalSongNames.set(
      normalizedSongName,
      canonicalSongNames.get(normalizedSongName) ?? entry.songName.trim(),
    );

    const showSongs = uniqueSongsByShow.get(entry.showId) ?? new Set<string>();
    showSongs.add(normalizedSongName);
    uniqueSongsByShow.set(entry.showId, showSongs);
  }

  const songAppearances = new Map<string, number>();
  for (const showSongs of uniqueSongsByShow.values()) {
    for (const normalizedSongName of showSongs) {
      songAppearances.set(
        normalizedSongName,
        (songAppearances.get(normalizedSongName) ?? 0) + 1,
      );
    }
  }

  const showCount = shows.length;
  const totalSongs = shows.reduce(
    (sum, show) => sum + (songCountByShow.get(show.showId) ?? 0),
    0,
  );
  const topSongs = [...songAppearances.entries()]
    .map(([normalizedSongName, appearanceCount]) => ({
      songName: canonicalSongNames.get(normalizedSongName) ?? normalizedSongName,
      showCount: appearanceCount,
      percentOfShows: appearanceCount / showCount,
    }))
    .sort((left, right) => {
      if (right.showCount !== left.showCount) {
        return right.showCount - left.showCount;
      }
      return left.songName.localeCompare(right.songName);
    });

  const recentShows = shows
    .toSorted((left, right) => right.showDate.localeCompare(left.showDate))
    .slice(0, 10)
    .map((show) => ({
      showId: show.showId,
      showDate: show.showDate,
      songCount: songCountByShow.get(show.showId) ?? 0,
    }));

  return {
    venueKey,
    label: buildVenueLabel(venueIdentity),
    venueName: venueIdentity.venueName,
    city: venueIdentity.city,
    region: venueIdentity.region,
    showCount,
    firstShowDate: sortedShows[0].showDate,
    latestShowDate: sortedShows[sortedShows.length - 1].showDate,
    uniqueSongs: songAppearances.size,
    averageSongsPerShow: totalSongs / showCount,
    topSongs,
    recentShows,
  };
}
