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

export function getPredictionStatusLabel(showDate: string | null) {
  if (!showDate) {
    return "Prediction Outlook";
  }

  return isShowTonight(showDate) ? TONIGHT_STATUS_LABEL : "Next Show";
}
