import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { OhlcRow } from '../api/types'
import { rowsToSingleSeries } from '../utils/ohlcMerge'
import type { EChartsOption } from 'echarts'

interface OhlcCandlestickPreviewProps {
  rows: OhlcRow[]
  tail?: number
}

export default function OhlcCandlestickPreview({ rows, tail = 200 }: OhlcCandlestickPreviewProps) {
  const slice = useMemo(() => rows.slice(-tail), [rows, tail])
  const data = useMemo(() => rowsToSingleSeries(slice), [slice])

  const option = useMemo((): EChartsOption => {
    return {
      title: {
        text: `末尾 ${slice.length} 本のプレビュー`,
        left: 'center',
        textStyle: { fontSize: 13 },
      },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: '8%', right: '5%', top: 40, bottom: 48 },
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
  }, [data, slice.length])

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
