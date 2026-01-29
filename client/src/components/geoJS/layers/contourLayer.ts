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

export default class ContourLayer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  spectroInfo: SpectroInfo;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  contourLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  features: any[];

  colorScheme: (t: number) => string;

  maxLevel: number;

  scaledHeight: number;

  scaledWidth: number;

  computedPulseAnnotations: ComputedPulseAnnotation[];

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
    computedPulseAnnotations: ComputedPulseAnnotation[],
    colorScheme: (t: number) => string,
  ) {
    this.geoViewerRef = geoViewerRef;
    this.event = event;
    this.spectroInfo = spectroInfo;
    this.scaledHeight = this.spectroInfo.height;
    this.scaledWidth = this.spectroInfo.width;
    this.colorScheme = colorScheme;
    this.computedPulseAnnotations = computedPulseAnnotations;
    this.features = [];
    this.maxLevel = 0;
    this.init();
  }

  setScaledDimensions(scaledWidth: number, scaledHeight: number) {
    this.scaledWidth = scaledWidth;
    this.scaledHeight = scaledHeight;
    this.removeContours();
    this.drawContours();
  }

  init() {
    if (!this.contourLayer) {
      this.contourLayer = this.geoViewerRef.createLayer('feature');
    }
  }

  destroy() {
    if (this.contourLayer) {
      this.geoViewerRef.deleteLayer(this.contourLayer);
    }
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
      .style(this.getContourStyle())
      .draw();
    this.features.push(polygonFeature);
  }

  removeContours() {
    if (!this.contourLayer) return;
    this.features.forEach((feature) => {
      feature.data([]).draw();
   });
    this.contourLayer.draw();
  }

  drawContours() {
    this.computedPulseAnnotations.forEach((annotation: ComputedPulseAnnotation) => annotation.contours.forEach((contour: Contour) => {
      if (contour.level > this.maxLevel) {
        this.maxLevel = contour.level;
      }
    }));
    this.computedPulseAnnotations.forEach((pulseAnnotation: ComputedPulseAnnotation) => this.drawPolygonsForPulse(pulseAnnotation.contours));
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
      uniformPolygon: true,
      stroke: false,
      fillColor: (_val: number, _idx: number, coords: number[][]) => {
        return  this.colorScheme((coords[0][2] || 0) / this.maxLevel);
      },
      fillOpacity: 1.0,
    };
  }

  setColorScheme(colorScheme: (t: number) => string) {
    this.colorScheme = colorScheme;
    // Redraw
    this.removeContours();
    this.drawContours();
  }
}