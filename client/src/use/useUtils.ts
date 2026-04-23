function getCurrentTime() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  return hours + minutes + seconds;
}

function extractDateTimeComponents(dateTimeString: string) {
  const dateTime = new Date(dateTimeString);

  // Extracting date components
  const year = dateTime.getFullYear();
  const month = String(dateTime.getMonth() + 1).padStart(2, "0");
  const day = String(dateTime.getDate()).padStart(2, "0");

  // Forming date string in the format YYYY-MM-DD
  const dateString = `${year}-${month}-${day}`;

  // Extracting time components
  const hours = String(dateTime.getHours()).padStart(2, "0");
  const minutes = String(dateTime.getMinutes()).padStart(2, "0");
  const seconds = String(dateTime.getSeconds()).padStart(2, "0");

  // Forming time string in the format HHMMSS
  const timeString = `${hours}${minutes}${seconds}`;

  return { date: dateString, time: timeString };
}

function getImageDimensions(
  images: HTMLImageElement[],
  fallback: { width: number; height: number } = { width: 0, height: 0 },
) {
  if (!images.length) return { width: fallback.width, height: fallback.height };
  let width = 0,
    height = 0;
  images.forEach((img) => {
    width += img.naturalWidth;
    height = img.naturalHeight;
  });
  return { width, height };
}

const DEFAULT_SAMPLE_FRAME_ID = 14;

type RecordingQuadrant = "SW" | "NE" | "NW" | "SE";

interface ParsedRecordingFilename {
  cellId?: number;
  date?: string;
  time?: string;
  sampleFrameId: number;
  quadrant?: RecordingQuadrant;
}

function parseSampleFrameIdFromFilename(filename: string) {
  const match = filename.match(/sampleframeid(?:[:=_-]?)(\d+)/i);
  if (!match?.[1]) {
    return DEFAULT_SAMPLE_FRAME_ID;
  }
  return parseInt(match[1], 10);
}

function parseRecordingFilename(
  filename: string,
): ParsedRecordingFilename | null {
  const regexPattern = /^(\d+)_(.+)_(\d{8})_(\d{6})(?:_(.*))?$/;
  const match = filename.match(regexPattern);
  if (!match) {
    return null;
  }

  const firstToken = match[1];
  const labelName = match[2];
  const baseDate = match[3];
  const timestamp = match[4];
  const date = `${baseDate.slice(0, 4)}-${baseDate.slice(4, 6)}-${baseDate.slice(6, 8)}`;
  const secondTokenIsNumeric = /^\d+$/.test(labelName);
  const cellId = parseInt(secondTokenIsNumeric ? labelName : firstToken, 10);
  const quadrant = (
    ["SW", "NE", "NW", "SE"].includes(labelName) ? labelName : undefined
  ) as RecordingQuadrant | undefined;
  const sampleFrameId = secondTokenIsNumeric
    ? parseInt(firstToken, 10)
    : parseSampleFrameIdFromFilename(filename);

  return {
    cellId,
    date,
    time: timestamp,
    sampleFrameId,
    quadrant,
  };
}

export {
  DEFAULT_SAMPLE_FRAME_ID,
  getCurrentTime,
  extractDateTimeComponents,
  getImageDimensions,
  parseSampleFrameIdFromFilename,
  parseRecordingFilename,
};
