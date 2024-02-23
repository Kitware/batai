/* eslint-disable class-methods-use-this */
import { SpectroInfo } from "../geoJSUtils";
import { LayerStyle } from "./types";
import geo from "geojs";

interface LineData {
  line: GeoJSON.LineString;
  thicker?: boolean;
  grid?: boolean;
}

interface TextData {
  text: string;
  x: number;
  y: number;
  offsetY?: number;
  offsetX?: number;
}

export default class LegendLayer {
  lineDataX: LineData[];
  lineDataY: LineData[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  gridLayer: any;

  textDataX: TextData[];
  textDataY: TextData[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  gridLines: LineData[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  spectroInfo: SpectroInfo;

  textStyle: LayerStyle<TextData>;
  lineStyle: LayerStyle<LineData>;

  axisBuffer: number;

  gridEnabled: boolean;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    this.geoViewerRef = geoViewerRef;
    this.lineDataX = [];
    this.lineDataY = [];
    this.spectroInfo = spectroInfo;
    this.textDataX = [];
    this.textDataY = [];
    this.axisBuffer = 5;
    this.event = event;
    this.gridEnabled = false;
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["text", "line"],
    });
    this.textLayer = layer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .position((data: TextData) => ({ x: data.x, y: data.y }));

    this.lineLayer = layer.createFeature("line");
    this.gridLayer = layer.createFeature("line");

    this.textStyle = this.createTextStyle();
    this.lineStyle = this.createLineStyle();
    this.gridLines = [];
    this.createLabels();
    this.calcGridLines();
    this.geoViewerRef.geoOn(geo.event.pan, () => this.onPan());
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
    this.drawXAxis(bottomOffset, topOffset);
    this.redraw();
  }

  drawXAxisLabels(yOffset = 0) {
    const yBuffer = yOffset === 0 ? this.axisBuffer : this.axisBuffer * -0.5;
    const baseYPos = yOffset === 0 ? this.spectroInfo.height : yOffset;

    // Now we need tick marks for ms along the X-axis
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = this.spectroInfo.width / time;

    // every 100 ms a small tick and every 1000 a big tick
    for (let i = 0; i < time; i += 10) {
      const length = i % 1000 === 0 ? yBuffer * 8 : yBuffer * 4;
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
          text: `${i}ms`,
          x: i * timeToPixels,
          y: baseYPos + length,
          offsetX: 3,
          offsetY: yOffset === 0 ? 8 : -8,
        });
      }
    }
  }

  drawXAxisLabelsCompressed(yOffset = 0, topOffset = 0) {
    const yBuffer = yOffset === 0 ? this.axisBuffer : this.axisBuffer * -0.5;
    const baseYPos = yOffset === 0 ? this.spectroInfo.height : yOffset;
    const baseTopPos = topOffset === 0 ? 0 : -topOffset;
    const topBuffer = topOffset === 0 ? this.axisBuffer * 3 : this.axisBuffer * -0.5;

    // For compressed we need to draw based on the start/endTimes instead of the standard
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = this.spectroInfo.width / time;

    const { start_times, end_times, widths } = this.spectroInfo;
    if (start_times && end_times && widths) {
      // We need a pixel time to map to the 0 position
      let pixelOffset = 0;
      for (let i = 0; i < start_times.length; i += 1) {
        const length = yBuffer * 4;
        const start_time = start_times[i];
        const end_time = end_times[i];
        const width = widths[i];
        this.lineDataX.push({
          line: {
            type: "LineString",
            coordinates: [
              [0 + pixelOffset, baseYPos + yBuffer],
              [0 * timeToPixels + pixelOffset, baseYPos + length],
            ],
          },
          thicker: true,
        });
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
        this.textDataX.push({
          text: `${start_time}ms`,
          x: 0 + pixelOffset,
          y: baseYPos + length,
          offsetX: 3,
          offsetY: yOffset === 0 ? 16 : -16,
        });
        this.textDataX.push({
          text: `${end_time}ms`,
          x: width + pixelOffset,
          y: baseTopPos,
          offsetX: 3,
          offsetY: baseTopPos === 0 ? -16 : 16,
        });
        pixelOffset += width;
        // Need to add the current
      }
    }
  }

  calcGridLines() {
    // Y-Axis grid lines:
    const xBuffer = this.axisBuffer;
    const hz = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const hzToPixels = this.spectroInfo.height / hz;
    for (let i = 0; i < hz; i += 10000) {
      this.gridLines.push({
        line: {
          type: "LineString",
          coordinates: [
            [0 - xBuffer - length, this.spectroInfo.height - i * hzToPixels],
            [this.spectroInfo.width, this.spectroInfo.height - i * hzToPixels],
          ],
        },
        grid: true,
      });
    }
    const baseYPos = this.spectroInfo.height;

    // Now we need tick marks for ms along the X-axis
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = this.spectroInfo.width / time;

    // every 100 ms a small tick and every 1000 a big tick
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

  drawYAxis(offset = 0) {
    const xBuffer = offset === 0 ? this.axisBuffer : this.axisBuffer * -0.25;
    const yAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [offset - xBuffer, 0],
        [offset - xBuffer, this.spectroInfo.height + xBuffer],
      ],
    };
    this.lineDataY.push({ line: yAxis });

    // Lets do the vertical Hz axis now
    const hz = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const hzToPixels = this.spectroInfo.height / hz;
    for (let i = 0; i < hz; i += 10000) {
      const length = i % 10000 === 0 ? xBuffer * 8 : xBuffer * 4;
      this.lineDataY.push({
        line: {
          type: "LineString",
          coordinates: [
            [offset - xBuffer, this.spectroInfo.height - i * hzToPixels],
            [offset - xBuffer - length, this.spectroInfo.height - i * hzToPixels],
          ],
        },
        thicker: i % 10000 === 0,
      });
      this.textDataY.push({
        text: `${(i + this.spectroInfo.low_freq) / 1000}KHz`,
        x: offset - xBuffer - length,
        y: this.spectroInfo.height - i * hzToPixels,
        offsetX: offset === 0 ? -25 : 25,
        offsetY: 0,
      });
    }
  }

  drawXAxis(bottomOffset = 0, topOffset = 0) {
    const xAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, this.spectroInfo.height + this.axisBuffer],
        [this.spectroInfo.width, this.spectroInfo.height + this.axisBuffer],
      ],
    };

    this.lineDataX.push({ line: xAxis });
    this.drawYAxis();

    if (this.spectroInfo.start_times && this.spectroInfo.end_times) {
      this.drawXAxisLabelsCompressed(bottomOffset, topOffset);
    } else {
      this.drawXAxisLabels(bottomOffset);
    }
  }
  createLabels() {
    // Take spectro Info and create lines for X/Y axis
    this.textDataX = [];
    this.lineDataX = [];
    this.textDataY = [];
    this.lineDataY = [];
    const xAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, this.spectroInfo.height + this.axisBuffer],
        [this.spectroInfo.width, this.spectroInfo.height + this.axisBuffer],
      ],
    };

    this.lineDataX.push({ line: xAxis });
    this.drawYAxis();

    if (this.spectroInfo.start_times && this.spectroInfo.end_times) {
      this.drawXAxisLabelsCompressed();
    } else {
      this.drawXAxisLabels();
    }
  }

  redraw() {
    // add some styles
    const combinedLineData = this.lineDataX.concat(this.lineDataY);
    this.lineLayer
      .data(combinedLineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    const combinedTextData = this.textDataX.concat(this.textDataY);
    this.textLayer.data(combinedTextData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.lineLayer.data([]).draw();
    this.textLayer.data([]).draw();
  }

  setGridEnabled(val: boolean) {
    this.gridEnabled = val;
    if (this.gridEnabled) {
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
        strokeColor: "#00FFFF",
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
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
  createTextStyle(): LayerStyle<TextData> {
    return {
      ...{
        strokeColor: "yellow",
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
        uniformPolygon: true,
        fill: false,
      },
      color: () => {
        return "white";
      },
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
    };
  }
}
