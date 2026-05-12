import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { OhlcRow } from '../api/types'
import { rowsToSingleSeries, pickOhlcOnly } from '../utils/ohlcMerge'
import type { CandleTuple } from '../utils/ohlcMerge'
import type { EChartsOption } from 'echarts'
import {
  type ChartTimeMode,
  buildContinuousAxisFromSortedMs,
  detectGaps,
  gapsToAfterIndexMap,
  inferIntervalMsFromSortedMs,
} from '../utils/ohlcGap'

export type { ChartTimeMode }

interface OhlcCandlestickPreviewProps {
  rows: OhlcRow[]
  /** 指定時のみ末尾 `tail` 本に切り詰め。省略時は全行（dataZoom で範囲変更） */
  tail?: number
  /** 既定: continuous */
  mode?: ChartTimeMode
  intervalMs?: number
  gapFactor?: number
}

const ZOOM_TAIL_THRESHOLD = 500
const ZOOM_DEFAULT_START = 85
const ZOOM_DEFAULT_END = 100

type CandleDataItem = [number, number, number, number] | '-'

function tuplesSortedMs(tuples: CandleTuple[]): number[] {
  return [...new Set(tuples.map((t) => t[0]))].sort((a, b) => a - b)
}

export default function OhlcCandlestickPreview({
  rows,
  tail,
  mode = 'continuous',
  intervalMs: intervalMsProp,
  gapFactor = 1.5,
}: OhlcCandlestickPreviewProps) {
  const slice = useMemo(
    () => (tail === undefined ? rows : rows.slice(-tail)),
    [rows, tail],
  )
  const tuples = useMemo(() => rowsToSingleSeries(slice), [slice])

  const option = useMemo((): EChartsOption => {
    const n = slice.length
    const zoomToEnd = n > ZOOM_TAIL_THRESHOLD
    const dzStart = zoomToEnd ? ZOOM_DEFAULT_START : 0
    const dzEnd = zoomToEnd ? ZOOM_DEFAULT_END : 100

    const titleText =
      tail === undefined
        ? `全 ${n} 本（下スライダー・ドラッグで範囲変更）`
        : `末尾 ${n} 本のプレビュー`

    if (mode === 'real') {
      const data = tuples
      return {
        title: {
          text: titleText,
          left: 'center',
          textStyle: { fontSize: 13 },
        },
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        grid: { left: '8%', right: '5%', top: 40, bottom: 64 },
        dataZoom: [
          { type: 'inside', xAxisIndex: 0, start: dzStart, end: dzEnd },
          { type: 'slider', xAxisIndex: 0, start: dzStart, end: dzEnd, bottom: 8, height: 22 },
        ],
        xAxis: { type: 'time' },
        yAxis: { type: 'value', scale: true },
        series: [
          {
            type: 'candlestick',
            data,
            itemStyle: {
              color: '#26A69A',
              color0: '#EF5350',
              borderColor: '#26A69A',
              borderColor0: '#EF5350',
            },
          },
        ],
      }
    }

    const categoriesMs = tuplesSortedMs(tuples)
    const resolvedInterval = intervalMsProp ?? inferIntervalMsFromSortedMs(categoriesMs)

    if (!resolvedInterval || !categoriesMs.length) {
      const data = tuples
      return {
        title: {
          text: titleText,
          left: 'center',
          textStyle: { fontSize: 13 },
        },
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        grid: { left: '8%', right: '5%', top: 40, bottom: 64 },
        dataZoom: [
          { type: 'inside', xAxisIndex: 0, start: dzStart, end: dzEnd },
          { type: 'slider', xAxisIndex: 0, start: dzStart, end: dzEnd, bottom: 8, height: 22 },
        ],
        xAxis: { type: 'time' },
        yAxis: { type: 'value', scale: true },
        series: [
          {
            type: 'candlestick',
            data,
            itemStyle: {
              color: '#26A69A',
              color0: '#EF5350',
              borderColor: '#26A69A',
              borderColor0: '#EF5350',
            },
          },
        ],
      }
    }

    const { categories } = buildContinuousAxisFromSortedMs(categoriesMs)
    const gaps = detectGaps(categoriesMs, resolvedInterval, gapFactor)
    const gapByAfterIndex = gapsToAfterIndexMap(gaps)

    const map = new Map<number, CandleTuple>()
    for (const t of tuples) map.set(t[0], t)

    const data: CandleDataItem[] = categoriesMs.map((ms) => {
      const c = map.get(ms)
      return c ? pickOhlcOnly(c) : '-'
    })

    return {
      title: {
        text: titleText,
        left: 'center',
        textStyle: { fontSize: 13 },
      },
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
          const d = (first as { data?: CandleDataItem }).data
          if (d && d !== '-' && Array.isArray(d) && d.length >= 4) {
            const [o, c, l, h] = d
            lines.push(
              `O ${Number(o).toFixed(4)} H ${Number(h).toFixed(4)} L ${Number(l).toFixed(4)} C ${Number(c).toFixed(4)}`,
            )
          }
          if (gap) {
            lines.push('省略表示: 直前にギャップあり')
            lines.push(`欠け本数（推定）: 約 ${gap.missingCount} 本`)
          }
          return lines.join('<br/>')
        },
      },
      grid: { left: '8%', right: '5%', top: 40, bottom: 64 },
      dataZoom: [
        { type: 'inside', xAxisIndex: 0, start: dzStart, end: dzEnd },
        { type: 'slider', xAxisIndex: 0, start: dzStart, end: dzEnd, bottom: 8, height: 22 },
      ],
      xAxis: {
        type: 'category',
        data: categories,
        boundaryGap: true,
        axisLabel: { interval: 'auto', hideOverlap: true },
      },
      yAxis: { type: 'value', scale: true },
      series: [
        {
          type: 'candlestick',
          data: data as any,
          itemStyle: {
            color: '#26A69A',
            color0: '#EF5350',
            borderColor: '#26A69A',
            borderColor0: '#EF5350',
          },
        },
      ],
    }
  }, [tuples, slice.length, tail, mode, intervalMsProp, gapFactor])

  if (!tuples.length) {
    return <p className="msg-muted">ローソク表示に十分なデータがありません。</p>
  }

  return (
    <div style={{ width: '100%', height: 320 }}>
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