/* eslint-disable class-methods-use-this */
import geo, { GeoEvent } from 'geojs';
import { SpectroInfo, spectroToGeoJSon } from '../geoJSUtils';
import { SpectrogramAnnotation } from '../../../api/api';

interface RectGeoJSData{
  id: number;
  selected: boolean;
  editing: boolean | string;
  polygon: GeoJSON.Polygon;
}

// eslint-disable-next-line max-len
export type StyleFunction<T, D> = T | ((point: [number, number], index: number, data: D) => T | undefined);
export type ObjectFunction<T, D> = T | ((data: D, index: number) => T | undefined);
export type PointFunction<T, D> = T | ((data: D) => T | undefined);

export interface LayerStyle<D> {
    strokeWidth?: StyleFunction<number, D> | PointFunction<number, D>;
    strokeOffset?: StyleFunction<number, D> | PointFunction<string, D>;
    strokeOpacity?: StyleFunction<number, D> | PointFunction<string, D>;
    strokeColor?: StyleFunction<string, D> | PointFunction<string, D>;
    fillColor?: StyleFunction<string, D> | PointFunction<string, D>;
    fillOpacity?: StyleFunction<number, D> | PointFunction<number, D>;
    position?: (point: [number, number]) => { x: number; y: number };
    color?: (data: D) => string;
    textOpacity?: (data: D) => number;
    fontSize?: (data: D) => string | undefined;
    offset?: (data: D) => { x: number; y: number };
    fill?: ObjectFunction<boolean, D> | boolean;
    radius?: PointFunction<number, D> | number;
    textAlign?: ((data: D) => string) | string;
    textScaled?: ((data: D) => number | undefined) | number | undefined;
    [x: string]: unknown;
  }
  

export default class RectangleLayer{
    formattedData: RectGeoJSData[];

    drawingOther: boolean; //drawing another type of annotation at the same time?

    hoverOn: boolean; //to turn over annnotations on
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    featureLayer: any;

    selectedIndex: number[]; // sparse array

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    geoViewerRef: any;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    event: (name: string, data: any) => void;

    spectroInfo: SpectroInfo;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    constructor(geoViewerRef: any, event: (name: string, data: any) => void, spectroInfo: SpectroInfo) {
    this.geoViewerRef = geoViewerRef;
      this.drawingOther = false;
      this.spectroInfo = spectroInfo;
      this.formattedData = [];
      this.hoverOn = false;
      this.selectedIndex = [];
      this.event = event;
      //Only initialize once, prevents recreating Layer each edit
      this.initialize();
    }

    initialize() {
      const layer = this.geoViewerRef.value.createLayer('feature', {
        features: ['polygon'],
      });
      this.featureLayer = layer
        .createFeature('polygon', { selectionAPI: true })
        .geoOn(geo.event.feature.mouseclick, (e: GeoEvent) => {
        /**
         * Handle clicking on individual annotations, if DrawingOther is true we use the
         * Rectangle type if only the polygon is visible we use the polygon bounds
         * */
          if (e.mouse.buttonsDown.left) {
            if (!e.data.editing || (e.data.editing && !e.data.selected)) {
              this.event('annotation-clicked', { id: e.data.id, edit: false });
            }
          } else if (e.mouse.buttonsDown.right) {
            if (!e.data.editing || (e.data.editing && !e.data.selected)) {
              this.event('annotation-right-clicked', { id: e.data.id, edit: true });
            }
          }
        });
      this.featureLayer.geoOn(
        geo.event.feature.mouseclick_order,
        this.featureLayer.mouseOverOrderClosestBorder,
      );
      this.featureLayer.geoOn(geo.event.mouseclick, (e: GeoEvent) => {
        // If we aren't clicking on an annotation we can deselect the current track
        if (this.featureLayer.pointSearch(e.geo).found.length === 0) {
            this.event('annotation-clicked', { id: null, edit: false });
        }
      });
    }

    hoverAnnotations(e: GeoEvent) {
      const { found } = this.featureLayer.pointSearch(e.mouse.geo);
      this.event('annotation-hover', {id: found, pos: e.mouse.geo});
    }

    setHoverAnnotations(val: boolean) {
      if (!this.hoverOn && val) {
        this.featureLayer.geoOn(
          geo.event.feature.mouseover,
          (e: GeoEvent) => this.hoverAnnotations(e),
        );
        this.featureLayer.geoOn(
          geo.event.feature.mouseoff,
          (e: GeoEvent) => this.hoverAnnotations(e),
        );
        this.hoverOn = true;
      } else if (this.hoverOn && !val) {
        this.featureLayer.geoOff(geo.event.feature.mouseover);
        this.featureLayer.geoOff(geo.event.feature.mouseoff);
        this.hoverOn = false;
      }
    }

    /**
   * Used to set the drawingOther parameter used to change styling if other types are drawn
   * and also handle selection clicking between different types
   * @param val - determines if we are drawing other types of annotations
   */
    setDrawingOther(val: boolean) {
      this.drawingOther = val;
    }


    formatData(annotationData: SpectrogramAnnotation[]) {
      const arr: RectGeoJSData[] = [];
      annotationData.forEach((annotation: SpectrogramAnnotation, ) => {
        const polygon = spectroToGeoJSon(annotation, this.spectroInfo);
        const newAnnotation: RectGeoJSData = {
            id: annotation.id,
            selected: false,
            editing: false,
            polygon,
          };
        arr.push(newAnnotation);

      });
      return arr;
    }

    redraw() {
      this.featureLayer
        .data(this.formattedData)
        .polygon((d: RectGeoJSData) => d.polygon.coordinates[0])
        .draw();
    }

    disable() {
      this.featureLayer
        .data([])
        .draw();
    }

    createStyle(): LayerStyle<RectGeoJSData> {
      return {
        // Style conversion to get array objects to work in geoJS
        position: (point) => ({ x: point[0], y: point[1] }),
        strokeColor: (_point, _index, data) => {
          if (data.selected) {
            return 'cyan';
          }
          return 'red';
        },
      };
    }
}
