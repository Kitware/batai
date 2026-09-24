const RecordingMimeTypes = [
  "audio/mpeg",
  "audio/wav",
  "audio/mp4",
  "audio/x-aiff",
  // Add more audio mime types as needed
];

const DEFAULT_SAMPLE_FRAME_ID = 14;

type SpectrogramView = "image" | "contour" | "both";

// Matches a path/URL anywhere under a "nabat" segment, with or without a leading
// slash (e.g. "nabat/authorize", "/nabat/123/spectrogram"). Used anywhere we just
// need to know "is this NABat-related at all".
const NABAT_PATH_REGEX = /^\/?nabat(\/|$)/;

// Matches only the two true external NABat entrypoints - a fresh page load of
// "/nabat/auth/" (NABat's Keycloak redirect target) or "/nabat/:id/" (a direct
// link) - and not deeper client-side routes like "/nabat/:id/spectrogram".
const NABAT_ENTRYPOINT_PATH_REGEX = /^\/nabat\/[^/]+\/?$/;

export { RecordingMimeTypes, DEFAULT_SAMPLE_FRAME_ID, NABAT_PATH_REGEX, NABAT_ENTRYPOINT_PATH_REGEX };
export type { SpectrogramView };
