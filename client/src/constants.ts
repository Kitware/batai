const RecordingMimeTypes = [
  "audio/mpeg",
  "audio/wav",
  "audio/mp4",
  "audio/x-aiff",
  // Add more audio mime types as needed
];

const DEFAULT_SAMPLE_FRAME_ID = 14;

type SpectrogramView = "image" | "contour" | "both";

export { RecordingMimeTypes, DEFAULT_SAMPLE_FRAME_ID };
export type { SpectrogramView };
