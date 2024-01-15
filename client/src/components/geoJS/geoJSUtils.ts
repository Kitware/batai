
import { ref, Ref } from "vue";
import geo from "geojs";

const useGeoJS = () => {

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const geoViewer: Ref<any> = ref();
    const container: Ref<HTMLElement| undefined> = ref();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let quadFeature: any;
    let originalBounds = {
        left: 0,
        top: 0,
        bottom: 1,
        right: 1,
    };

    const getGeoViewer = () => {
        return geoViewer;
    };

    const initializeViewer = (sourceContainer: HTMLElement, width: number, height: number) => {
        container.value = sourceContainer;
        const params = geo.util.pixelCoordinateParams(
        container.value,
        width,
        height
        );
        if (!container.value) {
            return;
        }
        geoViewer.value = geo.map(params.map);
        resetMapDimensions(width, height);
        const interactorOpts = geoViewer.value.interactor().options();
        interactorOpts.keyboard.focusHighlight = false;
        interactorOpts.keyboard.actions = {};
        interactorOpts.click.cancelOnMove = 5;

        interactorOpts.actions = [
        interactorOpts.actions[0],
        // The action below is needed to have GeoJS use the proper handler
        // with cancelOnMove for right clicks
        {
            action: geo.geo_action.select,
            input: { right: true },
            name: "button edit",
            owner: "geo.MapInteractor",
        },
        // The action below adds middle mouse button click to panning
        // It allows for panning while in the process of polygon editing or creation
        {
            action: geo.geo_action.pan,
            input: "middle",
            modifiers: { shift: false, ctrl: false },
            owner: "geo.mapInteractor",
            name: "button pan",
        },
        interactorOpts.actions[2],
        interactorOpts.actions[6],
        interactorOpts.actions[7],
        interactorOpts.actions[8],
        interactorOpts.actions[9],
        ];
        // Set > 2pi to disable rotation
        interactorOpts.zoomrotateMinimumRotation = 7;
        interactorOpts.zoomAnimation = {
        enabled: false,
        };
        interactorOpts.momentum = {
        enabled: false,
        };
        interactorOpts.wheelScaleY = 0.2;
        geoViewer.value.interactor().options(interactorOpts);
        geoViewer.value.bounds({
            left: 0,
            top: 0,
            bottom: height,
            right: width,
        });

        const quadFeatureLayer = geoViewer.value.createLayer("feature", {
        features: ["quad"],
        autoshareRenderer: false,
        renderer: "canvas",
        });
        quadFeature = quadFeatureLayer.createFeature("quad");
    };

    const drawImage =  (image: HTMLImageElement, width = image.width, height = image.height) => {
        if (quadFeature) {
            quadFeature
                .data([
                {
                    ul: { x: 0, y: 0 },
                    lr: { x: width, y: height },
                    image: image,
                },
                ])
                .draw();
        }
        resetMapDimensions(width, height);
    };
    const resetZoom = () => {
        const zoomAndCenter = geoViewer.value.zoomAndCenterFromBounds(
          originalBounds, 0,
        );
        geoViewer.value.zoom(zoomAndCenter.zoom);
        geoViewer.value.center(zoomAndCenter.center);
    };
  
    const resetMapDimensions = ( width: number, height: number, margin = 0.3) => {
        geoViewer.value.bounds({
            left: 0,
            top: 0,
            bottom: height,
            right: width,
          });
          const params = geo.util.pixelCoordinateParams(
            container.value, width, height, width, height,
          );
          const { right, bottom } = params.map.maxBounds;
          originalBounds = params.map.maxBounds;
          geoViewer.value.maxBounds({
            left: 0 - (right * margin),
            top: 0 - (bottom * margin),
            right: right * (1 + margin),
            bottom: bottom * (1 + margin),
          });
          geoViewer.value.zoomRange({
            // do not set a min limit so that bounds clamping determines min
              min: -Infinity,
              // 4x zoom max
              max: 4,
            });
            geoViewer.value.clampBoundsX(true);
            geoViewer.value.clampBoundsY(true);
            geoViewer.value.clampZoom(true);
    
          resetZoom();    
    };

    return {
        getGeoViewer,
        initializeViewer,
        drawImage,
        resetMapDimensions,
        resetZoom
    };
};

import { SpectrogramAnnotation } from "../../api/api";

export interface SpectroInfo {
    width: number;
    height: number;
    start_time: number;
    end_time: number;
    low_freq: number;
    high_freq: number;
}
function spectroToGeoJSon(annotation: SpectrogramAnnotation, spectroInfo: SpectroInfo): GeoJSON.Polygon  {
    //scale pixels to time and frequency ranges
    const widthScale =   spectroInfo.width / (spectroInfo.end_time - spectroInfo.start_time);
    const heightScale = spectroInfo.height / (spectroInfo.high_freq - spectroInfo.low_freq);
    // Now we remap our annotation to pixel coordinates
    const low_freq = spectroInfo.height - (annotation.low_freq * heightScale);
    const high_freq = spectroInfo.height - (annotation.high_freq * heightScale);
    const start_time = annotation.start_time * widthScale;
    const end_time = annotation.end_time * widthScale;
    return {
        type: 'Polygon',
        coordinates: [  
            [
              [start_time, low_freq],
              [start_time, high_freq],
              [end_time, high_freq],
              [end_time, low_freq],
              [start_time, low_freq],
            ],
          ],
      
    };
}

/* beginning at bottom left, rectangle is defined clockwise */
function geojsonToSpectro(geojson: GeoJSON.Feature<GeoJSON.Polygon>, spectroInfo: SpectroInfo): { start_time: number, end_time: number, low_freq: number, high_freq: number} {
  const coords = geojson.geometry.coordinates[0];
  const widthScale =  spectroInfo.width / (spectroInfo.end_time - spectroInfo.start_time);
  const heightScale = spectroInfo.height / (spectroInfo.high_freq - spectroInfo.low_freq);
  const start_time = coords[1][0] / widthScale;
  const end_time = coords[3][0] / widthScale;
  const low_freq = spectroInfo.high_freq - (coords[1][1]) / heightScale;
  const high_freq = spectroInfo.high_freq - (coords[3][1]) / heightScale;
  return {
    start_time,
    end_time,
    low_freq,
    high_freq
  };
}


/**
 * This will take the current geoJSON Coordinates for a rectangle and reorder it
 * to keep the vertices index the same with respect to how geoJS uses it
 * Example: UL, LL, LR, UR, UL
 */
function reOrdergeoJSON(coords: GeoJSON.Position[]) {
  let x1 = Infinity;
  let x2 = -Infinity;
  let y1 = Infinity;
  let y2 = -Infinity;
  coords.forEach((coord) => {
    x1 = Math.min(x1, coord[0]);
    x2 = Math.max(x2, coord[0]);
    y1 = Math.min(y1, coord[1]);
    y2 = Math.max(y2, coord[1]);
  });
  return [
    [x1, y2],
    [x1, y1],
    [x2, y1],
    [x2, y2],
    [x1, y2],
  ];
}


export {
  spectroToGeoJSon,
  geojsonToSpectro,
  reOrdergeoJSON,
  useGeoJS,
};
