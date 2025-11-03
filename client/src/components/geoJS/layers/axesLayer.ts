import { SpectroInfo } from "../geoJSUtils";
import geo from "geojs";
import { LayerStyle, TextData } from "./types";
import BaseTextLayer from "./baseTextLayer";

interface Point {
  x: number;
  y: number;
}

interface Tick {
  value: number;
  position: Point;
}

interface TickTextData extends TextData {
  textAlign?: 'left' | 'center' | 'right';
  textScaled?: number;
}

export default class AxesLayer extends BaseTextLayer<TickTextData> {
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
  gridLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  axesFeature: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  gridFeature: any;

  left: number;
  top: number;
  right: number;
  bottom: number;

  lineData: Point[][];
  gridData: Point[][];
  textData: TickTextData[];
  color: string;

  freqRange: number[];
  timeRange: number[];
  tickSizeY: number;
  tickSizeX: number;
  tickLength: number;

  disabled: boolean;

  showGridLines: boolean;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    super(geoViewerRef, event, spectroInfo);
    this.geoViewerRef = geoViewerRef;
    this.event = event;
    this.spectroInfo = spectroInfo;
    this.scaledHeight = -1;
    this.scaledWidth = -1;
    this.xScale = 0;
    this.compressedView = false;

    this.lineData = [];
    this.gridData = [];
    this.textData = [];
    this.color = 'white';

    this.freqRange = [0, 1];
    this.tickSizeY = 10000;
    this.timeRange = [0, 1];
    this.tickSizeX = 50;
    this.tickLength = 10;

    this.disabled = false;
    this.showGridLines = false;

    this.init();
  }

  init() {
    this.initializeLineLayer();
    this.initializeGridLayer();
    this.initializeTextLayer();
    this.addEventListeners();
    this.drawAxes();
  }

  computeNodeBounds() {
    const mapNode: HTMLElement = (this.geoViewerRef.node()[0] as HTMLElement);
    const {
      left,
      right,
      top,
      bottom
    } = mapNode.getBoundingClientRect();
    this.left = left;
    this.top = top;
    this.right = right;
    this.bottom = bottom;
  }

  disable() {
    this.disabled = true;
    this.drawAxes();
  }

  enable() {
    this.disabled = false;
    this.drawAxes();
  }

  setGridEnabled(value: boolean) {
    this.showGridLines = value;
    if (!this.disabled) {
      this.drawAxes();
    }
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
    if (!this.disabled) {
      this.drawAxes();
    }
  }

  initializeLineLayer() {
    this.lineLayer = this.geoViewerRef.createLayer("feature", {
      features: ["line"],
    });
    this.axesFeature = this.lineLayer.createFeature("line");
  }

  initializeGridLayer() {
    this.gridLayer = this.geoViewerRef.createLayer("feature", {
      features: ["line"],
    });
    this.gridFeature = this.gridLayer.createFeature("line");
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
    this.lineData = [];
    this.gridData = [];
    this.textData = [];
    if (this.disabled) {
      this.axesFeature?.data(this.lineData).draw();
      this.gridFeature?.data(this.lineData).draw();
      this.textLayer?.data(this.textData).draw();
      return;
    }
    this.computeNodeBounds();
    this.computeLineData();
    this.computeYTickData();
    this.computeXTickData();
    this.axesFeature
      .data(this.lineData)
      .style(this.createAxesStyle())
      .draw();
    this.gridFeature
      .data(this.gridData)
      .style(this.createGridStyle())
      .draw();
    this.textLayer
      .data(this.textData)
      .style(this.createTextStyle())
      .draw();
  }

  computeFrequencyRange() {
    const yAxisTop = { x: this.left + 2, y: 0 };
    const yAxisBottom = { x: this.left + 2, y: this.bottom };
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
    const yAxisTop = { x: this.left + 2, y: 0 };
    const yAxisBottom = { x: this.left + 2, y: this.bottom - this.top };
    const xAxisLeft = { x: this.left, y: this.bottom - (this.top + 2)};
    const xAxisRight = { x: this.right, y: this.bottom - (this.top + 2)};

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
    const yAxisTop = { x: this.left + 2, y: 0 };
    const { x: gcsLeft } = this.geoViewerRef.displayToGcs(yAxisTop);
    const yTickStop = { x: this.left + this.tickLength, y: 0 };
    const textStart = { x: this.left + this.tickLength + 5, y: 0 };
    const gcsTickStop = this.geoViewerRef.displayToGcs(yTickStop).x;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).x;
    const tickFrequencies = [];
    const maxFreq = this.freqRange[1];
    for (let i = this.spectroInfo.low_freq; i < Math.min(Math.floor(maxFreq), this.spectroInfo.high_freq); i += this.tickSizeY) {
      tickFrequencies.push(i);
    }
    const yTicks: Tick[] = [];
    // Each i value is a frequency. Compute the needed y-value for each one
    tickFrequencies.forEach((freq: number) => {
      const yVal = this.scaledHeight - (((freq / 1000) - (this.spectroInfo.low_freq / 1000)) *this.scaledHeight * 1000) / (this.spectroInfo.high_freq - this.spectroInfo.low_freq);
      yTicks.push({
        value: freq,
        position: { x: gcsLeft, y: yVal },
      });
    });
    yTicks.forEach((tick: Tick) => {
      const { x, y } = tick.position;
      const line: Point[] = [{ x, y }, {x: gcsTickStop, y}];
      this.lineData.push(line);

      this.textData.push({
        text: `${(tick.value / 1000).toFixed(0)}KHz`,
        x: gcsTextStart,
        y,
        textAlign: 'left',
        textScaled: this.textScaled,
      });

      if (this.showGridLines) {
        this.gridData.push([
          { x: gcsTickStop, y },
          { x: this.scaledWidth, y },
        ]);
      }
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
    const xAxisLeft = { x: this.left, y: this.bottom - 2 };
    const xAxisRight = { x: this.right, y: this.bottom - 2};
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

    const xAxisLeft = { x: this.left, y: this.bottom - this.top };
    const { x: minX, y: gcsBottom } = this.geoViewerRef.displayToGcs(xAxisLeft);
    const { x: maxX } = this.geoViewerRef.displayToGcs({ x: this.right, y: this.top });
    const xTickStop = { x: 0, y: this.bottom - (this.top + this.tickLength) };
    const textStart = { x: 0, y: this.bottom - (this.top + this.tickLength + 5) };
    const gcsTickStop = this.geoViewerRef.displayToGcs(xTickStop).y;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).y;

    const gcsTopLeft = this.geoViewerRef.displayToGcs({x: this.left, y: 0});
    const gcsTopText = this.geoViewerRef.displayToGcs({x: this.left, y: 12}).y;
    const gcsTop = gcsTopLeft.y;

    let cumulativeWidth = 0;
    let visibleSegments = 0;
    for (let i = 0; i < widths.length; i++) {
      const startingWidth = cumulativeWidth;
      const endWidth = startingWidth + (widths[i] * (this.scaledWidth / compressedWidth));
      if (
        (endWidth >= minX && endWidth <= maxX)
        || (startingWidth >= minX && endWidth <= maxX)
      ) {
        visibleSegments += 1;
      }
      cumulativeWidth = endWidth;
    }

    cumulativeWidth = 0;
    const xTicks: Tick[] = [];
    startTimes.forEach((time, idx) => {
      xTicks.push({
        value: time,
        position: { x: cumulativeWidth, y: gcsBottom }
      });
      cumulativeWidth += widths[idx] * (this.scaledWidth / compressedWidth);
    });
    const lastTick: Tick = {
      value: endTimes[endTimes.length - 1],
      position: { x: cumulativeWidth, y: gcsBottom },
    };

    xTicks.forEach((tick, idx) => {
      const { x, y } = tick.position;
      const isFirstTick = idx === 0;
      const tickEnd = isFirstTick ? gcsTickStop : gcsTop;
      const line: Point[] = [{ x, y }, { x, y: gcsTickStop }];
      this.lineData.push(line);
      if (tickEnd !== gcsTickStop) {
        // Use the feature for the grid to draw fainter lines across
        // the image linking start/end time labels
        const gridLine = [
          { x, y: gcsTickStop + 50 },
          { x, y: gcsTop }
        ];
        this.gridData.push(gridLine);
      }
      this.textData.push({
        text: `▶${tick.value.toFixed(0)}ₘₛ`,
        x,
        y: gcsTextStart,
        textAlign: 'left',
        textScaled: this.textScaled,
      });
      if (visibleSegments <= (startTimes.length / 4) * 3 && idx < xTicks.length - 1) {
        // Add additional ticks using number of visible segments
        // as a proxy for how zoomed in the user currently is
        const xVal = (x + xTicks[idx + 1].position.x) / 2;
        const time = ((startTimes[idx] + endTimes[idx]) / 2).toFixed(0);
        this.lineData.push([
          { x: xVal, y: y },
          { x: xVal, y: gcsTickStop },
        ]);
        this.textData.push({
          text: `${time}ₘₛ`,
          x: xVal,
          y: gcsTextStart,
          textAlign: 'center',
          textScaled: this.textScaled,
        });
      }
      if (idx > 0) {
        this.textData.push({
          text: `${endTimes[idx - 1].toFixed(0)}ₘₛ◀`,
          x,
          y: gcsTopText,
          textAlign: 'right',
          textScaled: this.textScaled,
        });
      }
    });

    this.gridData.push([
      { x: lastTick.position.x, y: lastTick.position.y },
      { x: lastTick.position.x, y: gcsTop },
    ]);
    this.textData.push({
        text: `${lastTick.value.toFixed(0)}ₘₛ◀`,
        x: lastTick.position.x,
        y: gcsTop,
        textAlign: 'right',
        textScaled: this.textScaled,
    });
  }

  _computeFullXTickData() {
    this.computeTimeRange();
    const xAxisLeft = { x: this.left, y: this.bottom - this.top };
    const { y: gcsBottom } = this.geoViewerRef.displayToGcs(xAxisLeft);
    const xTickStop = { x: 0, y: this.bottom - (this.top + this.tickLength) };
    const textStart = { x: 0, y: this.bottom - (this.top + this.tickLength + 5) };
    const gcsTickStop = this.geoViewerRef.displayToGcs(xTickStop).y;
    const gcsTextStart = this.geoViewerRef.displayToGcs(textStart).y;
    const xTicks: Tick[] = [];
    for (let time = this.spectroInfo.start_time; time < Math.min(this.spectroInfo.end_time, this.timeRange[1]); time += this.tickSizeX) {
      const xVal = (time * this.scaledWidth) / (this.spectroInfo.end_time - this.spectroInfo.start_time);
      xTicks.push({
        value: time,
        position: { x: xVal, y: gcsBottom },
      });
    }
    xTicks.forEach((tick: Tick) => {
      const { x, y } = tick.position;
      const line: Point[] = [{ x, y }, { x, y: gcsTickStop }];
      this.lineData.push(line);

      this.textData.push({
        text: `${tick.value.toFixed(0)}ₘₛ`,
        x,
        y: gcsTextStart,
        textAlign: 'center',
        textScaled: this.textScaled,
      });

      if (this.showGridLines) {
        const gridStart = this.geoViewerRef.displayToGcs({ x: xTickStop.x, y: xTickStop.y - 20}).y;
        const gcsTopLeft = this.geoViewerRef.displayToGcs({x: this.left, y: 0});
        const gcsTop = gcsTopLeft.y;
        this.gridData.push([
          { x, y: gridStart },
          { x, y: gcsTop },
        ]);
      }
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
      textScaled: (data: TickTextData) => (data.textScaled),
    };
  }

  createGridStyle() {
    return {
      strokeWidth: 1,
      strokeColor: this.color,
      strokeOpacity: 0.4,
    };
  }
}
