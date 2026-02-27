import geo, { GeoEvent } from 'geojs';
import { SpectroInfo } from '../geoJSUtils';
import { PulseMetadata } from '@api/api';
import { LayerStyle, LineData, TextData } from './types';
import BaseTextLayer from './baseTextLayer';
import { PulseMetadataLabelsMode } from '@use/usePulseMetadata';

/** Point data for char_freq, knee, heel with pixel coords and label. */
interface PulsePointData {
  x: number;
  y: number;
  label: string;
}

interface HoverHitData {
  polygon: GeoJSON.Polygon;
}

type FreqDurationLineData  = LineData & { index: number };
export interface PulseMetadataStyle {
  lineColor: string;
  lineWidth: number;
  durationFreqLineColor: string;
  heelColor: string;
  charFreqColor: string;
  kneeColor: string;
  labelColor: string;
  labelFontSize: number;
  pointRadius: number;
  pulseMetadataLabels: PulseMetadataLabelsMode;
}

/** Payload for pulse-metadata-tooltip event (display coords). */
export interface PulseMetadataTooltipData {
  durationMs: number;
  fminKhz: number;
  fmaxKhz: number;
  fcKhz: number | null;
  heelColor: string | null;
  kneeColor: string | null;
  charFreqColor: string | null;
  heelKhz: number | null;
  kneeKhz: number | null;
  /** Slope at hi fc:knee (kHz/ms). */
  slopeAtHiFcKneeKhzPerMs: number | null;
  /** Slope at fc (kHz/ms). */
  slopeAtFcKhzPerMs: number | null;
  /** Slope at low fc:heel (kHz/ms). */
  slopeAtLowFcHeelKhzPerMs: number | null;
  bbox: { top: number; left: number; width: number; height: number };
}

const defaultPulseMetadataStyle: PulseMetadataStyle = {
  lineColor: '#00FFFF',
  lineWidth: 2,
  durationFreqLineColor: '#FFFF00',
  heelColor: '#FF0088',
  charFreqColor: '#00FF00',
  kneeColor: '#FF8800',
  labelColor: '#FFFFFF',
  labelFontSize: 12,
  pointRadius: 5,
  pulseMetadataLabels: 'None',
};

export default class PulseMetadataLayer extends BaseTextLayer<TextData> {
  pulseMetadataList: PulseMetadata[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  featureLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  featureTextLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  hoverHitLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  hoverPolygonFeature: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  freqDurationLineLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pointLayer: any;
  lineData: LineData[] = []; // Contour for Pulses
  durationFreqLineData: FreqDurationLineData[] = []; // Duration/frequency range summary for Pulses
  pointData: PulsePointData[] = [];
  /** Per-pulse text items for hover mode. */
  pulseTextData: TextData[][] = [];
  /** Per-pulse bbox polygons for hover hit-testing. */
  hoverHitData: HoverHitData[] = [];
  style: PulseMetadataStyle = { ...defaultPulseMetadataStyle };

  // When false, zoom must not call redraw (user has turned off the layer).
  private enabled = true;

  // Index of pulse currently hovered when pulseMetadataLabels is Hover or Tooltip; -1 when none.
  private hoveredPulseIndex = -1;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
    pulseMetadataList: PulseMetadata[],
  ) {
    super(geoViewerRef, event, spectroInfo);
    this.pulseMetadataList = pulseMetadataList;
    this.featureLayer = this.geoViewerRef.createLayer('feature', {
      features: ['line', 'point'],
    });
    this.featureTextLayer = this.geoViewerRef.createLayer('feature', {
      features: ['text'],
    });
    this.lineLayer = this.featureLayer.createFeature('line');
    this.freqDurationLineLayer = this.featureLayer.createFeature('line');
    this.pointLayer = this.featureLayer.createFeature('point');
    this.textLayer = this.featureTextLayer
      .createFeature('text')
      .text((d: TextData) => d.text)
      .position((d: TextData) => ({ x: d.x, y: d.y }));
    // Below is used for hover hit-testing when showLabelsOnHover is true.
    this.hoverHitLayer = this.geoViewerRef.createLayer('feature', {
      features: ['polygon'],
    });
    this.hoverPolygonFeature = this.hoverHitLayer
      .createFeature('polygon', { selectionAPI: true })
      .polygon((d: HoverHitData) => d.polygon.coordinates[0]);
    this.hoverPolygonFeature.geoOn(geo.event.feature.mouseover, (e: GeoEvent & { index?: number }) => this.onHoverHitOver(e));
    this.hoverPolygonFeature.geoOn(geo.event.feature.mouseoff, () => this.onHoverHitOff());
    this.setScaledDimensions(spectroInfo.width, spectroInfo.height);
    this.style = { ...defaultPulseMetadataStyle };
  }

  setScaledDimensions(scaledWidth: number, scaledHeight: number) {
    super.setScaledDimensions(scaledWidth, scaledHeight);
    this.enabled = true;
    this.formatData();
    this.redraw();
  }

  setPulseMetadataList(pulseMetadataList: PulseMetadata[]) {
    this.pulseMetadataList = pulseMetadataList;
    this.enabled = true;
    this.formatData();
    this.redraw();
  }

  setStyle(style: Partial<PulseMetadataStyle>) {
    this.style = { ...defaultPulseMetadataStyle, ...this.style, ...style };
  }

  /**
   * Called on every zoom event from BaseTextLayer. Avoid full redraw (formatData + draw):
   * zoom only changes text scale; geometry is unchanged. Update textScaled and redraw
   * existing data via updateMetadataStyle() to prevent performance issues during zoom.
   */
  onZoom(event: { zoomLevel: number }) {
    this.zoomLevel = event.zoomLevel;
    this.textScaled = undefined;
    if ((this.zoomLevel || 0) < -1.5) {
      this.textScaled = -1.5;
    } else if ((this.zoomLevel || 0) > 0) {
      this.textScaled = Math.sqrt(this.zoomLevel || 1);
    } else {
      this.textScaled = this.zoomLevel;
    }
    if (!this.enabled) return;
    this.updateMetadataStyle();
  }

  /** Re-apply styles and draw without re-formatting data. Use when only colors/sizes change. */
  updateMetadataStyle() {
    if (!this.enabled) return;
    this.lineLayer.style(this.createLineStyle()).draw();
    this.pointLayer.style(this.createPointStyle()).draw();
    const hoverActive = this.style.pulseMetadataLabels === 'Hover' || this.style.pulseMetadataLabels === 'Tooltip';
    if (hoverActive) {
      this.hoverPolygonFeature
        .data(this.hoverHitData)
        .style(this.createHoverHitStyle())
        .draw();
    }
    this.textLayer
      .data(this.getTextDataToShow())
      .style(this.createTextStyle())
      .draw();
    this.freqDurationLineLayer
      .data(this.getFreqDurationLineDataToShow())
      .style(this.createLineStyle())
      .draw();
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

  /** Text to show in the single text layer: all pulses or hovered pulse only. */
  private getTextDataToShow(): TextData[] {
    if (this.style.pulseMetadataLabels === 'Hover') {
      if (this.hoveredPulseIndex >= 0 && this.hoveredPulseIndex < this.pulseTextData.length) {
        return this.pulseTextData[this.hoveredPulseIndex];
      }
      return [];
    }
    if (this.style.pulseMetadataLabels === 'Always') {
      return this.pulseTextData.flat();
    }
    return [];
  }

  private getFreqDurationLineDataToShow(): LineData[] {
    if (this.style.pulseMetadataLabels === 'Hover') {
      if (this.hoveredPulseIndex >= 0) {
        return this.durationFreqLineData.filter((d) => d.index === this.hoveredPulseIndex);
      }
      return [];
    }
    return this.durationFreqLineData;
  }

  private getMap() {
    const ref = this.geoViewerRef as { value?: { gcsToDisplay: (c: { x: number; y: number }, gcs: null) => { x: number; y: number } } };
    return ref?.value ?? this.geoViewerRef;
  }

  private buildTooltipData(pulseIndex: number): PulseMetadataTooltipData | null {
    const pulse = this.pulseMetadataList[pulseIndex];
    if (!pulse || pulseIndex >= this.hoverHitData.length) return null;
    const hit = this.hoverHitData[pulseIndex];
    const coords = hit.polygon.coordinates[0];
    if (!coords || coords.length < 4) return null;
    const map = this.getMap();
    if (!map || typeof map.gcsToDisplay !== 'function') return null;
    const topLeft = map.gcsToDisplay({ x: coords[0][0], y: coords[0][1] }, null);
    const bottomRight = map.gcsToDisplay({ x: coords[2][0], y: coords[2][1] }, null);
    const left = Math.min(topLeft.x, bottomRight.x);
    const width = Math.abs(bottomRight.x - topLeft.x);
    const height = Math.abs(bottomRight.y - topLeft.y);

    let durationMs = 0;
    let fminKhz = 0;
    let fmaxKhz = 0;
    let fcKhz: number | null = null;
    if (pulse.curve && pulse.curve.length >= 2) {
      const times = pulse.curve.map((pt) => pt[0]);
      const freqs = pulse.curve.map((pt) => pt[1]);
      durationMs = Math.max(...times) - Math.min(...times);
      const minFreq = Math.min(...freqs);
      const maxFreq = Math.max(...freqs);
      fminKhz = minFreq / 1000;
      fmaxKhz = maxFreq / 1000;
    }
    if (pulse.char_freq && pulse.char_freq.length >= 2) {
      fcKhz = pulse.char_freq[1] / 1000;
    }
    const slopes = pulse.slopes ?? undefined;
    const { heelColor, charFreqColor, kneeColor } = this.style;
    return {
      durationMs,
      fminKhz,
      fmaxKhz,
      fcKhz,
      heelColor: pulse.heel ? heelColor : null,
      kneeColor: pulse.knee ? kneeColor : null,
      heelKhz: pulse.heel ? pulse.heel[1] / 1000 : null,
      kneeKhz: pulse.knee ? pulse.knee[1] / 1000 : null,
      charFreqColor: pulse.char_freq ? charFreqColor : null,
      slopeAtHiFcKneeKhzPerMs: slopes?.slope_at_hi_fc_knee_khz_per_ms ?? null,
      slopeAtFcKhzPerMs: slopes?.slope_at_fc_khz_per_ms ?? null,
      slopeAtLowFcHeelKhzPerMs: slopes?.slope_at_low_fc_heel_khz_per_ms ?? null,
      bbox: { top: 0, left, width, height },
    };
  }

  formatData() {
    this.lineData = [];
    this.durationFreqLineData = [];
    this.pointData = [];
    this.pulseTextData = [];
    this.hoverHitData = [];
    if (!this.spectroInfo.compressedWidth || !this.pulseMetadataList.length) {
      return;
    }
    const labelOffset = 8;
    const freqLineOffsetX = 4;

    this.pulseMetadataList.forEach((pulse: PulseMetadata) => {
      const index = pulse.index;
      const pulseText: TextData[] = [];
      const bboxPoints: { x: number; y: number }[] = [];

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
        bboxPoints.push(bottomLeft, bottomRight, topLeft);

        this.durationFreqLineData.push({
          line: {
            type: 'LineString',
            coordinates: [
              [bottomLeft.x, bottomLeft.y],
              [bottomRight.x, bottomRight.y],
            ],
          },
          lineKind: 'durationFreq',
          index: index,
        });

        this.durationFreqLineData.push({
          line: {
            type: 'LineString',
            coordinates: [
              [topLeft.x - freqLineOffsetX, topLeft.y],
              [bottomLeft.x - freqLineOffsetX, bottomLeft.y],
            ],
          },
          lineKind: 'durationFreq',
          index: index,
        });

        const durationMidX = (bottomLeft.x + bottomRight.x) / 2;
        pulseText.push({
          text: `${durationMs.toFixed(1)} ms`,
          x: durationMidX,
          y: bottomLeft.y + labelOffset,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'center',
        });
        pulseText.push({
          text: `Fₘₐₓ ${(maxFreq / 1000).toFixed(1)}kHz`,
          x: topLeft.x - freqLineOffsetX - labelOffset,
          y: topLeft.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'end',
        });
        pulseText.push({
          text: `Fₘᵢₙ ${(minFreq / 1000).toFixed(1)}kHz`,
          x: bottomLeft.x - freqLineOffsetX - labelOffset,
          y: bottomLeft.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'end',
        });
      }
      if (pulse.knee && pulse.knee.length >= 2) {
        const pos = this.getCompressedPosition(pulse.knee[0], pulse.knee[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'knee' });
        bboxPoints.push(pos);
        const kneeFreqKhz = (pulse.knee[1] / 1000).toFixed(1);
        pulseText.push({
          text: `Knee ${kneeFreqKhz} kHz`,
          x: pos.x - 2,
          y: pos.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'end',
        });
      }
      if (pulse.heel && pulse.heel.length >= 2) {
        const pos = this.getCompressedPosition(pulse.heel[0], pulse.heel[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'heel' });
        bboxPoints.push(pos);
        const heelFreqKhz = (pulse.heel[1] / 1000).toFixed(1);
        pulseText.push({
          text: `Heel ${heelFreqKhz} kHz`,
          x: pos.x + 2,
          y: pos.y,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'start',
        });
      }
      if (pulse.char_freq && pulse.char_freq.length >= 2) {
        const pos = this.getCompressedPosition(pulse.char_freq[0], pulse.char_freq[1], index);
        this.pointData.push({ x: pos.x, y: pos.y, label: 'char_freq' });
        bboxPoints.push(pos);
        const charFreqKhz = (pulse.char_freq[1] / 1000).toFixed(1);
        pulseText.push({
          text: `Fc ${charFreqKhz} kHz`,
          x: pos.x,
          y: pos.y - 2,
          offsetX: 0,
          offsetY: 0,
          textAlign: 'center',
        });
      }

      this.pulseTextData.push(pulseText);
      if (bboxPoints.length > 0) {
        const xs = bboxPoints.map((p) => p.x);
        const ys = bboxPoints.map((p) => p.y);
        const xmin = Math.min(...xs);
        const xmax = Math.max(...xs);
        const ymin = Math.min(...ys);
        const ymax = Math.max(...ys);
        this.hoverHitData.push({
          polygon: {
            type: 'Polygon',
            coordinates: [
              [
                [xmin, ymin],
                [xmax, ymin],
                [xmax, ymax],
                [xmin, ymax],
                [xmin, ymin],
              ],
            ],
          },
        });
      } else {
        this.hoverHitData.push({
          polygon: {
            type: 'Polygon',
            coordinates: [[[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]],
          },
        });
      }
    });
  }

  private onHoverHitOver(e: GeoEvent & { index?: number }) {
    if (!this.enabled) return;
    const hoverActive = this.style.pulseMetadataLabels === 'Hover' || this.style.pulseMetadataLabels === 'Tooltip';
    if (!hoverActive) return;
    const index = (e as GeoEvent & { index: number }).index;
    if (index < 0) return;
    this.hoveredPulseIndex = index;
    if (this.style.pulseMetadataLabels === 'Tooltip') {
      const data = this.buildTooltipData(index);
      if (data) this.event('pulse-metadata-tooltip', data);
    }
    this.updateMetadataStyle();
  }

  private onHoverHitOff() {
    if (this.hoveredPulseIndex === -1) return;
    if (this.style.pulseMetadataLabels === 'Tooltip') {
      this.event('pulse-metadata-tooltip', null);
    }
    this.hoveredPulseIndex = -1;
    this.updateMetadataStyle();
  }

  private createHoverHitStyle(): LayerStyle<HoverHitData> {
    return {
      fill: true,
      fillOpacity: 0,
      // Below is used for hover hit-testing debug by making stroke true
      stroke: false, // don't show stroke on hover
      strokeColor: '#FFFFFF',
      strokeWidth: 1,
    };
  }

  createLineStyle(): LayerStyle<LineData> {
    const { lineColor, lineWidth, durationFreqLineColor } = this.style || defaultPulseMetadataStyle;
    return {
      strokeColor: (_point, _index, d: LineData) =>
        d.lineKind === 'durationFreq' ? durationFreqLineColor : lineColor,
      strokeWidth: lineWidth,
      strokeOpacity: (_point, _index, d: LineData) => {
        const showLabels = this.style.pulseMetadataLabels === 'Always' || this.style.pulseMetadataLabels === 'Hover';
        if (!showLabels && d.lineKind === 'durationFreq') {
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

  createTextStyle(): LayerStyle<TextData> {
    const style = this.style ?? defaultPulseMetadataStyle;
    const { labelColor, labelFontSize } = style;
    return {
      fontSize: `${labelFontSize}px`,
      color: () => labelColor,
      strokeColor: '#000000',
      strokeWidth: 1,
      stroke: true,
      fill: false,
      textAlign: (d: TextData) => d.textAlign ?? 'start',
      textBaseline: 'middle',
      offset: (d: TextData) => ({ x: d.offsetX ?? 0, y: d.offsetY ?? 0 }),
      textScaled: this.textScaled,
    };
  }

  redraw() {
    if (!this.enabled) {
      this.lineLayer.data([]).draw();
      this.freqDurationLineLayer.data([]).draw();
      this.pointLayer.data([]).draw();
      this.textLayer.data([]).draw();
      this.hoverPolygonFeature.data([]).draw();
      return;
    }
    this.formatData();
    this.lineLayer
      .data(this.lineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    this.freqDurationLineLayer
      .data(this.getFreqDurationLineDataToShow())
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    this.pointLayer
      .data(this.pointData)
      .position((d: PulsePointData) => ({ x: d.x, y: d.y }))
      .style(this.createPointStyle())
      .draw();
    const hoverActive = this.style.pulseMetadataLabels === 'Hover' || this.style.pulseMetadataLabels === 'Tooltip';
    if (hoverActive) {
      this.hoverPolygonFeature
        .data(this.hoverHitData)
        .style(this.createHoverHitStyle())
        .draw();
    } else {
      this.hoverPolygonFeature.data([]).draw();
      this.hoveredPulseIndex = -1;
    }
    this.textLayer
      .data(this.getTextDataToShow())
      .style(this.createTextStyle())
      .draw();
  }

  disable() {
    this.enabled = false;
    this.hoveredPulseIndex = -1;
    this.lineLayer.data([]).draw();
    this.freqDurationLineLayer.data([]).draw();
    this.pointLayer.data([]).draw();
    this.hoverPolygonFeature.data([]).draw();
    super.disable();
  }

  destroy() {
    if (this.featureLayer) {
      this.geoViewerRef.deleteLayer(this.featureLayer);
    }
    if (this.featureTextLayer) {
      this.geoViewerRef.deleteLayer(this.featureTextLayer);
    }
    if (this.hoverHitLayer) {
      this.geoViewerRef.deleteLayer(this.hoverHitLayer);
    }
  }
}
