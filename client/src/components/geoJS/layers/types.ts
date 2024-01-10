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
