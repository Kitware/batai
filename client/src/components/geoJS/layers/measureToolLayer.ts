import geo, { GeoEvent } from 'geojs';
import { SpectroInfo } from '../geoJSUtils';
import { LayerStyle, LineData, TextData } from './types';
import BaseTextLayer from './baseTextLayer';


export default class MeasureToolLayer extends BaseTextLayer<TextData> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  frequencyRulerLayer: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pointAnnotation: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lineAnnotation: any;

  rulerOn: boolean;
  dragging: boolean;
  yValue: number;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
  ) {
    super(geoViewerRef, event, spectroInfo);

    const textLayer = this.geoViewerRef.createLayer('feature', {
      features: ['text']
    });
    this.textLayer = textLayer
      .createFeature("text")
      .text((data: TextData) => data.text)
      .style(this.createTextStyle())
      .position((data: TextData) => ({
        x: data.x,
        y: data.y,
      }));

    const frequencyRulerLayer = this.geoViewerRef.createLayer("feature", {
      features: ['point', 'line'],
    });
    this.frequencyRulerLayer = frequencyRulerLayer;
    this.rulerOn = false;
    this.pointAnnotation= null;
    this.lineAnnotation = null;
    this.dragging = false;
    this.yValue = 0;

    this.textStyle = this.createTextStyle();
  }

  enableDrawing() {
    this.rulerOn = true;
    // Frequency ruler
    this.lineAnnotation = this.frequencyRulerLayer.createFeature('line')
      .data([[
        {x: 0, y: this.yValue},
        {x: this.spectroInfo.width, y: this.yValue},
      ]])
      .style(this.createLineStyle());
    this.pointAnnotation = this.frequencyRulerLayer.createFeature('point')
      .data([{x: 0, y: this.yValue}])
      .style(this.createPointStyle());
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
    this.updateRuler(this.yValue);
  }

  updateRuler(newY: number) {
    if (newY < 0) {
      return;
    }
    this.yValue = newY;
    this.lineAnnotation
      .data([[
        {x: 0, y: this.yValue},
        {x: this.spectroInfo.width, y: this.yValue},
      ]])
      .style(this.createLineStyle());
    this.pointAnnotation
      .data([{x: 0, y: this.yValue}])
      .style(this.createPointStyle());
    this.frequencyRulerLayer.draw();
    const height = Math.max(this.scaledHeight, this.spectroInfo.height);
    const frequency = height - this.yValue >= 0
      ? ((height - newY) * (this.spectroInfo.high_freq - this.spectroInfo.low_freq)) / height / 1000 + this.spectroInfo.low_freq / 1000
      : -1;
    const textValue = `${frequency.toFixed(1)}KHz`;
    this.textData = [
      {
        text: textValue,
        x: 0,
        y: this.yValue,
        offsetY: 20,
        offsetX: 20,
      },
    ];
    this.textLayer.data(this.textData).draw();
  }

  disableDrawing() {
    this.rulerOn = false;
    this.textData = [];
    this.textLayer.data(this.textData).draw();
    this.clearRulerLayer();
  }

  clearRulerLayer() {
    this.pointAnnotation.data([]);
    this.lineAnnotation.data([]);
    this.textLayer.data([]).draw();
    this.frequencyRulerLayer.draw();
  }

  destroy() {
    super.destroy();
    this.textData = [];
    if (this.frequencyRulerLayer) {
      this.geoViewerRef.deleteLater(this.frequencyRulerLayer);
    }
  }

  redraw() {
    if (this.rulerOn) {
      this.updateRuler(this.yValue);
    }
    super.redraw();
  }

  createTextStyle(): LayerStyle<TextData> {
    return {
      color: () => this.color,
      offset: (data: TextData) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textAlign: 'start',
      textScaled: this.textScaled,
      textBaseline: 'bottom',
    };
  }

  createPointStyle(): LayerStyle<LineData> {
    return {
      radius: 10,
      fillColor: this.color,
      stroke: true,
      strokeColor: this.color,
      strokeWidth: 5,
    };
  }

  createLineStyle(): LayerStyle<LineData> {
    return {
      strokeColor: this.color,
      strokeWidth: 2,
    };
  }

  setTextColor(color: string) {
    super.setTextColor(color);
    if (this.rulerOn) {
      this.updateRuler(this.yValue);
    }
  }
}
