import { SpectroInfo } from '../geoJSUtils';
import { PulseMetadata } from '@api/api';
import { LayerStyle, LineData } from './types';

/** Point data for char_freq, knee, heel with pixel coords and label. */
interface PulsePointData {
  x: number;
  y: number;
  label: string;
}

export interface PulseMetadataStyle {
  lineColor: string;
  lineWidth: number;
  heelColor: string;
  charFreqColor: string;
  kneeColor: string;
  pointRadius: number;
}

const defaultPulseMetadataStyle: PulseMetadataStyle = {
  lineColor: '#00FFFF',
  lineWidth: 2,
  heelColor: '#FF0088',
  charFreqColor: '#00FF00',
  kneeColor: '#FF8800',
  pointRadius: 5,
};

export default class PulseMetadataLayer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;
  spectroInfo: SpectroInfo;
  scaledWidth: number;
  scaledHeight: number;
  pulseMetadataList: PulseMetadata[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  featureLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pointLayer: any;
  lineData: LineData[] = [];
  pointData: PulsePointData[] = [];
  style: PulseMetadataStyle = { ...defaultPulseMetadataStyle };

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    spectroInfo: SpectroInfo,
    pulseMetadataList: PulseMetadata[],
  ) {
    this.geoViewerRef = geoViewerRef;
    this.spectroInfo = spectroInfo;
    this.scaledWidth = spectroInfo.width;
    this.scaledHeight = spectroInfo.height;
    this.pulseMetadataList = pulseMetadataList;
    this.featureLayer = this.geoViewerRef.createLayer('feature', {
      features: ['line', 'point'],
    });
    this.lineLayer = this.featureLayer.createFeature('line');
    this.pointLayer = this.featureLayer.createFeature('point');
  }

  setScaledDimensions(scaledWidth: number, scaledHeight: number) {
    this.scaledWidth = scaledWidth;
    this.scaledHeight = scaledHeight;
    this.formatData();
    this.redraw();
  }

  setPulseMetadataList(pulseMetadataList: PulseMetadata[]) {
    this.pulseMetadataList = pulseMetadataList;
    this.formatData();
    this.redraw();
  }

  setStyle(style: Partial<PulseMetadataStyle>) {
    this.style = { ...defaultPulseMetadataStyle, ...this.style, ...style };
  }

  getCompressedPosition(time: number, freq: number, index: number): { x: number; y: number } {
    if (
      !this.spectroInfo.start_times
      || !this.spectroInfo.end_times
      || !this.spectroInfo.widths
      || !this.spectroInfo.compressedWidth
    ) {
      return { x: 0, y: 0 };
    }
    const scaleFactor = this.scaledWidth / this.spectroInfo.compressedWidth;
    const startTime = this.spectroInfo.start_times[index];
    const endTime = this.spectroInfo.end_times[index];
    const targetTime = Math.min(time, endTime);
    const width = this.spectroInfo.widths[index];
    let segmentOffset = 0;
    for (let i = 0; i < index; i++) {
      segmentOffset += this.spectroInfo.widths[i] * scaleFactor;
    }
    const pixelsPerMs = width / (endTime - startTime);
    const x = segmentOffset + (targetTime - startTime) * pixelsPerMs * scaleFactor;
    const y = this._getYValueFromFrequency(freq);
    return { x, y };
  }

  _getYValueFromFrequency(freq: number): number {
    const freqRange = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const height = Math.max(this.scaledHeight, this.spectroInfo.height);
    const pixelsPerMhz = height / freqRange;
    return (this.spectroInfo.high_freq - freq) * pixelsPerMhz;
  }

  formatData() {
    this.lineData = [];
    this.pointData = [];
    if (!this.spectroInfo.compressedWidth || !this.pulseMetadataList.length) {
      return;
    }
    this.pulseMetadataList.forEach((pulse: PulseMetadata) => {
      const index = pulse.index;
      if (pulse.curve && pulse.curve.length >= 2) {
        const coords: [number, number][] = pulse.curve.map((pt) => {
          const pos = this.getCompressedPosition(pt[0], pt[1], index);
          return [pos.x, pos.y];
        });
        this.lineData.push({
          line: { type: 'LineString', coordinates: coords },
        });
      }
      if (pulse.char_freq && pulse.char_freq.length >= 2) {
        const pos = this.getCompressedPosition(pulse.char_freq[0], pulse.char_freq[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'char_freq' });
      }
      if (pulse.knee && pulse.knee.length >= 2) {
        const pos = this.getCompressedPosition(pulse.knee[0], pulse.knee[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'knee' });
      }
      if (pulse.heel && pulse.heel.length >= 2) {
        const pos = this.getCompressedPosition(pulse.heel[0], pulse.heel[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'heel' });
      }
    });
  }

  createLineStyle(): LayerStyle<LineData> {
    const { lineColor, lineWidth } = this.style;
    return {
      strokeColor: lineColor,
      strokeWidth: lineWidth,
      stroke: true,
      fill: false,
    };
  }

  createPointStyle(): LayerStyle<PulsePointData> {
    const { heelColor, charFreqColor, kneeColor, pointRadius } = this.style;
    return {
      fillColor: (d: PulsePointData) => {
        if (d.label === 'char_freq') return charFreqColor;
        if (d.label === 'knee') return kneeColor;
        if (d.label === 'heel') return heelColor;
        return '#FFFFFF';
      },
      fill: true,
      stroke: true,
      strokeColor: '#FFFFFF',
      strokeWidth: 1,
      radius: pointRadius,
    };
  }

  redraw() {
    this.formatData();
    this.lineLayer
      .data(this.lineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    this.pointLayer
      .data(this.pointData)
      .position((d: PulsePointData) => ({ x: d.x, y: d.y }))
      .style(this.createPointStyle())
      .draw();
  }

  disable() {
    this.lineLayer.data([]).draw();
    this.pointLayer.data([]).draw();
  }

  destroy() {
    if (this.featureLayer) {
      this.geoViewerRef.deleteLayer(this.featureLayer);
    }
  }
}
