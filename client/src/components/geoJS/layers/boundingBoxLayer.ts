import geo, { GeoEvent } from 'geojs';
import BaseTextLayer from "./baseTextLayer";
import { geojsonToSpectro, SpectroInfo } from '../geoJSUtils';
import { LayerStyle, RectGeoJSData, TextData } from './types';

export default class BoundingBoxLayer extends BaseTextLayer<TextData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  boxLayer: any;
  drawing: boolean;
  boxError: string | undefined;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
    drawing?: boolean,
  ) {
    super(geoViewerRef, event, spectroInfo);

    const textLayer = this.geoViewerRef.createLayer('feature', {
      features: ['text']
    });
    this.textLayer = textLayer
      .createFeature('text')
      .text((data: TextData) => data.text)
      .style(this.createTextStyle())
      .position((data: TextData) => ({
        x: data.x,
        y: data.y,
      }));

      this.drawing = drawing || false;
      this.boxError = null;

      this.initialize();
  }

  initialize() {
    if (!this.boxLayer) {
      this.boxLayer = this.geoViewerRef.createLayer('annotation', {
        clickToEdit: true,
        showLabels: false,
        continuousPoiintProximity: false,
        finalPointProximity: 1,
        adjacentPointProximity: 1,
      });
    }
    this.boxLayer.geoOn(geo.event.annotation.state, (e: GeoEvent) => this.handleAnnotationState(e));
    this.boxLayer.geoOn(geo.event.annotation.edit_action, (e: GeoEvent) => this.handleAnnotationEditAction(e));
  }

  handleAnnotationState(e: GeoEvent) {
    if (this.boxLayer !== e.annotation.layer()) {
      // not an annotation owned by this object
      return;
    }
    if (e.annotation.state() === 'done') {
      this.event("update:cursor", { cursor: "default" });
      this.updateLabels(e.annotation);
      this.applyStyles();
      this.redraw();
    }
  }

  handleAnnotationEditAction(e: GeoEvent) {
    if (this.boxLayer !== e.annotation.layer()) {
      return;
    }
    if (e.annotation.state() === 'edit') {
      this.updateLabels(e.annotation);
    }
  }

  updateErrorState(error: string | undefined) {
    this.boxError = error;
    const message = error ? 'The current bounding box spans multiple pulses. The measurement labels are correct, but it is not to scale.' : null;
    this.event("bbox:error", { error: message });
  }

  updateLabels(annotation: any) {
    const geojsonData = annotation.geojson();
    const coordinates = geojsonData.geometry.coordinates[0];
    const {
      start_time: startTime,
      end_time: endTime,
      low_freq: lowFreq,
      high_freq: highFreq,
      error,
    } = geojsonToSpectro(
      geojsonData,
      this.spectroInfo,
      this.scaledWidth,
      this.scaledHeight,
    );

    this.updateErrorState(error);

    const determineFreqOffset = (freq: number) => {
      if (freq < 10000) return 38;
      if (freq < 100000) return 40;
      return 42;
    };

    this.textData = [
      {
        text: `${startTime}ms`,
        x: coordinates[0][0],
        y: coordinates[0][1],
        offsetX: 0,
        offsetY: 10,
      },
      {
        text: `${endTime}ms`,
        x: coordinates[3][0],
        y: coordinates[3][1],
        offsetX: 0,
        offsetY: 10,
      },
      {
        text: `${(lowFreq / 1000).toFixed(1)}KHz`,
        x: coordinates[3][0],
        y: coordinates[3][1],
        offsetX: determineFreqOffset(lowFreq),
        offsetY: -5,
      },
      {
        text: `${(highFreq / 1000).toFixed(1)}KHz`,
        x: coordinates[2][0],
        y: coordinates[2][1],
        offsetX: determineFreqOffset(highFreq),
        offsetY: 5,
      },
    ];
    this.redraw();
  }

  enableDrawing() {
    this.drawing = true;
    this.event("update:cursor", { cursor: "mdi-vector-rectangle" });
    if (this.boxLayer) {
      this.boxLayer.mode('rectangle');
    }
  }

  disableDrawing() {
    this.drawing = false;
    if (this.boxLayer) {
      this.boxLayer.mode(null);
      this.clearAnnotations();
    }
    if (this.textLayer) {
      this.textData = [];
      this.textLayer.data(this.textData).draw();
    }
  }

  clearAnnotations() {
    if (this.boxLayer) {
      this.boxLayer.removeAllAnnotations();
    }
  }

  redraw() {
    if (this.textLayer) {
      this.textLayer.data(this.textData).style(this.createTextStyle()).draw();
    }
    if (this.boxLayer) {
      this.applyStyles();
      this.boxLayer.draw();
    }
  }

  applyStyles() {
    if (this.boxLayer && this.boxLayer.annotations().length) {
      this.boxLayer.annotations().forEach((annotation: any) => {
        annotation.style(this.createRectStyle());
        annotation.editHandleStyle(this.createEditHandleStyle());
      });
    }
  }

  _isDarkMode() {
    return this.color === 'white';
  }

  createRectStyle(): LayerStyle<RectGeoJSData> {
    return {
      strokeWidth: 1.0,
      antialiasing: 0,
      stroke: true,
      uniformPolygon: true,
      fill: false,
      strokeColor: this._isDarkMode() ? 'yellow' : 'blue',
    };
  }

  createTextStyle(): LayerStyle<TextData> {
    return {
      fontSize: '16px',
      color: () => this.color,
      offset: (data) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textScaled: this.textScaled,
    };
  }

  createEditHandleStyle() {
    return {
      handles: {
        rotate: false,
        resize: false,
      },
      strokeColor: this._isDarkMode() ? 'yellow' : 'blue',
    };
  }
}
