import geo, { GeoEvent } from 'geojs';
import { SpectroInfo } from '../geoJSUtils';
import { LayerStyle, LineData, TextData } from './types';
import BaseTextLayer from './baseTextLayer';

function _determineRulerColor(isDragging: boolean, isDarkMode: boolean) {
  if (isDarkMode) {
    return isDragging ? 'orange' : 'yellow';
  }
  return isDragging ? 'cyan' : 'blue';
}

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

  moveHandler: (e: GeoEvent) => void;
  mousedownHandler: (e: GeoEvent) => void;
  hoverHandler: (e: GeoEvent) => void;
  mouseupHandler: () => void;

  constructor(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void,
    spectroInfo: SpectroInfo,
    measuring?: boolean
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
    this.color = 'white';

    this.textStyle = this.createTextStyle();
    this.rulerOn = measuring || false;
    if (this.rulerOn) {
      this.enableDrawing();
    }

    this.moveHandler = (e: GeoEvent) => {
      if (e && this.dragging) {
        this.updateRuler(e.mouse.geo.y);
      } 
    };
    this.hoverHandler = (e: GeoEvent) => {
      if (e) {
       const gcs = this.geoViewerRef.displayToGcs(e.map);
        const p = this.pointAnnotation.data()[0];
        const dx = Math.abs(gcs.x - p.x);
        const dy = Math.abs(gcs.y - p.y);
        if (Math.sqrt(dx*dx + dy*dy) < 20 || dy < 10) {
          this.event('update:cursor', { cursor: 'grab' });
        } else {
          this.event('update:cursor', { cursor: 'default' });
        }
      }
    };
    this.mousedownHandler = (e: GeoEvent) => {
      const gcs = this.geoViewerRef.displayToGcs(e.map);
      const p = this.pointAnnotation.data()[0];
      const dx = Math.abs(gcs.x - p.x);
      const dy = Math.abs(gcs.y - p.y);
      if (Math.sqrt(dx*dx + dy*dy) < 20 || dy < 10) {
        this.geoViewerRef.interactor().addAction({
          action: 'dragpoint',
          name: 'drag point with mouse',
          owner: 'MeasureToolLayer',
          input: 'left',
        });
        this.dragging = true;
        this.event('update:cursor', { cursor: 'grabbing' });
      }
    };
    this.mouseupHandler = () => {
      this.dragging = false;
      this.geoViewerRef.interactor().removeAction(undefined, undefined, 'MeasureToolLayer');
      this.updateRuler(this.yValue);
      this.event('update:cursor', { cursor: 'grab' });
    };
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
    this.geoViewerRef.geoOn(geo.event.mousedown, this.mousedownHandler);
    this.geoViewerRef.geoOn(geo.event.actionmove, this.moveHandler);
    this.geoViewerRef.geoOn(geo.event.mouseup, this.mouseupHandler);
    this.geoViewerRef.geoOn(geo.event.mousemove, this.hoverHandler);
    this.frequencyRulerLayer.draw();
    this.updateRuler(this.yValue);
  }

  _getTextCoordinates(): { x: number, y: number } {
    const bounds = this.geoViewerRef.bounds();
    const startX = 0;
    const endX = ((this.compressedView
      ? this.scaledWidth
      : this.spectroInfo.width
    ) || this.spectroInfo.width);
    const left = Math.max(startX, bounds.left);
    const right = Math.min(endX, bounds.right);
    return { x: (left + right) / 2, y: this.yValue };
  }

  updateRuler(newY: number) {
    if (newY < 0) {
      return;
    }
    this.yValue = newY;
    const spectroWidth = this.compressedView ? this.scaledWidth : this.spectroInfo.width;
    this.lineAnnotation
      .data([[
        {x: 0, y: this.yValue},
        {x: (spectroWidth || this.spectroInfo.width), y: this.yValue},
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
    const { x: textX, y: textY } = this._getTextCoordinates();
    this.textData = [
      {
        text: textValue,
        x: textX,
        y: textY,
        offsetY: 20,
      },
    ];
    this.textLayer.data(this.textData).draw();
  }

  disableDrawing() {
    this.rulerOn = false;
    this.textData = [];
    this.textLayer.data(this.textData).draw();
    this.clearRulerLayer();
    this.geoViewerRef.geoOff(geo.event.mousedown, this.mousedownHandler);
    this.geoViewerRef.geoOff(geo.event.mouseup, this.mouseupHandler);
    this.geoViewerRef.geoOff(geo.event.actionmove, this.moveHandler);
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
      color: () => _determineRulerColor(this.dragging, this.color === 'white'),
      offset: (data: TextData) => ({
        x: data.offsetX || 0,
        y: data.offsetY || 0,
      }),
      textAlign: 'center',
      textScaled: this.textScaled,
      textBaseline: 'bottom',
    };
  }

  createPointStyle(): LayerStyle<LineData> {
    return {
      radius: 10,
      fillColor: () => _determineRulerColor(this.dragging, this.color === 'white'),
      strokeColor: () => _determineRulerColor(this.dragging, this.color === 'white'),
      stroke: true,
      strokeWidth: 5,
    };
  }

  createLineStyle(): LayerStyle<LineData> {
    return {
      strokeColor: () => _determineRulerColor(this.dragging, this.color === 'white'),
      strokeWidth: 2,
    };
  }

}
