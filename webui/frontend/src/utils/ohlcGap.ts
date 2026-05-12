/**
 * 連続表示（category 軸）用のバー間隔推定・ギャップ検出。
 * docs/update.md フェーズ3に準拠。
 */

import type { OhlcRow } from '../api/types'
import type { CandleTuple } from './ohlcMerge'

export type ChartTimeMode = 'continuous' | 'real'

/** ギャップの直後に来るカテゴリ行インデックス（ツールチップはこの行で欠け情報を出す） */
export type GapEntry = { afterIndex: number; missingCount: number }

/** ソート済みユニークな epoch ms 列から、隣接差分の中央値でバー間隔を推定 */
export function inferIntervalMsFromSortedMs(sortedMs: number[]): number | null {
  if (sortedMs.length < 2) return null
  const diffs: number[] = []
  for (let i = 1; i < sortedMs.length; i++) {
    diffs.push(sortedMs[i]! - sortedMs[i - 1]!)
  }
  diffs.sort((a, b) => a - b)
  const mid = Math.floor(diffs.length / 2)
  return diffs.length % 2 === 1 ? diffs[mid]! : Math.round((diffs[mid - 1]! + diffs[mid]!) / 2)
}

export function inferIntervalMsFromOhlcRows(rows: OhlcRow[]): number | null {
  const ms = rows
    .map((r) => (r.timestamp ? Date.parse(r.timestamp) : Number.NaN))
    .filter((x) => !Number.isNaN(x))
  const uniq = [...new Set(ms)].sort((a, b) => a - b)
  return inferIntervalMsFromSortedMs(uniq)
}

export function inferIntervalMsFromCandles(candles: CandleTuple[]): number | null {
  const uniq = [...new Set(candles.map((c) => c[0]))].sort((a, b) => a - b)
  return inferIntervalMsFromSortedMs(uniq)
}

/**
 * 隣接バー間隔が intervalMs * gapFactor を超えたらギャップ。
 * 欠け本数（推定）= max(1, round(Δt / intervalMs) - 1)
 */
export function detectGaps(sortedMs: number[], intervalMs: number, gapFactor = 1.5): GapEntry[] {
  if (sortedMs.length < 2 || intervalMs <= 0 || !Number.isFinite(intervalMs)) return []
  const thr = intervalMs * gapFactor
  const out: GapEntry[] = []
  for (let i = 1; i < sortedMs.length; i++) {
    const dt = sortedMs[i]! - sortedMs[i - 1]!
    if (dt > thr) {
      const missingCount = Math.max(1, Math.round(dt / intervalMs) - 1)
      out.push({ afterIndex: i, missingCount })
    }
  }
  return out
}

export function gapsToAfterIndexMap(gaps: GapEntry[]): Map<number, GapEntry> {
  return new Map(gaps.map((g) => [g.afterIndex, g]))
}

export function sortedUnionMsFromCandles(...groups: CandleTuple[][]): number[] {
  const s = new Set<number>()
  for (const g of groups) {
    for (const t of g) s.add(t[0])
  }
  return [...s].sort((a, b) => a - b)
}

export function buildContinuousAxisFromSortedMs(sortedMs: number[]): {
  categories: string[]
  indexByMs: Map<number, number>
} {
  const categories = sortedMs.map((ms) => new Date(ms).toISOString())
  const indexByMs = new Map<number, number>()
  sortedMs.forEach((ms, i) => indexByMs.set(ms, i))
  return { categories, indexByMs }
}

/** OHLC 行から連続軸用のカテゴリと ms インデックスを構築 */
export function buildContinuousAxis(rows: OhlcRow[]): {
  categoriesMs: number[]
  categories: string[]
  indexByMs: Map<number, number>
} {
  const ms = rows
    .map((r) => (r.timestamp ? Date.parse(r.timestamp) : Number.NaN))
    .filter((x) => !Number.isNaN(x))
  const categoriesMs = [...new Set(ms)].sort((a, b) => a - b)
  const { categories, indexByMs } = buildContinuousAxisFromSortedMs(categoriesMs)
  return { categoriesMs, categories, indexByMs }
}
