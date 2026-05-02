import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { CandleTuple } from '../utils/ohlcMerge'
import type { EChartsOption } from 'echarts'

export interface EChartsCandlestickProps {
  history: CandleTuple[]
  prediction: CandleTuple[]
  actual: CandleTuple[]
  title?: string
  subtitle?: string
  height?: number
  showDataZoom?: boolean
  className?: string
}

function buildOption(
  history: CandleTuple[],
  prediction: CandleTuple[],
  actual: CandleTuple[],
  title: string | undefined,
  subtitle: string | undefined,
  showDataZoom: boolean,
): EChartsOption {
  const series: EChartsOption['series'] = []

  if (history.length) {
    series.push({
      name: '履歴',
      type: 'candlestick',
      data: history,
      barMaxWidth: 10,
      itemStyle: {
        color: '#9ca3af',
        color0: '#6b7280',
        borderColor: '#9ca3af',
        borderColor0: '#6b7280',
      },
    })
  }

  if (prediction.length) {
    series.push({
      name: '予測',
      type: 'candlestick',
      data: prediction,
      barMaxWidth: 10,
      itemStyle: {
        color: '#22c55e',
        color0: '#ef4444',
        borderColor: '#16a34a',
        borderColor0: '#dc2626',
      },
    })
  }

  if (actual.length) {
    series.push({
      name: '実測',
      type: 'candlestick',
      data: actual,
      barMaxWidth: 10,
      itemStyle: {
        color: '#f97316',
        color0: '#ea580c',
        borderColor: '#fb923c',
        borderColor0: '#c2410c',
      },
    })
  }

  const legendData = series.map((s) => (s as { name?: string }).name).filter(Boolean) as string[]

  const bottomMargin = showDataZoom ? '18%' : '12%'

  return {
    title: title
      ? {
          text: title,
          subtext: subtitle,
          left: 'center',
          textStyle: { fontSize: 14 },
          subtextStyle: { fontSize: 11, color: '#71717a' },
        }
      : undefined,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: legendData,
      top: title ? 48 : 8,
    },
    grid: {
      left: '4%',
      right: '3%',
      top: title ? 88 : 40,
      bottom: bottomMargin,
    },
    xAxis: {
      type: 'time',
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitArea: { show: true },
    },
    dataZoom: showDataZoom
      ? [
          { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
          { type: 'slider', xAxisIndex: 0, filterMode: 'none', height: 22, bottom: 8 },
        ]
      : [],
    series,
  }
}

export default function EChartsCandlestick({
  history,
  prediction,
  actual,
  title,
  subtitle,
  height = 480,
  showDataZoom = true,
  className,
}: EChartsCandlestickProps) {
  const option = useMemo(
    () => buildOption(history, prediction, actual, title, subtitle, showDataZoom),
    [history, prediction, actual, title, subtitle, showDataZoom],
  )

  const hasData = history.length + prediction.length + actual.length > 0

  if (!hasData) {
    return <p className="msg-muted">チャート用のデータがありません。</p>
  }

  return (
    <div className={className} style={{ width: '100%', height }}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        style={{ width: '100%', height: '100%' }}
        notMerge
        lazyUpdate
      />
    </div>
  )
}
