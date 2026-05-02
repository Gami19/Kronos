import type { OhlcRow } from '../api/types'

/** [timeMs, open, close, low, high] — ECharts candlestick（time 軸）用 */
export type CandleTuple = [number, number, number, number, number]

export function rowToTuple(row: OhlcRow): CandleTuple | null {
  if (!row.timestamp) return null
  const t = Date.parse(row.timestamp)
  if (Number.isNaN(t)) return null
  return [t, row.open, row.close, row.low, row.high]
}

/**
 * 予測・実測の時刻では履歴バーを表示しない（実測＞予測で重なる時は両方残し描画順で上に実測）
 */
export function mergeOhlcSeries(
  history: OhlcRow[],
  prediction: OhlcRow[],
  actual: OhlcRow[],
): {
  history: CandleTuple[]
  prediction: CandleTuple[]
  actual: CandleTuple[]
} {
  const predTuples = prediction.map(rowToTuple).filter((x): x is CandleTuple => x !== null)
  const actualTuples = actual.map(rowToTuple).filter((x): x is CandleTuple => x !== null)

  const excludeFromHistory = new Set<number>()
  predTuples.forEach(([ms]) => excludeFromHistory.add(ms))
  actualTuples.forEach(([ms]) => excludeFromHistory.add(ms))

  const historyTuples = history
    .map(rowToTuple)
    .filter((x): x is CandleTuple => x !== null)
    .filter(([ms]) => !excludeFromHistory.has(ms))

  const sortByTime = (a: CandleTuple, b: CandleTuple) => a[0] - b[0]

  return {
    history: historyTuples.sort(sortByTime),
    prediction: predTuples.sort(sortByTime),
    actual: actualTuples.sort(sortByTime),
  }
}

export function rowsToSingleSeries(rows: OhlcRow[]): CandleTuple[] {
  return rows
    .map(rowToTuple)
    .filter((x): x is CandleTuple => x !== null)
    .sort((a, b) => a[0] - b[0])
}
