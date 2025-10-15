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
  textData: TextData[];
  color: string;

  freqRange: number[];
  tickSize: number;
  tickLength: number;
  xTicks: Tick[];
  yTicks: Tick[];

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
    this.tickSize = 10000;
    this.tickLength = 10;
    this.xTicks = [];
    this.yTicks = [];

    this.initializeLineLayer();
    this.initializeTextLayer();
    this.addEventListeners();
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
    // Clear existing data (move line data clearig here as well)
    this.textData = [];
    this.yTicks = [];
    this.lineData = [];
    this.computeFrequencyRange();
    this.computeFrequencyTickOptions();
    // this.computeTimeRange();
    this.computeLineData();
    this.computeYTickData();
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
      this.tickSize = 10000;
      return;
    } else if (freqRangeMagnitude > 20000) {
      this.tickSize = 5000;
      return;
    } else {
      this.tickSize = 2000;
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
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const { left } = mapNode.getBoundingClientRect();
    const yAxisTop = { x: left + 2, y: 0 };
    const { x: gcsLeft } = this.geoViewerRef.displayToGcs(yAxisTop);
    const yTickStop = { x: left + this.tickLength, y: 0 };
    const textStart = { x: left + this.tickLength, y: 0 };
    const gcsTickStop = this.geoViewerRef.displayToGcs(yTickStop).x;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).x;
    const tickFrequencies = [];
    const maxFreq = this.freqRange[1];
    for (let i = this.spectroInfo.low_freq; i < Math.floor(maxFreq); i += this.tickSize) {
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
      });
    });
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
      textAlign: () => 'start',
      textBaseline: () => 'middle',
      color: () => this.color,
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
    };
  }
}
