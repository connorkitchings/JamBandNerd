export const TONIGHT_STATUS_LABEL = "Tonight!";

export type PredictionDisplayState = "previous" | "tonight" | "next";

export function getEasternTodayIso(now: Date = new Date()) {
  return now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export function isShowTonight(showDate: string | null, now: Date = new Date()) {
  if (!showDate) {
    return false;
  }

  return showDate === getEasternTodayIso(now);
}

export function getPredictionDisplayState(
  targetShowDate: string | null,
  now: Date = new Date(),
): PredictionDisplayState | null {
  if (!targetShowDate) {
    return null;
  }

  const easternDate = getEasternTodayIso(now);
  if (targetShowDate === easternDate) {
    return "tonight";
  }
  if (targetShowDate < easternDate) {
    return "previous";
  }
  return "next";
}

export function getPredictionStatusLabel(showDate: string | null, now: Date = new Date()) {
  const state = getPredictionDisplayState(showDate, now);
  if (!state) {
    return "Prediction Outlook";
  }

  if (state === "tonight") {
    return TONIGHT_STATUS_LABEL;
  }
  if (state === "previous") {
    return "Previous Show";
  }
  return "Next Show";
}
