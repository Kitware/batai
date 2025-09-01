

/* eslint-disable class-methods-use-this */
import { SpectroInfo } from "../geoJSUtils";
import { LayerStyle } from "./types";
import geo from "geojs";



export default abstract class BaseTextLayer<D> {
  textData: D[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  spectroInfo: SpectroInfo;

  textStyle: LayerStyle<D>;

  scaledWidth: number;
  scaledHeight: number;




  textScaled: number | undefined;

  zoomLevel: number;

  xScale: number;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    this.geoViewerRef = geoViewerRef;
    this.spectroInfo = spectroInfo;
    this.textData = [];
    this.scaledWidth = 0;
    this.scaledHeight = 0;
    this.event = event;
    this.xScale = 0;
    //Only initialize once, prevents recreating Layer each edit
    this.textStyle = this.createTextStyle();
    this.geoViewerRef.geoOn(geo.event.zoom, (event: {zoomLevel: number}) => this.onZoom(event));
    this.zoomLevel = this.geoViewerRef.camera().zoomLevel;

  }

  setScaledDimensions(newWidth: number, newHeight: number) {
    this.scaledWidth = newWidth;
    this.scaledHeight = newHeight;
    if (this.spectroInfo.compressedWidth) {
      this.xScale = newWidth / this.spectroInfo.compressedWidth;
    } else {
      this.xScale = newWidth / this.spectroInfo.width;
    }
  }

  onZoom(event: {zoomLevel: number}) {
  this.zoomLevel = event.zoomLevel;
  this.textScaled = undefined;
  if ((this.zoomLevel || 0) < -1.5 ) {
    this.textScaled = -1.5;
  } else if ((this.zoomLevel || 0) > 0) {
    this.textScaled = Math.sqrt(this.zoomLevel || 1);
  } else {
    this.textScaled = this.zoomLevel;
  }
  this.redraw();
}


  destroy() {
    if (this.textLayer) {
      this.geoViewerRef.deleteLayer(this.textLayer);
    }
  }



  redraw() {
    // add some styles
    this.textLayer.data(this.textData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.textLayer.data([]).draw();
  }

  getFontSize(fontA: number, fontB: number, xScale: number) {
  if (xScale >= 2.5) {
    return fontA; // clamp high
  } else if (xScale <= 1.0) {
    return fontB; // clamp low
  } else {
    const t = (xScale - 1.0) / (2.5 - 1.0); // normalized progress
    return fontB + t * (fontA - fontB);     // linear interpolation
  }
}


  createTextStyle(): LayerStyle<D> {
    return {
      ...{
        strokeColor: "white",
        strokeWidth: 2.0,
        antialiasing: 0,
        stroke: true,
        uniformPolygon: true,
        fill: false,
        fontSize: () => this.xScale < 2.5 ? '12px' : '16px'
      },
      color: () => {
        return "white";
      },
      textScaled: this.textScaled,
      textBaseline: 'middle',
    };
  }

}
