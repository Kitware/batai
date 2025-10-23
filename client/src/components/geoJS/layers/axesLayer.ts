import { SpectroInfo } from "../geoJSUtils";
import geo from "geojs";
import { LayerStyle, TextData } from "./types";

interface Point {
  x: number;
  y: number;
}

interface Tick {
  value: number;
  unit: string;
  position: Point;
}

interface TickTextData extends TextData {
  textAlign?: 'left' | 'center' | 'right';
}

export default class AxesLayer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;
  spectroInfo: SpectroInfo;

  scaledHeight: number;
  scaledWidth: number;
  xScale: number;
  compressedView: boolean;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  axesFeature: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;

  lineData: Point[][];
  textData: TickTextData[];
  color: string;

  freqRange: number[];
  timeRange: number[];
  tickSizeY: number;
  tickSizeX: number;
  tickLength: number;
  xTicks: Tick[];
  yTicks: Tick[];

  disabled: boolean;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    this.geoViewerRef = geoViewerRef;
    this.event = event;
    this.spectroInfo = spectroInfo;
    this.scaledHeight = -1;
    this.scaledWidth = -1;
    this.xScale = 0;
    this.compressedView = false;

    this.lineData = [];
    this.textData = [];
    this.color = 'white';

    this.freqRange = [0, 1];
    this.tickSizeY = 10000;
    this.timeRange = [0, 1];
    this.tickSizeX = 50;
    this.tickLength = 10;
    this.xTicks = [];
    this.yTicks = [];

    this.disabled = false;

    this.init();
  }

  init() {
    this.initializeLineLayer();
    this.initializeTextLayer();
    this.addEventListeners();
    this.drawAxes();
  }

  disable() {
    this.disabled = true;
    this.lineData = [];
    this.textData = [];
    if (this.lineLayer && this.axesFeature) {
      this.axesFeature.data(this.lineData).draw();
    }
    if (this.textLayer) {
      this.textLayer.data(this.textData).draw();
    }
  }

  enable() {
    this.disabled = false;
    this.drawAxes();
  }

  setScaledDimensions(newWidth: number, newHeight: number) {
    this.scaledWidth = newWidth;
    this.scaledHeight = newHeight;
    if (this.spectroInfo.compressedWidth) {
      this.xScale = newWidth / this.spectroInfo.compressedWidth;
      this.compressedView = true;
    } else {
      this.xScale = newWidth / this.spectroInfo.width;
      this.compressedView = false;
    }
    this.drawAxes();
  }

  initializeLineLayer() {
    this.lineLayer = this.geoViewerRef.createLayer("feature", {
      features: ["line"],
    });
    this.axesFeature = this.lineLayer.createFeature("line");
  }

  initializeTextLayer() {
    this.textLayer = this.geoViewerRef.createLayer('feature', {
      features: ['text']
    });
    this.textLayer = this.textLayer
      .createFeature('text')
      .text((data: TextData) => data.text)
      .style(this.createTextStyle())
      .position((data: TextData) => ({
        x: data.x,
        y: data.y
      }));
  }

  addEventListeners() {
    this.geoViewerRef.geoOn(geo.event.pan, () => {
      this.drawAxes();
    });
  }

  drawAxes() {
    if (this.disabled) {
      this.axesFeature.data([]).draw();
      this.textLayer.data([]).draw();
      return;
    }
    // Clear existing data (move line data clearig here as well)
    this.textData = [];
    this.yTicks = [];
    this.xTicks = [];
    this.lineData = [];
    // this.computeTimeRange();
    this.computeLineData();
    this.computeYTickData();
    this.computeXTickData();
    this.axesFeature
      .data(this.lineData)
      .style(this.createAxesStyle())
      .draw();
    this.textLayer
      .data(this.textData)
      .style(this.createTextStyle())
      .draw();
  }

  computeFrequencyRange() {
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { left, bottom } = mapNode.getBoundingClientRect();
    const yAxisTop = { x: left + 2, y: 0 };
    const yAxisBottom = { x: left + 2, y: bottom };
    const axisTopGcs = this.geoViewerRef.displayToGcs(yAxisTop);
    const axisBottomGcs = this.geoViewerRef.displayToGcs(yAxisBottom);
    const highFreqY = axisTopGcs.y;
    const lowFreqY = axisBottomGcs.y;
    const height = Math.max(this.scaledHeight, this.spectroInfo.height);
    const highFreq = height - highFreqY >= 0
      ? ((height - highFreqY) * (this.spectroInfo.high_freq - this.spectroInfo.low_freq)) / height / 1000 + this.spectroInfo.low_freq / 1000
      : -1;
    const lowFreq = height - lowFreqY >= 0
      ? ((height - lowFreqY) * (this.spectroInfo.high_freq - this.spectroInfo.low_freq)) / height / 1000 + this.spectroInfo.low_freq / 1000
      : -1;
    this.freqRange = [Math.max(this.spectroInfo.low_freq, lowFreq * 1000), highFreq * 1000];
  }

  computeFrequencyTickOptions() {
    // Need the frequency value of all the ticks
    const freqRangeMagnitude = this.freqRange[1] - this.freqRange[0];
    if (freqRangeMagnitude > 50000) {
      this.tickSizeY = 10000;
      return;
    } else if (freqRangeMagnitude > 20000) {
      this.tickSizeY = 5000;
      return;
    } else {
      this.tickSizeY = 2000;
    }
  }

  computeLineData() {
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { left, top, right, bottom } = mapNode.getBoundingClientRect();
    const yAxisTop = { x: left + 2, y: 0 };
    const yAxisBottom = { x: left + 2, y: bottom - top };
    const xAxisLeft = { x: left, y: bottom - (top + 2)};
    const xAxisRight = { x: right, y: bottom - (top + 2)};

    this.lineData = [
      [
        this.geoViewerRef.displayToGcs(yAxisTop),
        this.geoViewerRef.displayToGcs(yAxisBottom),
      ],
      [
        this.geoViewerRef.displayToGcs(xAxisLeft),
        this.geoViewerRef.displayToGcs(xAxisRight),
      ]
    ];
  }

  computeYTickData() {
    this.computeFrequencyRange();
    this.computeFrequencyTickOptions();
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { left } = mapNode.getBoundingClientRect();
    const yAxisTop = { x: left + 2, y: 0 };
    const { x: gcsLeft } = this.geoViewerRef.displayToGcs(yAxisTop);
    const yTickStop = { x: left + this.tickLength, y: 0 };
    const textStart = { x: left + this.tickLength + 5, y: 0 };
    const gcsTickStop = this.geoViewerRef.displayToGcs(yTickStop).x;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).x;
    const tickFrequencies = [];
    const maxFreq = this.freqRange[1];
    for (let i = this.spectroInfo.low_freq; i < Math.min(Math.floor(maxFreq), this.spectroInfo.high_freq); i += this.tickSizeY) {
      tickFrequencies.push(i);
    }
    // Each i value is a frequency. Compute the needed y-value for each one
    tickFrequencies.forEach((freq: number) => {
      const yVal = this.scaledHeight - (((freq / 1000) - (this.spectroInfo.low_freq / 1000)) *this.scaledHeight * 1000) / (this.spectroInfo.high_freq - this.spectroInfo.low_freq);
      this.yTicks.push({
        value: freq,
        unit: '',
        position: { x: gcsLeft, y: yVal },
      });
    });
    this.yTicks.forEach((tick: Tick) => {
      const { x, y } = tick.position;
      const line: Point[] = [{ x, y }, {x: gcsTickStop, y}];
      this.lineData.push(line);

      this.textData.push({
        text: `${(tick.value / 1000).toFixed(0)}KHz`,
        x: gcsTextStart,
        y,
        textAlign: 'left',
      });
    });
  }

  computeXTickData() {
    if (this.compressedView) {
      this._computeCompressedXTickData();
    } else {
      this._computeFullXTickData();
    }
  }

  computeTimeRange() {
    const mapNode: HTMLElement = this.geoViewerRef.node()[0] as HTMLElement;
    const { left, right, bottom } = mapNode.getBoundingClientRect();
    const xAxisLeft = { x: left, y: bottom - 2 };
    const xAxisRight = { x: right, y: bottom - 2};
    const axisLeftGcs = this.geoViewerRef.displayToGcs(xAxisLeft);
    const axisRightGcs = this.geoViewerRef.displayToGcs(xAxisRight);
    const startTimeX = axisLeftGcs.x;
    const endTimeX = axisRightGcs.x;
    const startTime = startTimeX * ((this.spectroInfo.end_time - this.spectroInfo.start_time) / this.scaledWidth);
    const endTime = endTimeX * ((this.spectroInfo.end_time - this.spectroInfo.start_time) / this.scaledWidth);
    this.timeRange = [startTime, Math.min(endTime, this.spectroInfo.end_time)];

    const timeRangeMagnitude = this.timeRange[1] - this.timeRange[0];
    if (timeRangeMagnitude > 200) {
      this.tickSizeX = 50;
    } else if (timeRangeMagnitude > 100) {
      this.tickSizeX = 25;
    } else {
      this.tickSizeX = 10;
    }
  }

  _computeCompressedXTickData() {
    const {
      start_times: startTimes,
      end_times: endTimes,
      widths,
      compressedWidth,
      height,
    } = this.spectroInfo;
    if (!startTimes || !endTimes || !widths || !compressedWidth || !height) return;

    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { bottom, left, top } = mapNode.getBoundingClientRect();
    const xAxisLeft = { x: left, y: bottom - top };
    const { y: gcsBottom } = this.geoViewerRef.displayToGcs(xAxisLeft);
    const xTickStop = { x: 0, y: bottom - (top + this.tickLength) };
    const textStart = { x: 0, y: bottom - (top + this.tickLength + 5) };
    const gcsTickStop = this.geoViewerRef.displayToGcs(xTickStop).y;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).y;

    const gcsTopLeft = this.geoViewerRef.displayToGcs({x: left, y: 0});
    const gcsTop = gcsTopLeft.y;

    let cumulativeWidth = 0;

    startTimes.forEach((time, idx) => {
      this.xTicks.push({
        value: time,
        unit: '',
        position: { x: cumulativeWidth, y: gcsBottom }
      });
      cumulativeWidth += widths[idx] * (this.scaledWidth / compressedWidth);
    });

    this.xTicks.forEach((tick, idx) => {
      const { x, y } = tick.position;
      const isFirstTick = idx === 0;
      const tickEnd = isFirstTick ? gcsTickStop : gcsTop;
      const line: Point[] = [{ x, y }, { x, y: tickEnd }];
      this.lineData.push(line);
      this.textData.push({
        text: `▶${tick.value.toFixed(0)}ₘₛ`,
        x,
        y: gcsTextStart,
        textAlign: 'left',
      });
      if (idx > 0) {
        this.textData.push({
          text: `${endTimes[idx - 1].toFixed(0)}ₘₛ◀`,
          x,
          y: gcsTop + 24,
          textAlign: 'right',
        });
      }
    });
  }

  _computeFullXTickData() {
    this.computeTimeRange();
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { bottom, left, top } = mapNode.getBoundingClientRect();
    const xAxisLeft = { x: left, y: bottom - top };
    const { y: gcsBottom } = this.geoViewerRef.displayToGcs(xAxisLeft);
    const xTickStop = { x: 0, y: bottom - (top + this.tickLength) };
    const textStart = { x: 0, y: bottom - (top + this.tickLength + 5) };
    const gcsTickStop = this.geoViewerRef.displayToGcs(xTickStop).y;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).y;
    for (let time = this.spectroInfo.start_time; time < Math.min(this.spectroInfo.end_time, this.timeRange[1]); time += this.tickSizeX) {
      const xVal = (time * this.scaledWidth) / (this.spectroInfo.end_time - this.spectroInfo.start_time);
      this.xTicks.push({
        value: time,
        unit: '',
        position: { x: xVal, y: gcsBottom },
      });
    }
    this.xTicks.forEach((tick: Tick) => {
      const { x, y } = tick.position;
      const line: Point[] = [{ x, y }, { x, y: gcsTickStop }];
      this.lineData.push(line);

      this.textData.push({
        text: `${tick.value.toFixed(0)}ₘₛ`,
        x,
        y: gcsTextStart,
        textAlign: 'center',
      });
    });
  }

  destroy() {
    if (this.textLayer) {
      this.geoViewerRef.deleteLayer(this.textLayer);
    }
    if (this.lineLayer) {
      this.geoViewerRef.deleteLayer(this.lineLayer);
    }
  }

  createAxesStyle() {
    return {
      strokeWidth: 1,
      strokeColor: this.color,
    };
  }

  createTextStyle(): LayerStyle<TextData> {
    return {
      fontSize: '16px',
      textAlign: (data: TickTextData) => data.textAlign || 'center',
      textBaseline: () => 'middle',
      color: () => this.color,
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
    };
  }
}
