
import { defineComponent, PropType, ref, Ref, watch } from "vue";
import geo, { GeoEvent } from "geojs";

const useGeoJS = () => {

    const geoViewer: Ref<any> = ref();
    const container: Ref<HTMLElement| undefined> = ref();
    let quadFeature: any;
    let originalBounds = {
        left: 0,
        top: 0,
        bottom: 1,
        right: 1,
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
        initializeViewer,
        drawImage,
        resetMapDimensions,
        resetZoom
    };
};

export {
    useGeoJS,
};