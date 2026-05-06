import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { OhlcRow } from '../api/types'
import { rowsToSingleSeries } from '../utils/ohlcMerge'
import type { EChartsOption } from 'echarts'

interface OhlcCandlestickPreviewProps {
  rows: OhlcRow[]
  /** 指定時のみ末尾 `tail` 本に切り詰め。省略時は全行（dataZoom で範囲変更） */
  tail?: number
}

const ZOOM_TAIL_THRESHOLD = 500
const ZOOM_DEFAULT_START = 85
const ZOOM_DEFAULT_END = 100

export default function OhlcCandlestickPreview({ rows, tail }: OhlcCandlestickPreviewProps) {
  const slice = useMemo(
    () => (tail === undefined ? rows : rows.slice(-tail)),
    [rows, tail],
  )
  const data = useMemo(() => rowsToSingleSeries(slice), [slice])

  const option = useMemo((): EChartsOption => {
    const n = slice.length
    const zoomToEnd = n > ZOOM_TAIL_THRESHOLD
    const dzStart = zoomToEnd ? ZOOM_DEFAULT_START : 0
    const dzEnd = zoomToEnd ? ZOOM_DEFAULT_END : 100

    const titleText =
      tail === undefined
        ? `全 ${n} 本（下スライダー・ドラッグで範囲変更）`
        : `末尾 ${n} 本のプレビュー`

    return {
      title: {
        text: titleText,
        left: 'center',
        textStyle: { fontSize: 13 },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: '8%', right: '5%', top: 40, bottom: 64 },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0,
          start: dzStart,
          end: dzEnd,
        },
        {
          type: 'slider',
          xAxisIndex: 0,
          start: dzStart,
          end: dzEnd,
          bottom: 8,
          height: 22,
        },
      ],
      xAxis: {
        type: 'time',
      },
      yAxis: {
        type: 'value',
        scale: true,
      },
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
  }, [data, slice.length, tail])

  if (!data.length) {
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
