/**
 * tree-shaking 用に ECharts コンポーネントを明示登録する
 */
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DataZoomComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DataZoomComponent,
  LegendComponent,
  CandlestickChart,
  LineChart,
  CanvasRenderer,
])

export { echarts }
