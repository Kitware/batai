/* eslint-disable class-methods-use-this */
import { SpectroInfo } from "../geoJSUtils";
import { LayerStyle } from "./types";

interface RectCompressedGeoJSData {
  polygon: GeoJSON.Polygon;
}


function scaleCompressedTime(start_time: number, end_time: number, spectroInfo: SpectroInfo, yScale: number, scaledWidth: number, scaledHeight: number) {
  const adjustedWidth = scaledWidth > spectroInfo.width ? scaledWidth : spectroInfo.width;
  const adjustedHeight = scaledHeight > spectroInfo.height ? scaledHeight : spectroInfo.height;

  const widthScale = adjustedWidth / (spectroInfo.end_time - spectroInfo.start_time);
  const heightScale = adjustedHeight / (spectroInfo.high_freq - spectroInfo.low_freq);
  // Now we remap our annotation to pixel coordinates
  const low_freq =
    adjustedHeight - (spectroInfo.low_freq) * heightScale;
  const high_freq =
    adjustedHeight - (spectroInfo.high_freq) * heightScale;
  const start_time_scaled = start_time * widthScale;
  const end_time_scaled = end_time * widthScale;
  return {
    type: "Polygon",
    coordinates: [
      [
        [start_time_scaled, low_freq * yScale],
        [start_time_scaled, high_freq * yScale],
        [end_time_scaled, high_freq * yScale],
        [end_time_scaled, low_freq * yScale],
        [start_time_scaled, low_freq * yScale],
      ],
    ],
  } as GeoJSON.Polygon;

}

export default class CompressedOverlayLayer {
  formattedData: RectCompressedGeoJSData[];


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  featureLayer: any;


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  spectroInfo: SpectroInfo;

  style: LayerStyle<RectCompressedGeoJSData>;

  scaledWidth: number;
  scaledHeight: number;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    spectroInfo: SpectroInfo
  ) {
    this.geoViewerRef = geoViewerRef;
    this.spectroInfo = spectroInfo;
    this.formattedData = [];
    this.scaledWidth = 0;
    this.scaledHeight = 0;
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["polygon"],
    });
    this.featureLayer = layer
      .createFeature("polygon", { selectionAPI: true });
    this.style = this.createStyle();
  }

  setScaledDimensions(newWidth: number, newHeight: number) {
    this.scaledWidth = newWidth;
    this.scaledHeight = newHeight;    
  }

  destroy() {
    if (this.featureLayer) {
      this.geoViewerRef.deleteLayer(this.featureLayer);
    }
  }

  formatData(
    startTimes: number[],
    endTimes: number[],
    yScale = 1,
  ) {
    const arr: RectCompressedGeoJSData[] = [];

    for (let i = 0; i< startTimes.length; i += 1) {
      const startTime = startTimes[i];
      const endTime = endTimes[i];
      const polygon = scaleCompressedTime(startTime, endTime, this.spectroInfo, yScale, this.scaledWidth, this.scaledHeight);
      const newAnnotation: RectCompressedGeoJSData = {
        polygon,
      };
      arr.push(newAnnotation);
    }
    this.formattedData = arr;
  }

  redraw() {
    // add some styles
    this.featureLayer
      .data(this.formattedData)
      .polygon((d: RectCompressedGeoJSData) => d.polygon.coordinates[0])
      .style(this.createStyle())
      .draw();
  }

  disable() {
    this.featureLayer.data([]).draw();
  }

  createStyle(): LayerStyle<RectCompressedGeoJSData> {
    return {
      ...{
        strokeColor: "black",
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
        uniformPolygon: true,
        fill: false,
      },
      // Style conversion to get array objects to work in geoJS
      position: (point) => {
        return { x: point[0], y: point[1] };
      },
      strokeColor: (_point, _index, data) => {
        return "cyan";
      },
    };
  }
}
