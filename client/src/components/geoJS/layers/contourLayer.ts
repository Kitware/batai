import { SpectroInfo } from '../geoJSUtils';
import {
  ComputedPulseAnnotation,
  Contour,
} from '@api/api';

interface ContourPoint {
  x: number;
  y: number;
  z: number;
}

interface LineData {
  coord: number[][];
  strokeColor?: string;
  level?: number;
}

export default class ContourLayer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  spectroInfo: SpectroInfo;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  contourLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  contourFeature: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  features: any[];

  colorScheme: (t: number) => string;

  maxLevel: number;

  scaledHeight: number;

  scaledWidth: number;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
    colorScheme: (t: number) => string,
  ) {
    this.geoViewerRef = geoViewerRef;
    this.event = event;
    this.spectroInfo = spectroInfo;
    this.scaledHeight = this.spectroInfo.height;
    this.scaledWidth = this.spectroInfo.width;
    this.colorScheme = colorScheme;
    this.maxLevel = 0;
    this.init();
  }

  setScaledDimensions(scaledWidth: number, scaledHeight: number) {
    this.scaledWidth = scaledWidth;
    this.scaledHeight = scaledHeight;
  }

  init() {
    this.contourLayer = this.geoViewerRef.createLayer('feature');
    this.contourFeature = this.contourLayer.createFeature('contour');
    this.features = [];
  }

  drawContoursForPulse(pulse: Contour[]) {
    const data: ContourPoint[] = [];
    pulse.forEach((contour: Contour) => {
      contour.curve.forEach((point: number[]) => {
        data.push(this.getTransformedContourPoint(point, contour.level, contour.index));
      });
    });
    const feature = this.contourLayer.createFeature('contour');
    feature
      .data(data)
      .draw();
    this.features.push(feature);
  }

  drawLinesForPulse(pulse: Contour[]) {
    const lineData: LineData[] = [];
    pulse.forEach((contour: Contour) => {
      const coord: number[][] = [];
      contour.curve.forEach((point: number[]) => {
        const contourPoint = this.getTransformedContourPoint(point, contour.level, contour.index);
        coord.push([contourPoint.x, contourPoint.y]);
      });
      lineData.push({ coord, strokeColor: 'yellow', level: contour.level });
    });
    const lineFeature = this.contourLayer.createFeature('line');
    lineFeature
      .data(lineData)
      .line((item: LineData) => item.coord)
      .position((item: number[]) => ({ x: item[0], y: item[1] }))
      .style({
        strokeColor: (_vertex: number[], _vertexIndex: number, item: LineData) => {
          if (!this.colorScheme) return 'yellow';
          return this.colorScheme((item.level || 0) / this.maxLevel);
        },
        strokeWidth: 2,
        closed: true,
      })
      .draw();
    this.features.push(lineFeature);
  }

  drawPolygonsForPulse(pulse: Contour[]) {
    const polyData: number[][][] = [];
    pulse.sort((a: Contour, b: Contour) => {
      return a.level - b.level;
    }).forEach((contour: Contour) => {
      const newPoly: number[][] = [];
      contour.curve.forEach((point: number[]) => {
        const contourPoint = this.getTransformedContourPoint(point, contour.level, contour.index);
        newPoly.push([contourPoint.x, contourPoint.y, contour.level]);
      });
      polyData.push(newPoly);
    });
    const polygonFeature = this.contourLayer.createFeature('polygon');
    polygonFeature
      .data(polyData)
      .position((item: number[]) => ({ x: item[0], y: item[1] }))
      .style({
        uniformPolygon: true,
        stroke: false,
        fillColor: (_val: number, _idx: number, coords: number[][]) => {
          return this.colorScheme((coords[0][2] ||0) / this.maxLevel);
        },
        fillOpacity: 1.0,
      })
      .draw();
    this.features.push(polygonFeature);
  }

  removeFeatures() {
    if (!this.contourLayer) return;
    this.features.forEach((feature) => {
      feature.data([]).draw();
   });
    this.contourLayer.draw();
  }

  drawContours(computedPulseAnnotations: ComputedPulseAnnotation[]) {
    computedPulseAnnotations.forEach((annotation: ComputedPulseAnnotation) => annotation.contours.forEach((contour: Contour) => {
      if (contour.level > this.maxLevel) {
        this.maxLevel = contour.level;
      }
    }));
    computedPulseAnnotations.forEach((pulseAnnotation: ComputedPulseAnnotation) => this.drawPolygonsForPulse(pulseAnnotation.contours));
  }

   getTransformedContourPoint(point: number[], level: number, index: number): ContourPoint {
    if (this.spectroInfo.compressedWidth) {
      return this._getTransformedContourPointCompressed(point, level, index);
    }
    return this._getTransformedContourPoint(point, level);
  }

  _getYValueFromFrequency(freq: number) {
    const freqRange = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const height = Math.max(this.scaledHeight, this.spectroInfo.height);
    const pixelsPerMhz = height / freqRange;
    return (this.spectroInfo.high_freq - freq) * pixelsPerMhz;
  }

  _getTransformedContourPointCompressed(point: number[], level: number, index: number): ContourPoint {
    if (
      !this.spectroInfo.start_times
      || !this.spectroInfo.end_times
      || !this.spectroInfo.widths
      || !this.spectroInfo.compressedWidth
    ) {
      // Dummy value
      return { x: 0, y: 0, z: 0 };
    }
    const scaleFactor = this.scaledWidth / this.spectroInfo.compressedWidth;
    // Find the segment containing the target time
    const startTime = this.spectroInfo.start_times[index];
    const endTime = this.spectroInfo.end_times[index];
    // If the time for the given point exceeds the end time of the specified segment, clamp to the segment
    const targetTime = Math.min(point[0], endTime);
    // Get the width of the segment
    const width = this.spectroInfo.widths[index];
    // Get the offset of the segment
    let segmentOffset = 0;
    for (let i = 0; i < index; i++) {
      segmentOffset += (this.spectroInfo.widths[i] * scaleFactor);
    }
    // Find the pixelsPerMs and pixel offset
    const pixelsPerMs = width / (endTime - startTime);
    // Calculate final X position for the given time
    const xVal = segmentOffset + ((targetTime - startTime) * pixelsPerMs * scaleFactor);
    return {
      x: xVal,
      y: this._getYValueFromFrequency(point[1]),
      z: level
    };
  }

  _getTransformedContourPoint(point: number[], level: number,): ContourPoint {
    const width = Math.max(this.spectroInfo.width, this.scaledWidth);
    const timeRange = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const pixelsPerMs = width / timeRange;
    const timeOffset = point[0] - this.spectroInfo.start_time;
    return {
      x: timeOffset * pixelsPerMs,
      y: this._getYValueFromFrequency(point[1]),
      z: level
    };
  }

  getContourStyle() {
    return {
      strokeColor: 'yellow',
      strokeWidth: 2,
    };
  }
}
