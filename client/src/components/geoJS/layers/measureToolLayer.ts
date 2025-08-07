import geo, { GeoEvent } from 'geojs';
import { SpectroInfo, geojsonToSpectro } from '../geoJSUtils';
import { LayerStyle, RectGeoJSData, TextData } from './types';


export default class MeasureToolLayer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  geoViewerRef: any;
  spectroInfo: SpectroInfo;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  event: (name: string, data: any) => void;

  scaledWidth: number;
  scaledHeight: number;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  measureLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  measureAnnotation: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textAnnotation: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  textFeature: any;

  mode: null | 'rectangle';


  rectStyle: LayerStyle<RectGeoJSData>;
  textStyle: LayerStyle<TextData>;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
  ) {
    this.geoViewerRef = geoViewerRef;
    this.spectroInfo = spectroInfo;
    this.event = event;

    this.scaledWidth = 0;
    this.scaledHeight = 0;

    const rectangleLayer = this.geoViewerRef.createLayer("annotation", {
      clickToEdit: false
    });
    const labelLayer = this.geoViewerRef.createLayer("feature", {
      features: ['text'],
    });
    console.log('adding labelLayer', labelLayer);
    this.textLayer = labelLayer;
    this.measureLayer = rectangleLayer;
    this.textFeature = null;
//    this.textFeature = layer
//      .createFeature("text")
//      .text((data: TextData) => data.text)
//      .position((data: TextData) => ({ x: data.x, y: data.y }));
    this.mode = null;
    this.measureLayer.mode(this.mode);
    this.measureAnnotation = null;

    this.textStyle = this.createTextStyle();
    this.rectStyle = this.createRectStyle();
  }

  handleFinishDrawing(e: GeoEvent) {
    // 0. Make sure it is a legal annotation (doesn't cross compressed segments)
    this.applyStyles();
    // 3. Remove existing annotation (only one measure at a time)
    this.updateActiveMeasureAnnotation(e.annotation.id());
    // 4. Draw text with measurements
    // 5. Trigger redraw?
    this.measureLayer.draw();
    this.enableDrawing();
  }

  updateActiveMeasureAnnotation(activeAnnotationId: number) {
    console.log('updating active annotation to be ', activeAnnotationId);
    const annotations = this.measureLayer.annotations();
    if (annotations && annotations.length) {
      annotations.forEach((annotation: any) => {
        const id = annotation.id();
        if (id !== activeAnnotationId) {
          console.log('removing annotation ', id)
          this.measureLayer.removeAnnotation(annotation);
        }
      });
    }
  }

  applyStyles() {
    const annotations = this.measureLayer.annotations();
    if (annotations && annotations.length) {
      annotations.forEach((annotation: any) => {
        annotation.style(this.createRectStyle());
      });
    }
    this.measureLayer.draw();
  }

  _updateMode() {
    this.measureLayer.mode(this.mode, this.measureAnnotation);
  }

  enableDrawing() {
    console.log(geo.event);
    this.mode = 'rectangle';
    this._updateMode();
    this.measureAnnotation = this.measureLayer.annotations()[0];
    this.measureLayer.geoOn(geo.event.annotation.add, (e: GeoEvent) => {
      // this.updateActiveMeasureAnnotation(e.annotation.id());
      console.log(e);
      if (this.measureLayer.annotations().length > 1) {
        const oldAnnotation = this.measureLayer.annotations()[1];
        this.measureLayer.removeAnnotation(oldAnnotation);
      }
      // this.measureAnnotation = this.measureLayer.annotations()[0];
      // this.applyStyles();
      // this.measureLayer.draw();
      // this._updateMode();
    });
    Object.values(geo.event.annotation).forEach((eventName: string) => {
      this.measureLayer.geoOn(eventName, (e: GeoEvent) => {
        console.log(eventName, e);
      });
    });
    this.measureLayer.geoOn(geo.event.annotation.mode, (e: GeoEvent) => {
      // If we're still in "measure mode", re-enable drawing for the annotation
      this.applyStyles();
      this.measureLayer.annotations()[0].label('');
      this.measureLayer.draw();
      // if (this.mode === 'rectangle') {
        // this._updateMode();
      // }
    });
    this.measureLayer.geoOn(geo.event.annotation.state, (e: GeoEvent) => {
      console.log(this.measureLayer.annotations()[0].state());
      if (this.measureLayer.annotations()[0].state() === 'done') {
        this.showMeasurements(this.measureLayer.annotations()[0]);
      }
    });
  }

  disableDrawing() {
    this.mode = null;
    this._updateMode();
    this.measureLayer.geoOff(geo.event.annotation.add);
    this.measureLayer.geoOff(geo.event.actionup);
    this.measureLayer.removeAllAnnotations();
    this.measureAnnotation = null;
    this.textFeature.data([]).draw();
  }

  showMeasurements(annotation: any) {
    if (!annotation.features() && !annotation.features.length) {
      // The annotation has no features
      return;
    }
    const rectangle: GeoJSON.Feature<GeoJSON.Polygon> = annotation.geojson();
    const measurements = geojsonToSpectro(rectangle, this.spectroInfo);
    if (measurements.error) {
      // Raise
      console.error(measurements.error);
      return;
    }
    const coordinates = rectangle.geometry.coordinates[0];
    const determineFreqOffset = (input: number) => {
      if (input < 10000) {
        return 31;
      }
      if (input < 100000) {
        return 33;
      }
      return 35;
    };
    const measureData = [
      {
         label: `${measurements.start_time}ms`,
         x: coordinates[0][0],
         y: coordinates[0][1],
         offset: { x: 0, y: 10 },
      },
      {
         label: `${measurements.end_time}ms`,
         x: coordinates[3][0],
         y: coordinates[3][1],
         offset: { x: 0, y: 10 },
      },
      {
         label: `${measurements.low_freq}Hz`,
         x: coordinates[3][0],
         y: coordinates[3][1],
         offset: { x: determineFreqOffset(measurements.low_freq), y: -5 },
      },
      {
         label: `${measurements.high_freq}Hz`,
         x: coordinates[2][0],
         y: coordinates[2][1],
         offset: { x: determineFreqOffset(measurements.high_freq), y: 5 },
      },
    ];
    if (!this.textFeature) {
      this.textFeature = this.textLayer.createFeature('text');
    }
    this.textFeature.data(
      measureData
    ).position(
      function (dataPoint: { label: string, x: number, y: number }) {
        const { x, y } = dataPoint;
        return { x, y };
      }
    ).text(
      function (dataPoint: { label: string, x: number, y: number }) {
        return dataPoint.label;
      }
    ).style({
      fontSize: '12px',
      color: 'white',
      offset: function(dataPoint: { offset: { x: number, y: number } }) {
        return dataPoint.offset;
      },
    }).draw();
  }

  createTextStyle(): LayerStyle<TextData> {
    return {
      ...{
        stroleColor: "yellow",
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
      textAlign: 'starts',
    };
  }

  createRectStyle(): LayerStyle<RectGeoJSData> {
    return {
      ...{
        strokeColor: 'black',
        strokeWidth: 1.0,
        antialiasing: 0,
        stroke: true,
        uniformPolygon: true,
        fill: false,
      },
      fill: false,
      strokeColor: "cyan",
    };
  }
}
