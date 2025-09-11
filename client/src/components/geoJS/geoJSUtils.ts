import { ref, Ref } from "vue";
import geo from "geojs";

const useGeoJS = () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const geoViewer: Ref<any> = ref();
  const container: Ref<HTMLElement | undefined> = ref();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const quadFeatures: any[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let quadFeatureLayer: any;

  const thumbnail = ref(false);

  let originalBounds = {
    left: 0,
    top: 0,
    bottom: 1,
    right: 1,
  };

  let originalDimensions = { width: 0, height: 0 };

  const getGeoViewer = () => {
    return geoViewer;
  };

  const destroyGeoViewer = () => {
    if (geoViewer.value) {
      geoViewer.value.exit();
    }
  };

  const clearQuadFeatures = () => {
    quadFeatures.forEach((feature) => {
      if (quadFeatureLayer) {
        quadFeatureLayer.removeFeature(feature);
      }
    });
    quadFeatures.splice(0, quadFeatures.length);
  };

  const initializeViewer = (
    sourceContainer: HTMLElement,
    width: number,
    height: number,
    thumbnailVal = false,
    imageCount = 1
  ) => {
    thumbnail.value = thumbnailVal;
    container.value = sourceContainer;
    originalDimensions = { width, height };
    const params = geo.util.pixelCoordinateParams(container.value, width, height);
    if (!container.value) {
      return;
    }
    geoViewer.value = geo.map(params.map);
    resetMapDimensions(width, height);
    const interactorOpts = geoViewer.value.interactor().options();
    interactorOpts.keyboard.focusHighlight = false;
    interactorOpts.keyboard.actions = {};
    interactorOpts.click.cancelOnMove = 5;
    interactorOpts.actions = [
      interactorOpts.actions[0],
      // The action below is needed to have GeoJS use the proper handler
      // with cancelOnMove for right clicks
      {
        action: geo.geo_action.select,
        input: { right: true },
        name: "button edit",
        owner: "geo.MapInteractor",
      },
      // The action below adds middle mouse button click to panning
      // It allows for panning while in the process of polygon editing or creation
      {
        action: geo.geo_action.pan,
        input: "middle",
        modifiers: { shift: false, ctrl: false },
        owner: "geo.mapInteractor",
        name: "button pan",
      },
      interactorOpts.actions[2],
      interactorOpts.actions[6],
      interactorOpts.actions[7],
      interactorOpts.actions[8],
      interactorOpts.actions[9],
    ];
    // Set > 2pi to disable rotation
    interactorOpts.zoomrotateMinimumRotation = 7;
    interactorOpts.zoomAnimation = {
      enabled: false,
    };
    interactorOpts.momentum = {
      enabled: false,
    };
    interactorOpts.wheelScaleY = 0.2;
    if (thumbnail.value) {
      interactorOpts.actions = [
        {
          action: "overview_pan",
          input: "left",
          modifiers: { shift: false, ctrl: false },
          name: "button pan",
        },
      ];
    }
    geoViewer.value.interactor().options(interactorOpts);
    geoViewer.value.bounds({
      left: 0,
      top: 0,
      bottom: height,
      right: width,
    });
    if (!quadFeatureLayer) {
      quadFeatureLayer = geoViewer.value.createLayer("feature", {
        features: ["quad"],
        autoshareRenderer: false,
        renderer: "canvas",
      });
    }
    clearQuadFeatures();
    quadFeatureLayer.node().css("filter", "url(#apply-color-scheme)");
    for (let i = 0; i < imageCount; i += 1) {
      quadFeatures.push(quadFeatureLayer.createFeature("quad"));
    }
  };

  const drawImages = (images: HTMLImageElement[], width = 0, height = 0, resetCam = true) => {
    let previousWidth = 0;
    let totalBaseWidth = 0;
    images.forEach((image) => (totalBaseWidth += image.naturalWidth));
    images.forEach((image, index) => {
      const scaledWidth = width / totalBaseWidth;
      const currentWidth = image.width * scaledWidth;
      if (quadFeatures[index] === undefined) {
        quadFeatures[index] = quadFeatureLayer.createFeature("quad");
      }
      quadFeatures[index]
        .data([
          {
            ul: { x: previousWidth, y: 0 },
            lr: { x: previousWidth + currentWidth, y: height },
            image: image,
          },
        ])
        .draw();
      previousWidth += currentWidth;
    });
    if (resetCam) {
      resetMapDimensions(width, height, 0.3, resetCam);
    } else {
      const params = geo.util.pixelCoordinateParams(container.value, width, height);
      const margin = 0.3;
      const { right, bottom } = params.map.maxBounds;
      originalBounds = params.map.maxBounds;
      geoViewer.value.maxBounds({
        left: 0 - right * margin,
        top: 0 - bottom * margin,
        right: right * (1 + margin),
        bottom: bottom * (1 + margin),
      });
    }
  };
  const resetZoom = () => {
    const { width: mapWidth } = geoViewer.value.camera().viewport;

    const bounds = !thumbnail.value
      ? {
          left: 0, // Making sure the legend is on the screen
          top: -(originalBounds.bottom - originalDimensions.height) / 2.0,
          right: mapWidth * 2,
          bottom: originalBounds.bottom,
        }
      : {
          left: 0,
          top: 0,
          right: originalDimensions.width,
          bottom: originalDimensions.height,
        };
    const zoomAndCenter = geoViewer.value.zoomAndCenterFromBounds(bounds, 0);
    geoViewer.value.zoom(zoomAndCenter.zoom);
    geoViewer.value.center(zoomAndCenter.center);
  };

  const resetMapDimensions = (width: number, height: number, margin = 0.3, resetCam = false) => {
    // Want the height to be the main view and whe width to be  relative to the width of the geo.amp
    geoViewer.value.bounds({
      left: 0,
      top: 0,
      bottom: height,
      right: width,
    });
    const params = geo.util.pixelCoordinateParams(container.value, width, height, width, height);
    const { right, bottom } = params.map.maxBounds;
    geoViewer.value.maxBounds({
      left: 0 - right * margin,
      top: 0 - bottom * margin,
      right: right * (1 + margin),
      bottom: bottom * (1 + margin),
    });
    originalBounds = geoViewer.value.maxBounds();
    geoViewer.value.zoomRange({
      // do not set a min limit so that bounds clamping determines min
      min: -Infinity,
      // 4x zoom max
      max: 20,
    });
    geoViewer.value.clampBoundsX(true);
    geoViewer.value.clampBoundsY(true);
    geoViewer.value.clampZoom(true);
    if (resetCam) {
      resetZoom();
    }
  };

  return {
    getGeoViewer,
    initializeViewer,
    drawImages,
    resetMapDimensions,
    resetZoom,
    destroyGeoViewer,
  };
};

import { SpectrogramAnnotation, SpectrogramSequenceAnnotation } from "../../api/api";

export interface SpectroInfo {
  spectroId: number;
  width: number;
  height: number;
  start_time: number;
  end_time: number;
  start_times?: number[];
  end_times?: number[];
  widths?: number[]; //widths of segements
  compressedWidth?: number;
  low_freq: number;
  high_freq: number;
}

function spectroSequenceToGeoJSon(
  annotation: SpectrogramSequenceAnnotation,
  spectroInfo: SpectroInfo,
  ymin = 0,
  ymax = 10,
  yScale = 1,
  scaledWidth = 0,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _scaledHeight = 0, // may be useful in the future
  offsetY = 0 // used to push sequence annotations higher when viewing in compressed view
): GeoJSON.Polygon {
  const adjustedWidth = scaledWidth > spectroInfo.width ? scaledWidth : spectroInfo.width;
  // const adjustedHeight = scaledHeight > spectroInfo.height ? scaledHeight : spectroInfo.height;
  //scale pixels to time and frequency ranges
  if (spectroInfo.compressedWidth === undefined) {
    const widthScale = adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time);
    // Now we remap our annotation to pixel coordinates
    const start_time = annotation.start_time * widthScale;
    const end_time = annotation.end_time * widthScale;
    return {
      type: "Polygon",
      coordinates: [
        [
          [start_time, ymin * yScale],
          [start_time, ymax * yScale],
          [end_time, ymax * yScale],
          [end_time, ymin * yScale],
          [start_time, ymin * yScale],
        ],
      ],
    };
  } else if (spectroInfo.compressedWidth && spectroInfo.start_times && spectroInfo.end_times) {
    // Compressed Spectro has different conversion
    // Find what section the annotation is in
    const start = annotation.start_time;
    const end = annotation.end_time;
    const { start_times, end_times, widths } = spectroInfo;
    const lengths = start_times.length === end_times.length ? start_times.length : 0;
    let foundStartIndex = -1;
    let foundEndIndex = -1;
    if (start < start_times[0]) {
      foundStartIndex = 0;
    }
    let totalTime = 0;
    let startOutside = true; // if Start is outside a compressed view
    let endOutside = true; // if end is outside a compressed view
    for (let i = 0; i < lengths; i += 1) {
      if (foundStartIndex === -1) {
        if (start < start_times[i]) {
          foundStartIndex = i; // Lock to the current index if before the interval
        } else if (start_times[i] <= start && start <= end_times[i]) {
          foundStartIndex = i; // Found within the interval
          startOutside = false;
        } else if (i === lengths - 1 && start > end_times[i]) {
          foundStartIndex = i; // Lock to the last interval's end
        }
      }
      totalTime += end_times[i] - start_times[i];

      // Check for end time
      if (foundEndIndex === -1) {
        if (end < start_times[i]) {
          foundEndIndex = i; // Lock to the current index if before the interval
        } else if (start_times[i] <= end && end <= end_times[i]) {
          foundEndIndex = i; // Found within the interval
          endOutside = false;
        } else if (i === lengths - 1 && end > end_times[i]) {
          foundEndIndex = i; // Lock to the last interval's end
        }
      }
    }
    // We need to build the length of times to pixel size for the time spaces before the annotation
    let timeAddStart = 0;
    let timeAddEnd = 0;
    // Total width from widths
    for (let i = 0; i < Math.max(foundStartIndex, foundEndIndex); i += 1) {
      const addWidth = widths && widths[i];
      if (addWidth && i < foundStartIndex) {
        timeAddStart += addWidth;
      }
      if (addWidth && i < foundEndIndex) {
        timeAddEnd += addWidth;
      }
    }
    // Now we remap our annotation to pixel coordinates

    // lets calcualte a pixels per ms for the copressed view

    const compressedWidth =
      scaledWidth > (spectroInfo.compressedWidth || 1)
        ? scaledWidth
        : spectroInfo.compressedWidth || spectroInfo.width;
    const pixelPerMS = compressedWidth / totalTime;
    const xScaling = compressedWidth / spectroInfo.compressedWidth;
    const start_time =
      timeAddStart * xScaling +
      (!startOutside ? (annotation.start_time - start_times[foundStartIndex]) * pixelPerMS : 0);

    const end_time =
      timeAddEnd * xScaling +
      (!endOutside ? (annotation.end_time - start_times[foundEndIndex]) * pixelPerMS : 0);
    return {
      type: "Polygon",
      coordinates: [
        [
          [start_time, ymin * yScale + offsetY],
          [start_time, ymax * yScale + offsetY],
          [end_time, ymax * yScale + offsetY],
          [end_time, ymin * yScale + offsetY],
          [start_time, ymin * yScale + offsetY],
        ],
      ],
    };
  }
  return {
    type: "Polygon",
    coordinates: [
      [
        [-1, -1],
        [-1, -1],
        [-1, -1],
        [-1, -1],
        [-1, -1],
      ],
    ],
  };
}

function spectroToGeoJSon(
  annotation: SpectrogramAnnotation,
  spectroInfo: SpectroInfo,
  yScale = 1,
  scaledWidth = 0,
  scaledHeight = 0
): GeoJSON.Polygon {
  //scale pixels to time and frequency ranges
  const adjustedWidth = scaledWidth > spectroInfo.width ? scaledWidth : spectroInfo.width;
  const adjustedHeight = scaledHeight > spectroInfo.height ? scaledHeight : spectroInfo.height;

  if (spectroInfo.compressedWidth === undefined) {
    const widthScale = adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time);
    const heightScale = adjustedHeight / (spectroInfo.high_freq - spectroInfo.low_freq);
    // Now we remap our annotation to pixel coordinates
    const low_freq = adjustedHeight - (annotation.low_freq - spectroInfo.low_freq) * heightScale;
    const high_freq = adjustedHeight - (annotation.high_freq - spectroInfo.low_freq) * heightScale;
    const start_time = annotation.start_time * widthScale;
    const end_time = annotation.end_time * widthScale;
    return {
      type: "Polygon",
      coordinates: [
        [
          [start_time, low_freq * yScale],
          [start_time, high_freq * yScale],
          [end_time, high_freq * yScale],
          [end_time, low_freq * yScale],
          [start_time, low_freq * yScale],
        ],
      ],
    };
  } else if (spectroInfo.compressedWidth && spectroInfo.start_times && spectroInfo.end_times) {
    // Compressed Spectro has different conversion
    // Find what section the annotation is in
    const start = annotation.start_time;
    const end = annotation.end_time;
    const { start_times, end_times, widths } = spectroInfo;
    const lengths = start_times.length === end_times.length ? start_times.length : 0;
    let foundStartIndex = -1;
    let foundEndIndex = -1;
    for (let i = 0; i < lengths; i += 1) {
      if (foundStartIndex === -1 && start_times[i] < start && start < end_times[i]) {
        foundStartIndex = i;
      }
      if (foundEndIndex === -1 && start_times[i] < end && end < end_times[i]) {
        foundEndIndex = i;
      }
    }
    // We need to build the length of times to pixel size for the time spaces before the annotation
    const compressedScale =
      scaledWidth > (spectroInfo.compressedWidth || 1)
        ? scaledWidth / (spectroInfo.compressedWidth || spectroInfo.width)
        : 1;
    const widthScale =
      (adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time)) * compressedScale;
    let pixelAddStart = 0;
    let pixelAddEnd = 0;
    for (let i = 0; i < Math.max(foundStartIndex, foundEndIndex); i += 1) {
      const addWidth = widths && widths[i];
      if (addWidth && i < foundStartIndex) {
        pixelAddStart += addWidth;
      }
      if (addWidth && i < foundEndIndex) {
        pixelAddEnd += addWidth;
      }
    }
    const heightScale = adjustedHeight / (spectroInfo.high_freq - spectroInfo.low_freq);
    // Now we remap our annotation to pixel coordinates
    const low_freq = adjustedHeight - (annotation.low_freq - spectroInfo.low_freq) * heightScale;
    const high_freq = adjustedHeight - (annotation.high_freq - spectroInfo.low_freq) * heightScale;
    const start_time =
      pixelAddStart * compressedScale +
      (annotation.start_time - start_times[foundStartIndex]) * widthScale;
    const end_time =
      pixelAddEnd * compressedScale +
      (annotation.end_time - start_times[foundEndIndex]) * widthScale;

    return {
      type: "Polygon",
      coordinates: [
        [
          [start_time, low_freq * yScale],
          [start_time, high_freq * yScale],
          [end_time, high_freq * yScale],
          [end_time, low_freq * yScale],
          [start_time, low_freq * yScale],
        ],
      ],
    };
  }
  return {
    type: "Polygon",
    coordinates: [
      [
        [-1, -1],
        [-1, -1],
        [-1, -1],
        [-1, -1],
        [-1, -1],
      ],
    ],
  };
}

function findPolygonCenter(polygon: GeoJSON.Polygon): number[] {
  const coordinates = polygon.coordinates[0]; // Extract the exterior ring coordinates

  // Calculate the average of longitude and latitude separately
  const avgLng = coordinates.reduce((sum, point) => sum + point[0], 0) / coordinates.length;
  const avgLat = coordinates.reduce((sum, point) => sum + point[1], 0) / coordinates.length;

  return [avgLng, avgLat];
}

function spectroToCenter(
  annotation: SpectrogramAnnotation | SpectrogramSequenceAnnotation,
  spectroInfo: SpectroInfo,
  type: "sequence" | "pulse"
) {
  if (type === "pulse") {
    const geoJSON = spectroToGeoJSon(annotation as SpectrogramAnnotation, spectroInfo);
    return findPolygonCenter(geoJSON);
  }
  if (type === "sequence") {
    const geoJSON = spectroSequenceToGeoJSon(
      annotation as SpectrogramSequenceAnnotation,
      spectroInfo
    );
    return findPolygonCenter(geoJSON);
  }
  return [0, 0];
}

/* beginning at bottom left, rectangle is defined clockwise */
function geojsonToSpectro(
  geojson: GeoJSON.Feature<GeoJSON.Polygon>,
  spectroInfo: SpectroInfo,
  scaledWidth = 0,
  scaledHeight = 0,
): { error?: string; start_time: number; end_time: number; low_freq: number; high_freq: number } {
  const adjustedWidth = scaledWidth > spectroInfo.width ? scaledWidth : spectroInfo.width;
  const adjustedHeight = scaledHeight > spectroInfo.height ? scaledHeight : spectroInfo.height;

  const coords = geojson.geometry.coordinates[0];
  if (spectroInfo.compressedWidth === undefined) {
    const widthScale = adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time);
    const heightScale = adjustedHeight / (spectroInfo.high_freq - spectroInfo.low_freq);
    const start_time = Math.round(coords[1][0] / widthScale);
    const end_time = Math.round(coords[3][0] / widthScale);
    const high_freq = Math.round(spectroInfo.high_freq - coords[1][1] / heightScale);
    const low_freq = Math.round(spectroInfo.high_freq - coords[3][1] / heightScale);
    return {
      start_time,
      end_time,
      low_freq,
      high_freq,
    };
  } else if (spectroInfo.start_times && spectroInfo.end_times) {
    // first need to map the X positions to times based on the start/endtimes
    const compressedScale =
      scaledWidth > (spectroInfo.compressedWidth || 1)
        ? scaledWidth / (spectroInfo.compressedWidth || spectroInfo.width)
        : 1;
    let start = coords[1][0] / compressedScale;
    let end = coords[3][0] / compressedScale;
    if (start < 0) {
      start = 0;
    }
    if (end > spectroInfo.compressedWidth) {
      end = spectroInfo.compressedWidth;
    }
    const { start_times, widths } = spectroInfo;
    const timeToPixels = adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time);
    let additivePixels = 0;
    let start_time = -1;
    let end_time = -1;
    for (let i = 0; i < start_times.length; i += 1) {
      // convert the start/end time to a pixel
      const nextPixels = (widths && widths[i]) || 0;
      if (start_time === -1 && start >= additivePixels && start < additivePixels + nextPixels) {
        // Found the location for time markers
        // We need to remap pixels back to milliseconds
        const lowPixels = start - additivePixels;
        const lowTime = start_times[i] + lowPixels / timeToPixels;
        start_time = Math.round(lowTime);
      }
      if (
        end_time === -1 &&
        start_time !== -1 &&
        end > additivePixels &&
        end < additivePixels + nextPixels
      ) {
        const highPixels = end - additivePixels;
        const highTime = start_times[i] + highPixels / timeToPixels;
        end_time = Math.round(highTime);
      }
      additivePixels += nextPixels;
    }
    const heightScale = adjustedHeight / (spectroInfo.high_freq - spectroInfo.low_freq);
    const high_freq = Math.round(spectroInfo.high_freq - coords[1][1] / heightScale);
    const low_freq = Math.round(spectroInfo.high_freq - coords[3][1] / heightScale);
    if (start_time === -1 || end_time === -1) {
      // the time spreads across multiple pulses and isn't allowed;
      return {
        error:
          "Start or End Time spread across pusles.  This is not allowed in compressed annotations",
        start_time,
        end_time,
        low_freq,
        high_freq,
      };
    }
    return {
      start_time,
      end_time,
      low_freq,
      high_freq,
    };
  }
  return {
    error: "Spectrogram Info didn't match a regular or compressed view",
    start_time: 0,
    end_time: 0,
    low_freq: 0,
    high_freq: 0,
  };
}

/**
 * This will take the current geoJSON Coordinates for a rectangle and reorder it
 * to keep the vertices index the same with respect to how geoJS uses it
 * Example: UL, LL, LR, UR, UL
 */
function reOrdergeoJSON(coords: GeoJSON.Position[]) {
  let x1 = Infinity;
  let x2 = -Infinity;
  let y1 = Infinity;
  let y2 = -Infinity;
  coords.forEach((coord) => {
    x1 = Math.min(x1, coord[0]);
    x2 = Math.max(x2, coord[0]);
    y1 = Math.min(y1, coord[1]);
    y2 = Math.max(y2, coord[1]);
  });
  return [
    [x1, y2],
    [x1, y1],
    [x2, y1],
    [x2, y2],
    [x1, y2],
  ];
}

function luminance(r: number, g: number, b: number): number {
  const toLinear = (c: number): number => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };

  const R = toLinear(r);
  const G = toLinear(g);
  const B = toLinear(b);

  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}


function getContrastingColor(r: number, g: number, b: number): "black" | "white" {
  const L = luminance(r, g, b);
  return L > 0.179 ? "black" : "white";
}

function textColorFromBackground(rgbString: string): "black" | "white" {
  const matches = rgbString.match(/\d+/g);
  if (!matches || matches.length < 3) {
    throw new Error("Invalid RGB string format");
  }
  const [r, g, b] = matches.map(Number);
  return getContrastingColor(r, g, b);
}

export {
  spectroToGeoJSon,
  geojsonToSpectro,
  reOrdergeoJSON,
  useGeoJS,
  spectroToCenter,
  spectroSequenceToGeoJSon,
  textColorFromBackground
};
