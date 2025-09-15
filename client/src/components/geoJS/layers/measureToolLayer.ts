import geo, { GeoEvent } from 'geojs';
import { SpectroInfo, geojsonToSpectro } from '../geoJSUtils';
import { TextData } from './types';
import BaseTextLayer from './baseTextLayer';


export default class MeasureToolLayer extends BaseTextLayer<TextData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  frequencyRulerLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pointAnnotation: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineAnnotation: any;

  mode: null | 'rectangle';
  dragging: boolean;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
  ) {
    super(geoViewerRef, event, spectroInfo);

    const frequencyRulerLayer = this.geoViewerRef.createLayer("feature", {
      features: ['point', 'line'],
    });
    this.frequencyRulerLayer = frequencyRulerLayer;
    this.mode = null;
    this.pointAnnotation= null;
    this.lineAnnotation = null;
    this.dragging = false;

    this.textStyle = this.createTextStyle();
  }

  enableDrawing() {
    // Frequency ruler
    this.lineAnnotation = this.frequencyRulerLayer.createFeature('line')
      .data([[
        {x: 0, y: 0},
        {x: this.spectroInfo.width, y: 0},
      ]])
      .style({
        strokeColor: 'white',
        strokeWidth: 2,
      });
    this.pointAnnotation = this.frequencyRulerLayer.createFeature('point')
      .data([{x: 0, y: 0}])
      .style({
        radius: 10,
        fillColor: 'blue',
        stroke: true,
        strokeColor: 'white',
        strokeWidth: 5,
      });
    this.geoViewerRef.geoOn(geo.event.mousedown, (e: GeoEvent) => {
      const gcs = this.geoViewerRef.displayToGcs(e.map);
      const p = this.pointAnnotation.data()[0];
      const dx = gcs.x - p.x;
      const dy = gcs.y - p.y;
      if (Math.sqrt(dx*dx + dy*dy) < 10) {
        this.geoViewerRef.interactor().addAction({
          action: 'dragpoint',
          name: 'drag point with mouse',
          owner: 'MeasureToolLayer',
          input: 'left',
        });
        this.dragging = true;
      }
    });
    this.geoViewerRef.geoOn(geo.event.actionmove, (e: GeoEvent) => {
      if (this.dragging) {
        this.updateRuler(e.mouse.geo.y);
      }
    });
    this.geoViewerRef.geoOn(geo.event.mouseup, () => {
      this.dragging = false;
      this.geoViewerRef.interactor().removeAction(undefined, undefined, 'MeasureToolLayer');
    });
    this.frequencyRulerLayer.draw();
  }

  updateRuler(newY: number) {
    this.lineAnnotation.data([[
      {x: 0, y: newY},
      {x: this.spectroInfo.width, y: newY},
    ]]);
    this.pointAnnotation.data([{x: 0, y: newY}]);
    this.frequencyRulerLayer.draw();
    const height = Math.max(this.scaledHeight, this.spectroInfo.height);
    const freq = height - newY >= 0
      ? ((height - newY) * (this.spectroInfo.high_freq - this.spectroInfo.low_freq)) / height / 1000 + this.spectroInfo.low_freq / 1000
      : -1;
    console.log(freq);
  }

  disableDrawing() {
    this.mode = null;
    this.textLayer.data([]).draw();
    this.clearRulerLayer();
  }

  clearRulerLayer() {
    this.pointAnnotation.data([]);
    this.lineAnnotation.data([]);
    this.textLayer.data([]).draw();
    this.frequencyRulerLayer.draw();
  }
}
