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

  scaledHeight: number;

  scaledWidth: number;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
  ) {
    this.geoViewerRef = geoViewerRef;
    this.event = event;
    this.spectroInfo = spectroInfo;
    this.scaledHeight = this.spectroInfo.height;
    this.scaledWidth = this.spectroInfo.width;
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
      lineData.push({ coord, strokeColor: 'yellow' });
    });
    const lineFeature = this.contourLayer.createFeature('line');
    lineFeature
      .data(lineData)
      .line((item: LineData) => item.coord)
      .position((item: number[]) => ({ x: item[0], y: item[1] }))
      .style({
        strokeColor: 'yellow',
        strokeWidth: 2,
      })
      .draw();
    this.features.push(lineFeature);
  }

  removeFeatures() {
    if (!this.contourLayer) return;
    console.log(this.contourLayer.features());
    this.contourLayer.clear();
    console.log('cleared layer');
    console.log(this.contourLayer.features());
    this.contourLayer.draw();
  }

  drawContours(computedPulseAnnotations: ComputedPulseAnnotation[]) {
    computedPulseAnnotations.forEach((pulseAnnotation: ComputedPulseAnnotation) => this.drawLinesForPulse(pulseAnnotation.contours));
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
}
