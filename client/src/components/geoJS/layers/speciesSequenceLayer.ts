/* eslint-disable class-methods-use-this */
import { SpectrogramSequenceAnnotation } from "../../../api/api";
import { SpectroInfo, spectroSequenceToGeoJSon } from "../geoJSUtils";
import { LayerStyle } from "./types";
import geo from "geojs";

interface TextData {
  text: string;
  x: number;
  y: number;
  offsetY?: number;
  offsetX?: number;
  textType: "species" | "type";
}

export default class SpeciesSequenceLayer {
  textData: TextData[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  spectroInfo: SpectroInfo;

  textStyle: LayerStyle<TextData>;

  scaledWidth: number;
  scaledHeight: number;

  textScaled: number | undefined;

  zoomLevel: number;

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
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["text"],
    });
    this.textLayer = layer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .position((data: TextData) => ({ x: data.x, y: data.y }));

    this.textStyle = this.createTextStyle();
    this.geoViewerRef.geoOn(geo.event.zoom, (event: {zoomLevel: number}) => this.onZoom(event));
    this.zoomLevel = this.geoViewerRef.camera().zoomLevel;
    this.onZoom({zoomLevel: this.zoomLevel });

  }

  setScaledDimensions(newWidth: number, newHeight: number) {
    this.scaledWidth = newWidth;
    this.scaledHeight = newHeight;
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

  formatData(annotationData: SpectrogramSequenceAnnotation[]) {
    this.textData = [];
    const compressedView = !!(this.spectroInfo.compressedWidth);
    const offsetY = compressedView ? -100 : -20;
    annotationData.forEach((annotation: SpectrogramSequenceAnnotation) => {
      const polygon = spectroSequenceToGeoJSon(
        annotation,
        this.spectroInfo,
        -10,
        -120,
        1,
        this.scaledWidth,
        this.scaledHeight
      );
      const [xmin, ymin] = polygon.coordinates[0][0];
      const [xmax, ymax] = polygon.coordinates[0][2];
      // For the compressed view we need to filter out default or NaN numbers
      if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
        return;
      }
      if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
        return;
      }
      let textOffset = -40 + offsetY;
      const species = annotation.species;
      const type = annotation.type;
      if (species) {
        if (type) {
          this.textData.push({
            text: `${type}`,
            x: xmin + (xmax - xmin) / 2.0,
            y: ymin + textOffset,
            textType: "type",
          });
          textOffset -= 40;
        }
        for (let i = 0; i < species.length; i += 1) {
          const specie = species[i];
          this.textData.push({
            text: `${specie.species_code || specie.common_name}`,
            x: xmin + (xmax - xmin) / 2.0,
            y: ymin + textOffset,
            textType: "species",
          });
          textOffset -= 40;
        }
      }
    });
  }

  redraw() {
    // add some styles
    this.textLayer.data(this.textData).style(this.createTextStyle()).draw();
  }

  disable() {
    this.textLayer.data([]).draw();
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
        fontSize: '18px',
      },
      color: (d) => {
        if (d.textType === "type") {
          return "yellow";
        }
        return "white";
      },
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textAlign: "center",
      textScaled: this.textScaled,
    };
  }
}
