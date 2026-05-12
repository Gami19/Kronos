import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { CandleTuple } from '../utils/ohlcMerge'
import { pickOhlcOnly } from '../utils/ohlcMerge'
import {
  type ChartTimeMode,
  buildContinuousAxisFromSortedMs,
  detectGaps,
  gapsToAfterIndexMap,
  inferIntervalMsFromSortedMs,
  sortedUnionMsFromCandles,
} from '../utils/ohlcGap'
import type { EChartsOption, SeriesOption } from 'echarts'

export type { ChartTimeMode }

const BAR_MAX_WIDTH = 6

export interface EChartsCandlestickProps {
  history: CandleTuple[]
  prediction: CandleTuple[]
  actual: CandleTuple[]
  title?: string
  subtitle?: string
  height?: number
  showDataZoom?: boolean
  className?: string
  /** 既定: continuous（フェーズ3） */
  mode?: ChartTimeMode
  /** 指定時はバー間隔として優先（例: 5m 履歴なら 5*60*1000） */
  intervalMs?: number
  /** ギャップ判定の係数（既定 1.5） */
  gapFactor?: number
}

type CandleDataItem = [number, number, number, number] | '-'

function alignCandlesToCategories(candles: CandleTuple[], categoriesMs: number[]): CandleDataItem[] {
  const m = new Map<number, CandleTuple>()
  for (const c of candles) m.set(c[0], c)
  return categoriesMs.map((ms) => {
    const c = m.get(ms)
    return c ? pickOhlcOnly(c) : '-'
  })
}

function buildRealTimeOption(
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
      barMaxWidth: BAR_MAX_WIDTH,
      z: 1,
      itemStyle: {
        color: '#9ca3af',
        color0: '#6b7280',
        borderColor: '#9ca3af',
        borderColor0: '#6b7280',
        opacity: 0.35,
      },
    })
  }

  if (prediction.length) {
    series.push({
      name: '予測',
      type: 'candlestick',
      data: prediction,
      barMaxWidth: BAR_MAX_WIDTH,
      z: 2,
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
      barMaxWidth: BAR_MAX_WIDTH,
      z: 3,
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
      min: 'dataMin',
      max: 'dataMax',
      splitArea: { show: true },
    },
    dataZoom: showDataZoom
      ? [
          { type: 'inside', xAxisIndex: 0, filterMode: 'filter' },
          { type: 'slider', xAxisIndex: 0, filterMode: 'filter', height: 22, bottom: 8 },
        ]
      : [],
    series,
  }
}

function buildContinuousOption(
  history: CandleTuple[],
  prediction: CandleTuple[],
  actual: CandleTuple[],
  title: string | undefined,
  subtitle: string | undefined,
  showDataZoom: boolean,
  intervalMsProp: number | undefined,
  gapFactor: number,
): EChartsOption {
  const categoriesMs = sortedUnionMsFromCandles(history, prediction, actual)
  const resolvedInterval = intervalMsProp ?? inferIntervalMsFromSortedMs(categoriesMs)

  if (!resolvedInterval || categoriesMs.length === 0) {
    return buildRealTimeOption(history, prediction, actual, title, subtitle, showDataZoom)
  }

  const { categories } = buildContinuousAxisFromSortedMs(categoriesMs)
  const gaps = detectGaps(categoriesMs, resolvedInterval, gapFactor)
  const gapByAfterIndex = gapsToAfterIndexMap(gaps)

  const series: SeriesOption[] = []

  const pushSeries = (
    name: string,
    candles: CandleTuple[],
    style: object,
    extra?: { opacity?: number },
  ) => {
    if (!candles.length) return
    series.push({
      name,
      type: 'candlestick',
      // ECharts は欠損に '-' を許容するが型定義が厳しい
      data: alignCandlesToCategories(candles, categoriesMs) as any,
      barMaxWidth: BAR_MAX_WIDTH,
      z: name === '履歴' ? 1 : name === '予測' ? 2 : 3,
      itemStyle: { ...(style as object), ...(extra?.opacity != null ? { opacity: extra.opacity } : {}) },
    } as SeriesOption)
  }

  pushSeries(
    '履歴',
    history,
    {
    color: '#9ca3af',
    color0: '#6b7280',
    borderColor: '#9ca3af',
    borderColor0: '#6b7280',
    },
    { opacity: 0.35 },
  )
  pushSeries('予測', prediction, {
    color: '#22c55e',
    color0: '#ef4444',
    borderColor: '#16a34a',
    borderColor0: '#dc2626',
  })
  pushSeries('実測', actual, {
    color: '#f97316',
    color0: '#ea580c',
    borderColor: '#fb923c',
    borderColor0: '#c2410c',
  })

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
      formatter: (params: unknown) => {
        const arr = Array.isArray(params) ? params : params != null ? [params] : []
        const first = arr[0] as { dataIndex?: number } | undefined
        const idx = first?.dataIndex
        if (idx === undefined || typeof idx !== 'number') return ''

        const gap = gapByAfterIndex.get(idx)
        const ts = categories[idx] ?? ''
        const lines: string[] = [`${ts}（バー #${idx}）`]

        for (const p of arr) {
          const px = p as {
            seriesName?: string
            data?: CandleDataItem
          }
          const d = px.data
          if (d && d !== '-' && Array.isArray(d) && d.length >= 4) {
            const [o, c, l, h] = d
            lines.push(
              `${px.seriesName ?? ''}: O ${Number(o).toFixed(4)} H ${Number(h).toFixed(4)} L ${Number(l).toFixed(4)} C ${Number(c).toFixed(4)}`,
            )
          }
        }

        if (gap) {
          lines.push('省略表示: 直前にギャップあり')
          lines.push(`欠け本数（推定）: 約 ${gap.missingCount} 本`)
        }
        return lines.join('<br/>')
      },
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
      type: 'category',
      data: categories,
      boundaryGap: true,
      axisLabel: { interval: 'auto', hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      min: 'dataMin',
      max: 'dataMax',
      splitArea: { show: true },
    },
    dataZoom: showDataZoom
      ? [
          { type: 'inside', xAxisIndex: 0, filterMode: 'filter' },
          { type: 'slider', xAxisIndex: 0, filterMode: 'filter', height: 22, bottom: 8 },
        ]
      : [],
    series,
  }
}

function buildOption(
  history: CandleTuple[],
  prediction: CandleTuple[],
  actual: CandleTuple[],
  title: string | undefined,
  subtitle: string | undefined,
  showDataZoom: boolean,
  mode: ChartTimeMode,
  intervalMs: number | undefined,
  gapFactor: number,
): EChartsOption {
  if (mode === 'real') {
    return buildRealTimeOption(history, prediction, actual, title, subtitle, showDataZoom)
  }
  return buildContinuousOption(
    history,
    prediction,
    actual,
    title,
    subtitle,
    showDataZoom,
    intervalMs,
    gapFactor,
  )
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
  mode = 'continuous',
  intervalMs,
  gapFactor = 1.5,
}: EChartsCandlestickProps) {
  const option = useMemo(
    () => buildOption(history, prediction, actual, title, subtitle, showDataZoom, mode, intervalMs, gapFactor),
    [history, prediction, actual, title, subtitle, showDataZoom, mode, intervalMs, gapFactor],
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
