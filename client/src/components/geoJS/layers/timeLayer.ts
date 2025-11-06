/* eslint-disable class-methods-use-this */
import { SpectrogramAnnotation, SpectrogramSequenceAnnotation } from "../../../api/api";
import { SpectroInfo, spectroSequenceToGeoJSon, spectroToGeoJSon } from "../geoJSUtils";
import BaseTextLayer from "./baseTextLayer";
import { LayerStyle } from "./types";

interface LineData {
  line: GeoJSON.LineString;
  thicker?: boolean;
  grid?: boolean;
  markerLine?: boolean; // Line for markiing time endpoints
}

interface TextData {
  text: string;
  x: number;
  y: number;
  offsetY?: number;
  offsetX?: number;
  textScaled?: undefined | number;
  textBaseline?: 'middle' | 'top' | 'bottom';
}

export default class TimeLayer extends BaseTextLayer<TextData> {
  lineData: LineData[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineLayer: any;

  lineStyle: LayerStyle<LineData>;

  displayDuration: boolean;

  displaying: { sequence: boolean; pulse: boolean };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    super(geoViewerRef, event, spectroInfo);
    this.lineData = [];
    this.textData = [];
    this.displayDuration = true;
    this.displaying = { sequence: true, pulse: true };
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["text", "line"],
    });
    this.textLayer = layer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .position((data: TextData) => ({ x: data.x, y: data.y }));

    this.lineLayer = layer.createFeature("line");
    this.displayDuration = true;
    this.lineStyle = this.createLineStyle();
  }

  destroy() {
    if (this.textLayer) {
      this.geoViewerRef.deleteLayer(this.textLayer);
    }
    if (this.lineLayer) {
      this.geoViewerRef.deleteLayer(this.lineLayer);
    }
  }

  createRange(
    annotationData: SpectrogramAnnotation[],
    sequenceData: SpectrogramSequenceAnnotation[] = []
  ) {
    this.textData = [];
    this.lineData = [];
    const lineDist = 12;
    if (this.displaying.pulse) {
      annotationData.forEach((annotation: SpectrogramAnnotation) => {
        const polygon = spectroToGeoJSon(
          annotation,
          this.spectroInfo,
          1,
          this.scaledWidth,
          this.scaledHeight
        );
        const { start_time, end_time } = annotation;
        const [xmin, ymin] = polygon.coordinates[0][0];
        const [xmax, ymax] = polygon.coordinates[0][2];
        // For the compressed view we need to filter out default or NaN numbers
        if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
          return;
        }
        if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
          return;
        }
        // We create two small lines for the beginning/end of annotation
        this.lineData.push({
          line: {
            type: "LineString",
            coordinates: [
              [xmin, ymin],
              [xmin, ymin + lineDist],
            ],
          },
          markerLine: true,
          thicker: true,
        });
        this.lineData.push({
          line: {
            type: "LineString",
            coordinates: [
              [xmax, ymin],
              [xmax, ymin + lineDist],
            ],
          },
          markerLine: true,
          thicker: true,
        });
        // Now we need to create the text Labels
        this.textData.push({
          text: `${start_time}ₘₛ`,
          x: xmin,
          y: ymin + lineDist + 5,
          textBaseline: 'top',
        });
        this.textData.push({
          text: `${end_time}ₘₛ`,
          x: xmax,
          y: ymin + lineDist + 5,
          textBaseline: 'top',
        });
      });
    }
    const compressedView = !!(this.spectroInfo.compressedWidth);
    const offsetY = compressedView ? -80 : 0;
    if (this.displaying.sequence) {
      sequenceData.forEach((annotation: SpectrogramSequenceAnnotation) => {
        const polygon = spectroSequenceToGeoJSon(
          annotation,
          this.spectroInfo,
          -10,
          -50,
          this.scaledWidth,
          this.scaledHeight,
          offsetY
        );
        const { start_time, end_time } = annotation;
        const [xmin, ymin] = polygon.coordinates[0][0];
        const [xmax, ymax] = polygon.coordinates[0][2];
        // For the compressed view we need to filter out default or NaN numbers
        if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
          return;
        }
        if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
          return;
        }
        // We create two small lines for the beginning/end of annotation
        this.lineData.push({
          line: {
            type: "LineString",
            coordinates: [
              [xmin, ymax],
              [xmin, ymax - lineDist],
            ],
          },
          markerLine: true,
          thicker: true,
        });
        this.lineData.push({
          line: {
            type: "LineString",
            coordinates: [
              [xmax, ymax],
              [xmax, ymax - lineDist],
            ],
          },
          markerLine: true,
          thicker: true,
        });
        // Now we need to create the text Labels
        this.textData.push({
          text: `${start_time}ₘₛ`,
          x: xmin,
          y: ymax - lineDist,
        });
        this.textData.push({
          text: `${end_time}ₘₛ`,
          x: xmax,
          y: ymax - lineDist,
        });
      });
    }
  }

  createDuration(
    annotationData: SpectrogramAnnotation[],
    sequenceData: SpectrogramSequenceAnnotation[] = []
  ) {
    this.textData = [];
    this.lineData = [];
    const lineDist = 12;
    if (this.displaying.pulse) {
      annotationData.forEach((annotation: SpectrogramAnnotation) => {
        const polygon = spectroToGeoJSon(
          annotation,
          this.spectroInfo,
          this.scaledWidth,
          this.scaledHeight
        );
        const { start_time, end_time } = annotation;
        const [xmin, ymin] = polygon.coordinates[0][0];
        const [xmax, ymax] = polygon.coordinates[0][2];
        // For the compressed view we need to filter out default or NaN numbers
        if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
          return;
        }
        if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
          return;
        }
        const xpos = (xmin + xmax) / 2.0;
        const ypos = (ymax + ymin) / 2.0;
        // Now we need to create the text Labels
        this.textData.push({
          text: `${end_time - start_time}ₘₛ`,
          x: xpos,
          y: ypos + lineDist,
        });
      });
    }
    const compressedView = !!(this.spectroInfo.compressedWidth);
    const offsetY = compressedView ? -50 : 30;
    if (this.displaying.sequence) {
      sequenceData.forEach((annotation: SpectrogramSequenceAnnotation) => {
        const polygon = spectroSequenceToGeoJSon(
          annotation,
          this.spectroInfo,
          -10,
          -50,
          this.scaledWidth,
          this.scaledHeight
        );
        const { start_time, end_time } = annotation;
        const [xmin, ymin] = polygon.coordinates[0][0];
        const [xmax, ymax] = polygon.coordinates[0][2];
        // For the compressed view we need to filter out default or NaN numbers
        if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
          return;
        }
        if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
          return;
        }
        const xpos = (xmin + xmax) / 2.0;
        // Now we need to create the text Labels
        this.textData.push({
          text: `${end_time - start_time}ₘₛ`,
          x: xpos,
          y: ((ymax - ymin) / 2.0) + -35 + offsetY,
        });
      });
    }
  }

  formatData(
    annotationData: SpectrogramAnnotation[],
    sequenceData: SpectrogramSequenceAnnotation[] = []
  ) {
    if (!this.displayDuration) {
      this.createRange(annotationData, sequenceData);
    } else {
      this.createDuration(annotationData, sequenceData);
    }
  }

  redraw() {
    // add some styles
    this.lineLayer
      .data(this.lineData)
      .line((d: LineData) => d.line.coordinates)
      .style(this.createLineStyle())
      .draw();
    this.textLayer.data(this.textData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.lineLayer.data([]).draw();
    this.textLayer.data([]).draw();
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
      strokeColor: () => {
        return this.color;
      },
      strokeOpacity: (_point, _index, data) => {
        // Reduce the rectangle opacity if a polygon is also drawn
        if (data.markerLine && this.zoomLevel < 0) {
          return 0.0;
        }
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
        fontSize: `${this.getFontSize(16, 12, this.xScale)}px`,
      },
      color: () => {
        return this.color;
      },
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textScaled: this.textScaled,
      textBaseline: 'middle',
    };
  }

  setDisplaying(data: { pulse: boolean; sequence: boolean }) {
    this.displaying = data;
  }
}
