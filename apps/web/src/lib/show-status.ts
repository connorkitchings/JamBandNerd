export const TONIGHT_STATUS_LABEL = "Tonight!";

function getEasternDateString(now: Date) {
  return now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export function isShowTonight(showDate: string | null, now: Date = new Date()) {
  if (!showDate) {
    return false;
  }

  return showDate === getEasternDateString(now);
}

export function getPredictionStatusLabel(showDate: string | null, now: Date = new Date()) {
  if (!showDate) {
    return "Prediction Outlook";
  }

  if (isShowTonight(showDate, now)) {
    return TONIGHT_STATUS_LABEL;
  }

  const easternDate = getEasternDateString(now);
  if (showDate < easternDate) {
    return "Previous Show";
  }

  return "Next Show";
}
