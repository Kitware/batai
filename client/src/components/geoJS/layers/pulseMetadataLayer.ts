import { SpectroInfo } from '../geoJSUtils';
import { PulseMetadata } from '@api/api';
import { LayerStyle, LineData, TextData } from './types';

/** Point data for char_freq, knee, heel with pixel coords and label. */
interface PulsePointData {
  x: number;
  y: number;
  label: string;
}

export interface PulseMetadataStyle {
  lineColor: string;
  lineWidth: number;
  durationFreqLineColor: string;
  heelColor: string;
  charFreqColor: string;
  kneeColor: string;
  pointRadius: number;
  showLabels: boolean;
}

const defaultPulseMetadataStyle: PulseMetadataStyle = {
  lineColor: '#00FFFF',
  lineWidth: 2,
  durationFreqLineColor: '#FFFF00',
  heelColor: '#FF0088',
  charFreqColor: '#00FF00',
  kneeColor: '#FF8800',
  pointRadius: 5,
  showLabels: true,
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
  featureTextLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pointLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;
  lineData: LineData[] = [];
  pointData: PulsePointData[] = [];
  labelData: TextData[] = [];
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
    this.featureTextLayer = this.geoViewerRef.createLayer('feature', {
      features: ['text'],
    });
    this.lineLayer = this.featureLayer.createFeature('line');
    this.pointLayer = this.featureLayer.createFeature('point');
    this.textLayer = this.featureTextLayer
      .createFeature('text')
      .text((d: TextData) => d.text)
      .position((d: TextData) => ({ x: d.x, y: d.y }));
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
    this.labelData = [];
    if (!this.spectroInfo.compressedWidth || !this.pulseMetadataList.length) {
      return;
    }
    const labelOffset = 8;
    const freqLineOffsetX = 4;

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

        const times = pulse.curve.map((pt) => pt[0]);
        const freqs = pulse.curve.map((pt) => pt[1]);
        const startTime = Math.min(...times);
        const endTime = Math.max(...times);
        const minFreq = Math.min(...freqs);
        const maxFreq = Math.max(...freqs);
        const durationMs = endTime - startTime;

        const bottomLeft = this.getCompressedPosition(startTime, minFreq, index);
        const bottomRight = this.getCompressedPosition(endTime, minFreq, index);
        const topLeft = this.getCompressedPosition(startTime, maxFreq, index);

        this.lineData.push({
          line: {
            type: 'LineString',
            coordinates: [
              [bottomLeft.x, bottomLeft.y],
              [bottomRight.x, bottomRight.y],
            ],
          },
          lineKind: 'durationFreq',
        });

        this.lineData.push({
          line: {
            type: 'LineString',
            coordinates: [
              [topLeft.x - freqLineOffsetX, topLeft.y],
              [bottomLeft.x - freqLineOffsetX, bottomLeft.y],
            ],
          },
          lineKind: 'durationFreq',
        });

        const durationMidX = (bottomLeft.x + bottomRight.x) / 2;
        this.labelData.push({
          text: `${durationMs.toFixed(1)} ms`,
          x: durationMidX,
          y: bottomLeft.y + labelOffset,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'center',
        });

        this.labelData.push({
          text: `${(maxFreq / 1000).toFixed(1)} kHz`,
          x: topLeft.x - freqLineOffsetX - labelOffset,
          y: topLeft.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'end',
        });
        this.labelData.push({
          text: `${(minFreq / 1000).toFixed(1)} kHz`,
          x: bottomLeft.x - freqLineOffsetX - labelOffset,
          y: bottomLeft.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'end',
        });
      }
      if (pulse.char_freq && pulse.char_freq.length >= 2) {
        const pos = this.getCompressedPosition(pulse.char_freq[0], pulse.char_freq[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'char_freq' });
      }
      if (pulse.knee && pulse.knee.length >= 2) {
        const pos = this.getCompressedPosition(pulse.knee[0], pulse.knee[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'knee' });
        const kneeFreqKhz = (pulse.knee[1] / 1000).toFixed(1);
        this.labelData.push({
          text: `Knee ${kneeFreqKhz} kHz`,
          x: pos.x + 8,
          y: pos.y,
        });
      }
      if (pulse.heel && pulse.heel.length >= 2) {
        const pos = this.getCompressedPosition(pulse.heel[0], pulse.heel[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'heel' });
        const heelFreqKhz = (pulse.heel[1] / 1000).toFixed(1);
        this.labelData.push({
          text: `Heel ${heelFreqKhz} kHz`,
          x: pos.x + 8,
          y: pos.y,
        });
      }
      if (pulse.char_freq && pulse.char_freq.length >= 2) {
        const pos = this.getCompressedPosition(pulse.char_freq[0], pulse.char_freq[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'char_freq' });
        const charFreqKhz = (pulse.char_freq[1] / 1000).toFixed(1);
        this.labelData.push({
          text: `Char ${charFreqKhz} kHz`,
          x: pos.x + 8,
          y: pos.y,
        });
      }
    });
  }

  createLineStyle(): LayerStyle<LineData> {
    const { lineColor, lineWidth, durationFreqLineColor } = this.style;
    return {
      strokeColor: (_point, _index, d: LineData) =>
        d.lineKind === 'durationFreq' ? durationFreqLineColor : lineColor,
      strokeWidth: lineWidth,
      strokeOpacity: (_point, _index, d: LineData) => {
        if (!this.style.showLabels && d.lineKind === 'durationFreq') {
          return 0;
        }
        return 1.0;
      },

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

  createLabelStyle(): LayerStyle<TextData> {
    return {
      fontSize: '12px',
      color: () => '#FFFFFF',
      strokeColor: '#000000',
      strokeWidth: 1,
      stroke: true,
      fill: false,
      textAlign: (d: TextData) => d.textAlign ?? 'start',
      textBaseline: 'middle',
      offset: (d: TextData) => ({ x: d.offsetX ?? 0, y: d.offsetY ?? 0 }),
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
    if (this.style.showLabels) {
      this.textLayer
        .data(this.labelData)
        .style(this.createLabelStyle())
        .draw();
    } else {
      this.textLayer.data([]).draw();
    }
  }

  disable() {
    this.lineLayer.data([]).draw();
    this.pointLayer.data([]).draw();
    this.textLayer.data([]).draw();
  }

  destroy() {
    if (this.featureLayer) {
      this.geoViewerRef.deleteLayer(this.featureLayer);
    }
    if (this.featureTextLayer) {
      this.geoViewerRef.deleteLayer(this.featureTextLayer);
    }
  }
}
