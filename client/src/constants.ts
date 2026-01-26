const RecordingMimeTypes  = [
  'audio/mpeg',
  'audio/wav',
  'audio/mp4',
  'audio/x-aiff',
  // Add more audio mime types as needed
];

type SpectrogramView = 'image' | 'contour' | 'both';

export {
  RecordingMimeTypes,
  SpectrogramView,
};
