import * as echarts from "echarts/core";
import { BarChart, LineChart, ScatterChart, HeatmapChart, GaugeChart } from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent,
  CalendarComponent,
  GraphicComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  HeatmapChart,
  GaugeChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent,
  CalendarComponent,
  GraphicComponent,
  SVGRenderer,
]);

export default echarts;
