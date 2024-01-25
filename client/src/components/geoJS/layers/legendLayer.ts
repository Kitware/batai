/* eslint-disable class-methods-use-this */
import { SpectroInfo } from "../geoJSUtils";
import { LayerStyle } from "./types";

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
  lineData: LineData[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;

  textData: TextData[];
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
    this.lineData = [];
    this.spectroInfo = spectroInfo;
    this.textData = [];
    this.axisBuffer = 5;
    this.event = event;
    this.gridEnabled = true;
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["text", "line"],
    });
    this.textLayer = layer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .position((data: TextData) => ({ x: data.x, y: data.y }));

    this.lineLayer = layer.createFeature("line");

    this.textStyle = this.createTextStyle();
    this.lineStyle = this.createLineStyle();
    this.gridLines = [];
    this.createLabels();

  }

  drawXAxisLabels() {
    // Now we need tick marks for ms along the X-axis
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = this.spectroInfo.width / time;

    // every 100 ms a small tick and every 1000 a big tick
    for (let i = 0; i < time; i += 10) {
      const length = i % 1000 === 0 ? this.axisBuffer * 8 : this.axisBuffer * 4;
      if (i % 50 === 0) {
        this.lineData.push({
          line: {
            type: "LineString",
            coordinates: [
              [i * timeToPixels, this.spectroInfo.height + this.axisBuffer],
              [i * timeToPixels, this.spectroInfo.height + length],
            ],
          },
          thicker: i % 1000 === 0,
        });
        this.textData.push({
          text: `${i}ms`,
          x: i * timeToPixels,
          y: this.spectroInfo.height + length,
          offsetX: 3,
          offsetY: 8,
        });
      }
      this.gridLines.push({
        line: {
          type: "LineString",
          coordinates: [
            [i * timeToPixels, 0],
            [i * timeToPixels, this.spectroInfo.height + length],
          ],
        },
        grid: true,
      });
    }
  }

  drawXAxisLabelsCompressed() {
    // For compressed we need to draw based on the start/endTimes instead of the standard
    const time = this.spectroInfo.end_time - this.spectroInfo.start_time;
    const timeToPixels = this.spectroInfo.width / time;

    const { start_times, end_times } = this.spectroInfo;
    if (start_times && end_times) {
        // We need a pixel time to map to the 0 position
        let pixelOffset = 0;
        for (let i =0; i< start_times.length; i+= 1) {
            const length = this.axisBuffer * 8;
            const start_time = start_times[i];
            const end_time = end_times[i];
            this.lineData.push({
                line: {
                  type: "LineString",
                  coordinates: [
                    [(0 + pixelOffset), this.spectroInfo.height + this.axisBuffer],
                    [(0 * timeToPixels) + pixelOffset, this.spectroInfo.height + length],
                  ],
                },
                thicker:true,
              });
              this.lineData.push({
                line: {
                  type: "LineString",
                  coordinates: [
                    [((end_time - start_time) * timeToPixels) + pixelOffset, this.spectroInfo.height + this.axisBuffer],
                    [((end_time - start_time) * timeToPixels) + pixelOffset, this.spectroInfo.height + length],
                  ],
                },
                thicker:true,
              });
              this.lineData.push({
                line: {
                  type: "LineString",
                  coordinates: [
                    [((end_time - start_time) * timeToPixels) + pixelOffset, this.spectroInfo.height + this.axisBuffer],
                    [((end_time - start_time) * timeToPixels) + pixelOffset, 0],
                  ],
                },
                grid:true,
              });

            // Need to decide what text to add to the label
            //   this.textData.push({
            //     text: `${start_time}ms`,
            //     x: (0 + pixelOffset),
            //     y: this.spectroInfo.height + length,
            //     offsetX: 3,
            //     offsetY: i > 0 ? 24: 8,
            //   });
            //   this.textData.push({
            //     text: `${end_time}ms`,
            //     x: ((start_time - end_time) * timeToPixels) + pixelOffset,
            //     y: this.spectroInfo.height + length,
            //     offsetX: 3,
            //     offsetY: i != start_times.length -1 ? 8 : 24,
            //   });
            // Need to add the current 
            pixelOffset += (end_time - start_time) * timeToPixels;
        }
    }

  }

  createLabels() {
    // Take spectro Info and create lines for X/Y axis
    const xAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, this.spectroInfo.height + this.axisBuffer],
        [this.spectroInfo.width, this.spectroInfo.height + this.axisBuffer],
      ],
    };
    const yAxis: GeoJSON.LineString = {
      type: "LineString",
      coordinates: [
        [0 - this.axisBuffer, 0],
        [0 - this.axisBuffer, this.spectroInfo.height + this.axisBuffer],
      ],
    };
    this.lineData.push({ line: xAxis });
    this.lineData.push({ line: yAxis });

    // Lets do the vertical Hz axis now
    const hz = this.spectroInfo.high_freq - this.spectroInfo.low_freq;
    const hzToPixels = this.spectroInfo.height / hz;
    for (let i = 0; i < hz; i += 10000) {
      const length = i % 10000 === 0 ? this.axisBuffer * 8 : this.axisBuffer * 4;
      this.lineData.push({
        line: {
          type: "LineString",
          coordinates: [
            [0 - this.axisBuffer, this.spectroInfo.height - i * hzToPixels],
            [0 - this.axisBuffer - length, this.spectroInfo.height - i * hzToPixels],
          ],
        },
        thicker: i % 10000 === 0,
      });
      this.textData.push({
        text: `${i / 1000}KHz`,
        x: 0 - this.axisBuffer - length,
        y: this.spectroInfo.height - i * hzToPixels,
        offsetX: -25,
        offsetY: 0,
      });
      this.gridLines.push({
        line: {
          type: "LineString",
          coordinates: [
            [0 - this.axisBuffer - length, this.spectroInfo.height - i * hzToPixels],
            [this.spectroInfo.width, this.spectroInfo.height - i * hzToPixels],
          ],
        },
        grid: true,
      });
    }
    if (this.spectroInfo.start_times && this.spectroInfo.end_times) {
        this.drawXAxisLabelsCompressed();
    } else {
        this.drawXAxisLabels();
    }
  }

  redraw() {
    // add some styles
    const lineData = this.gridEnabled ? this.lineData.concat(this.gridLines) : this.lineData;
    this.lineLayer
      .data(lineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    this.textLayer.data(this.textData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.lineLayer.data([]).draw();
    this.textLayer.data([]).draw();
  }

  setGridEnabled(val: boolean) {
    this.gridEnabled = val;
    this.redraw();
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
