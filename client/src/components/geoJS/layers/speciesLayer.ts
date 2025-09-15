/* eslint-disable class-methods-use-this */
import { SpectrogramAnnotation } from "../../../api/api";
import { SpectroInfo, spectroToGeoJSon } from "../geoJSUtils";
import BaseTextLayer from "./baseTextLayer";
import { LayerStyle } from "./types";

interface TextData {
  text: string;
  x: number;
  y: number;
  offsetY?: number;
  offsetX?: number;
}

export default class SpeciesLayer extends BaseTextLayer<TextData> {


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo
  ) {
    super(geoViewerRef, event, spectroInfo);
    //Only initialize once, prevents recreating Layer each edit
    const layer = this.geoViewerRef.createLayer("feature", {
      features: ["text"],
    });
    this.textLayer = layer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .position((data: TextData) => ({ x: data.x, y: data.y }));
  }


  formatData(annotationData: SpectrogramAnnotation[]) {
    this.textData = [];
    annotationData.forEach((annotation: SpectrogramAnnotation) => {
      const polygon = spectroToGeoJSon(annotation, this.spectroInfo, 1, this.scaledWidth, this.scaledHeight);
      const [xmin, ymin] = polygon.coordinates[0][0];
      const [xmax, ymax] = polygon.coordinates[0][2];
      // For the compressed view we need to filter out default or NaN numbers
      if (Number.isNaN(xmax) || Number.isNaN(xmin) || Number.isNaN(ymax) || Number.isNaN(ymin)) {
        return;
      }
      if (xmax === -1 && ymin === -1 && ymax === -1 && xmin === -1) {
        return;
      }
      let textOffset = 0;
      const species = annotation.species;
      if (species) {
        for (let i =0; i< species.length; i += 1) {
          const specie = species[i];
          this.textData.push({
            text: `${specie.species_code || specie.common_name}`,
            x: xmin + (xmax - xmin) / 2.0,
            y: ymax + textOffset,
          });
          textOffset -= 40;
    
        }
      }
    });
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
      color: () => {
        return this.color;
      },
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textAlign: 'center',
      textBaseline: 'bottom',
      textScaled: this.textScaled
    };
  }
}
