declare module "echarts-gl/charts" {
  export const SurfaceChart: Parameters<typeof import("echarts/core").use>[0];
  export const Scatter3DChart: Parameters<typeof import("echarts/core").use>[0];
}
declare module "echarts-gl/components" {
  export const Grid3DComponent: Parameters<
    typeof import("echarts/core").use
  >[0];
}
