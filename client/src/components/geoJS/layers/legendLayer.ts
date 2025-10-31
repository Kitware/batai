/* eslint-disable class-methods-use-this */
import { SpectroInfo } from "../geoJSUtils";
import BaseTextLayer from "./baseTextLayer";
import { LayerStyle, TextData } from "./types";
import geo from "geojs";

interface LineData {
  line: GeoJSON.LineString;
  thicker?: boolean;
  grid?: boolean;
}

interface LegendTextData extends TextData {
  type: 'time' | 'freq',
  textAlign?: 'left' | 'center' | 'right';
  textBaseline?: 'top' | 'middle' | 'bottom';
  textScaled?: number | undefined;
  compressedLabel?: boolean;
}

export default class LegendLayer extends BaseTextLayer<LegendTextData> {
  lineDataX: LineData[];
  lineDataY: LineData[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  gridLayer: any;

  textDataX: LegendTextData[];
  textDataY: LegendTextData[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;

  gridLines: LineData[];

  spectroInfo: SpectroInfo;

  textStyle: LayerStyle<LegendTextData>;
  lineStyle: LayerStyle<LineData>;

  axisBuffer: number;

  gridEnabled: boolean;

  disabled: boolean;


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {

    super(geoViewerRef, event, spectroInfo);
    this.lineDataX = [];
    this.lineDataY = [];
    this.spectroInfo = spectroInfo;
    this.textDataX = [];
    this.textDataY = [];
    this.axisBuffer = 5;
    this.scaledHeight = -1;
    this.scaledWidth  = -1;
    this.gridEnabled = false;
    this.disabled = false;

    this.init();
  }

  init() {
    if (!this.textLayer) {
      const layer = this.geoViewerRef.createLayer("feature", {
        features: ["text", "line"],
      });
      this.textLayer = layer
        .createFeature("text")
        .text((data: LegendTextData) => data.text)
        .position((data: LegendTextData) => ({ x: data.x, y: data.y }));

      this.lineLayer = layer.createFeature("line");
      this.gridLayer = layer.createFeature("line");

      this.textStyle = this.createTextStyle();
      this.lineStyle = this.createLineStyle();
      this.gridLines = [];
      this.geoViewerRef.geoOn(geo.event.pan, () => this.onPan());
      this.geoViewerRef.geoOn(geo.event.zoom, (event: {zoomLevel: number}) => this.onZoom(event));
      this.createLabels();
      this.calcGridLines();
    }
  }

  onPan() {
    const bounds = this.geoViewerRef.camera().bounds;
    const { left, bottom, top } = bounds;
    const bottomOffset = -bottom < this.spectroInfo.height + 20 ? -bottom : 0;
    const topOffset = top < 20 ? top : 0;
    const leftOffset = left > -20 ? left : 0;
    this.lineDataY = [];
    this.lineDataX = [];
    this.textDataX = [];
    this.textDataY = [];
    this.drawYAxis(leftOffset);
    this.drawXAxis(bottomOffset, topOffset, leftOffset);
    this.redraw();
  }

  setScaledDimensions( width: number, height: number) {
    super.setScaledDimensions(width, height);
    this.createLabels();
    this.redraw();
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  drawXAxisLabels(yOffset = 0, _xOffset = 0, leftOffset = 0) {
    const adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;

    const yBuffer = yOffset === 0 ? this.axisBuffer : this.axisBuffer * -0.5;
    const baseYPos = yOffset === 0 ? adjustedHeight : yOffset;

    // Now we need tick marks for ms along the X-axis
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = adjustedWidth / time;

    // every 100 ms a small tick and every 1000 a big tick
    for (let i = 0; i < time; i += 10) {
      const length = i % 1000 === 0 ? yBuffer * 8 : yBuffer * 4;
      const withinYAxis = (i * timeToPixels) < (leftOffset +  50)  && leftOffset  !== 0 && yOffset !== 0;
      if (withinYAxis) {
        continue;
      }
      if (i % 50 === 0) {
        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [i * timeToPixels, baseYPos + yBuffer],
              [i * timeToPixels, baseYPos + length],
            ],
          },
          thicker: i % 1000 === 0,
        });
        this.textDataX.push({
          text: `${i}ₘₛ`,
          type: 'time',
          x: i * timeToPixels,
          y: baseYPos + length,
          offsetX: 3,
          offsetY: yOffset === 0 ? 8 : -8,
          textScaled: this.textScaled,
        });
      }
    }
  }
  destroy() {
    if (this.textLayer) {
      this.geoViewerRef.deleteLayer(this.textLayer);
    }
    if (this.lineLayer) {
      this.geoViewerRef.deleteLayer(this.lineLayer);
    }
    if (this.gridLayer) {
      this.geoViewerRef.deleteLayer(this.gridLayer);
    }
  }


  drawXAxisLabelsCompressed(yOffset = 0, topOffset = 0, leftOffset = 0,) {
    // const adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;

    const yBuffer = yOffset === 0 ? this.axisBuffer : this.axisBuffer * -0.5;
    const baseYPos = yOffset === 0 ? adjustedHeight : yOffset;
    const baseTopPos = topOffset === 0 ? 0 : -topOffset;
    const topBuffer = topOffset === 0 ? this.axisBuffer * 3 : this.axisBuffer * -3;

    const { start_times, end_times, widths, compressedWidth } = this.spectroInfo;
    if (!compressedWidth) {
      throw Error('No compressed width');
    }
    if (start_times && end_times && widths) {
      // We need a pixel time to map to the 0 position
      let pixelOffset = 0;
      const length = yBuffer * 4;
      for (let i = 0; i < start_times.length; i += 1) {
        const start_time = start_times[i];
        const end_time = end_times[i];
        const width = this.scaledWidth > compressedWidth ? (this.scaledWidth / compressedWidth) * widths[i] : widths[i];
        const bottomWithinYAxisStart = (pixelOffset) < (leftOffset +  150)  && leftOffset !== 0 && yOffset !== 0;
        const topWithinYAxisEnd = (pixelOffset+width) < (leftOffset +  150)  && leftOffset !== 0 && topOffset !== 0;


      if (!bottomWithinYAxisStart) {
        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [pixelOffset, baseYPos + yBuffer],
              [ pixelOffset, baseYPos + length],
            ],
          },
          thicker: true,
        });
      }
      if (!topWithinYAxisEnd) {
        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [
                width + pixelOffset,
                baseYPos + yBuffer,
              ],
              [
                width + pixelOffset,
                baseYPos + topBuffer,
              ],
            ],
          },
          thicker: true,
        });

        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [width + pixelOffset, baseTopPos],
              [width + pixelOffset, baseTopPos - topBuffer],
            ],
          },
          thicker: true,
        });
      }
        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [
                width + pixelOffset,
                baseYPos + yBuffer,
              ],
              [width + pixelOffset, baseTopPos],
            ],
          },
          grid: true,
        });

        //Need to decide what text to add to the label
        if (!bottomWithinYAxisStart) {
        this.textDataX.push({
          text: `▶${start_time}ₘₛ`,
          type: 'time',
          x: 0 + pixelOffset,
          y: baseYPos + length + (yOffset === 0 ? 18 : -12),
          textScaled: this.textScaled,
          textAlign: 'left',
          compressedLabel: true,
        });
      }
      if (!topWithinYAxisEnd) {

        this.textDataX.push({
          text: `${end_time}ₘₛ◀`,
          type: 'time',
          x: width + pixelOffset,
          y: baseTopPos + (baseTopPos === 0 ? -16 : 16),
          textBaseline: baseTopPos === 0 ? 'bottom' : 'top',
          textAlign: 'right',
          textScaled: this.textScaled,
          compressedLabel: true,
        });
      }
        pixelOffset += width;
        // Need to add the current
      }
    }
  }

  calcGridLines() {
    // Y-Axis grid lines:
    let adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;
    const xBuffer = this.axisBuffer;
    const hz = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const hzToPixels = adjustedHeight / hz;
    this.gridLines = [];
    if (this.spectroInfo.compressedWidth && this.scaledWidth > this.spectroInfo.compressedWidth) {
      adjustedWidth = this.scaledWidth;
    }
    for (let i = 0; i < hz; i += 10000) {
      this.gridLines.push({
        line: {
          type: "LineString",
          coordinates: [
            [0 - xBuffer - length, adjustedHeight - i * hzToPixels],
            [adjustedWidth, adjustedHeight - i * hzToPixels],
          ],
        },
        grid: true,
      });
    }
    const baseYPos = adjustedHeight;

    // Now we need tick marks for ms along the X-axis
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = adjustedWidth / time;

    const { start_times, end_times, widths, compressedWidth } = this.spectroInfo;
    const compressed = (start_times && end_times && widths && compressedWidth);

    // every 100 ms a small tick and every 1000 a big tick
    if (!compressed) {
      for (let i = 0; i < time; i += 10) {
        this.gridLines.push({
          line: {
            type: "LineString",
            coordinates: [
              [i * timeToPixels, 0],
              [i * timeToPixels, baseYPos + length],
            ],
          },
          grid: true,
        });
      }
    }
  }

  drawYAxis(offset = 0) {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;
    const xBuffer = offset === 0 ? this.axisBuffer : this.axisBuffer * -0.25;
    const yAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [offset - xBuffer, 0],
        [offset - xBuffer, adjustedHeight + xBuffer],
      ],
    };
    this.lineDataY.push({ line: yAxis });

    // Lets do the vertical Hz axis now
    const hz = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const hzToPixels = adjustedHeight / hz;
    for (let i = 0; i < hz; i += 10000) {
      const length = i % 10000 === 0 ? xBuffer * 8 : xBuffer * 4;
      this.lineDataY.push({
        line: {
          type: "LineString",
          coordinates: [
            [offset - xBuffer, adjustedHeight - i * hzToPixels],
            [offset - xBuffer - length, adjustedHeight - i * hzToPixels],
          ],
        },
        thicker: i % 10000 === 0,
      });

      this.textDataY.push({
        text: `${(i + this.spectroInfo.low_freq) / 1000}KHz`,
        x: offset - xBuffer + (offset === 0 ? -45 : 10),
        y: adjustedHeight - i * hzToPixels,
        textAlign:  offset === 0 ? 'right' : 'left',
        offsetY: 0,
        type: 'freq',
        textScaled: this.textScaled,
      });
    }
  }

  drawXAxis(bottomOffset = 0, topOffset = 0, lefOffset = 0) {
    let adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;

    if (this.spectroInfo.compressedWidth && this.scaledWidth > this.spectroInfo.compressedWidth) {
      adjustedWidth = this.scaledWidth;
    }
    const xAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, adjustedHeight + this.axisBuffer],
        [adjustedWidth, adjustedHeight + this.axisBuffer],
      ],
    };

    this.lineDataX.push({ line: xAxis });
    this.drawYAxis(0);

    if (this.spectroInfo.compressedWidth && this.spectroInfo.start_times && this.spectroInfo.end_times) {
      this.drawXAxisLabelsCompressed(bottomOffset, topOffset, lefOffset);
    } else {
      this.drawXAxisLabels(bottomOffset, topOffset, lefOffset);
    }
  }
  createLabels() {
    const adjustedWidth = this.scaledWidth > this.spectroInfo.width ? this.scaledWidth : this.spectroInfo.width;
    const adjustedHeight = this.scaledHeight > this.spectroInfo.height ? this.scaledHeight : this.spectroInfo.height;

    // Take spectro Info and create lines for X/Y axis
    this.textDataX = [];
    this.lineDataX = [];
    this.textDataY = [];
    this.lineDataY = [];
    const xAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, adjustedHeight + this.axisBuffer],
        [adjustedWidth, adjustedHeight + this.axisBuffer],
      ],
    };

    this.lineDataX.push({ line: xAxis });
    this.drawYAxis();

    if (this.spectroInfo.compressedWidth && this.spectroInfo.start_times && this.spectroInfo.end_times) {
      this.drawXAxisLabelsCompressed();
    } else {
      this.drawXAxisLabels();
    }
  }

  redraw() {
    if (this.disabled) return;
    this.calcGridLines();
    if (this.gridEnabled) {
      this.gridLayer
        .data(this.gridLines)
        .line((d: LineData) => d.line.coordinates)
        .style(this.createLineStyle())
        .draw();
    } else {
      this.gridLayer.data([]).draw();
    }
    const combinedLineData = this.lineDataX.concat(this.lineDataY);
    this.lineLayer
      .data(combinedLineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    const combinedLegendTextData = this.textDataX.concat(this.textDataY);
    this.textLayer.data(combinedLegendTextData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.disabled = true;
    this.lineLayer.data([]).draw();
    this.gridLayer.data([]).draw();
    this.textLayer.data([]).draw();
  }

  enable() {
    this.disabled = false;
    this.redraw();
  }

  setTextColor(newColor: string) {
    this.color = newColor;
    this.textStyle = this.createTextStyle();
    this.lineStyle = this.createLineStyle();
    this.redraw();
  }

  setGridEnabled(val: boolean) {
    this.gridEnabled = val;
    if (this.gridEnabled && !this.disabled) {
      this.gridLayer
        .data(this.gridLines)
        .line((d: LineData) => d.line.coordinates)
        .style(this.createLineStyle())
        .draw();
    } else {
      this.gridLayer.data([]).draw();
    }
  }

  createLineStyle(): LayerStyle<LineData> {
    return {
      ...{
        strokeColor: () => this.color,
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
        color: () => this.color,
        uniformPolygon: true,
        fill: false,
      },
      strokeOpacity: (_point, _index, data) => {
        // Reduce the rectangle opacity if a polygon is also drawn
        if (data.grid) {
          return 0.5;
        }
        return 1.0;
      },

      strokeWidth: (_point, _index, data) => {
        if (data.thicker) {
          return 4.0;
        }
        if (data.grid) {
          return 1.0;
        }
        return 2.0;
      },
    };
  }
  createTextStyle(): LayerStyle<LegendTextData> {
    return {
      ...{
        strokeColor: "yellow",
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
        uniformPolygon: true,
        fill: false,
        fontSize: `${this.getFontSize(20, 12, this.xScale)}px`
      },
      color: () => {
        return this.color;
      },
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textBaseline: (data) => data.textBaseline || 'middle',
      textAlign: (data) => (data.textAlign || "center"),
      textScaled: (data) => (data.textScaled),
      fontSize: (data) => data.type === 'time' && this.compressedView ? `${this.getFontSize(16, 10, this.xScale)}px` : `20px`,
      visible: (data) => (data.compressedLabel && this.xScale < 1.5) ? false : true,
    };
  }
}
