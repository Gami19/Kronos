import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import { echarts } from '../echarts/registerEcharts'
import type { EChartsOption } from 'echarts'

export interface BacktestEquityChartProps {
  timestamps: string[]
  strategyEquity: number[]
  bhEquity: number[]
  height?: number
  className?: string
}

export default function BacktestEquityChart({
  timestamps,
  strategyEquity,
  bhEquity,
  height = 320,
  className,
}: BacktestEquityChartProps) {
  const option = useMemo((): EChartsOption => {
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['戦略', 'B&H'] },
      grid: { left: 48, right: 24, top: 40, bottom: 64 },
      xAxis: {
        type: 'category',
        data: timestamps,
        axisLabel: { rotate: 35, fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: '累積倍率',
        scale: true,
      },
      dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 8 }],
      series: [
        {
          name: '戦略',
          type: 'line',
          data: strategyEquity,
          smooth: false,
          showSymbol: false,
          lineStyle: { width: 2, color: '#2563eb' },
        },
        {
          name: 'B&H',
          type: 'line',
          data: bhEquity,
          smooth: false,
          showSymbol: false,
          lineStyle: { width: 2, color: '#94a3b8' },
        },
      ],
    }
  }, [timestamps, strategyEquity, bhEquity])

  if (!timestamps.length) {
    return null
  }

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height, width: '100%' }}
      className={className}
    />
  )
}
