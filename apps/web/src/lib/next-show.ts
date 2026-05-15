export type ShowDetails = {
  venueName: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  showDate: string | null;
  raw: Record<string, unknown>;
};

function getVenueNameFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.venue_name === "string") {
    return row.venue_name;
  }

  if (typeof row.venue === "string") {
    return row.venue;
  }

  return null;
}

function getVenueCityFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.venue_city === "string") {
    return row.venue_city;
  }

  if (typeof row.city === "string") {
    return row.city;
  }

  return null;
}

function getVenueRegionFromRow(row: Record<string, unknown> | null): string | null {
  if (!row) {
    return null;
  }

  if (typeof row.region === "string") {
    return row.region;
  }

  if (typeof row.venue_state === "string") {
    return row.venue_state;
  }

  if (typeof row.state === "string") {
    return row.state;
  }

  if (typeof row.venue_country === "string") {
    return row.venue_country;
  }

  if (typeof row.country === "string") {
    return row.country;
  }

  return null;
}

export function buildShowDetails(row: Record<string, unknown>): ShowDetails {
  return {
    venueName: getVenueNameFromRow(row),
    city: getVenueCityFromRow(row),
    state: getVenueRegionFromRow(row),
    country:
      typeof row.venue_country === "string"
        ? row.venue_country
        : typeof row.country === "string"
          ? row.country
          : null,
    showDate:
      typeof row.show_date === "string"
        ? row.show_date
        : typeof row.starts_at_local === "string"
          ? row.starts_at_local
          : null,
    raw: row,
  };
}

export function isUmDisplayEligibleUpcomingShow(
  row: Record<string, unknown> | null,
): boolean {
  const venueName = getVenueNameFromRow(row);
  if (!venueName) {
    return false;
  }

  return !venueName.trim().toLowerCase().startsWith("non-um |");
}

export function selectUmUpcomingShowRow(
  rows: Array<Record<string, unknown>>,
): Record<string, unknown> | null {
  const eligibleRows = rows.filter((row) => {
    if (!isUmDisplayEligibleUpcomingShow(row)) {
      return false;
    }

    return typeof row.starts_at_local === "string";
  });

  if (eligibleRows.length === 0) {
    return null;
  }

  return (
    eligibleRows.toSorted((left, right) => {
      const leftLocal =
        typeof left.starts_at_local === "string" ? left.starts_at_local : "";
      const rightLocal =
        typeof right.starts_at_local === "string" ? right.starts_at_local : "";

      const localComparison = leftLocal.localeCompare(rightLocal);
      if (localComparison !== 0) {
        return localComparison;
      }

      const leftStartsAt =
        typeof left.starts_at === "string" ? left.starts_at : "";
      const rightStartsAt =
        typeof right.starts_at === "string" ? right.starts_at : "";
      return leftStartsAt.localeCompare(rightStartsAt);
    })[0] ?? null
  );
}
