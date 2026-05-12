/**
 * フェーズ4: バー番号ベースのデモ指標（実測がある区間のみ、timestamp 一致は不要）
 */

import type { OhlcRow } from '../api/types'

export type DirSign = -1 | 0 | 1

export interface PerBarErr {
  index: number
  predClose: number
  actClose: number
  absError: number
  predDir?: DirSign
  actDir?: DirSign
  /** i>=1 かつ両者の騰落が非ゼロのときのみ */
  dirMatch?: boolean
}

export interface AccuracyMetricsResult {
  count: number
  /** 0..1。隣接騰落が両方非ゼロのペアのみを母数 */
  directionAccuracy: number
  closeMae: number
  maxError: number
  perBar: PerBarErr[]
}

function dirFromDelta(d: number): DirSign {
  if (d > 0) return 1
  if (d < 0) return -1
  return 0
}

export function computeAccuracyMetrics(
  predictions: OhlcRow[] | undefined | null,
  actuals: OhlcRow[] | undefined | null,
): AccuracyMetricsResult {
  const p = predictions ?? []
  const a = actuals ?? []
  const n = Math.min(p.length, a.length)
  if (n === 0) {
    return { count: 0, directionAccuracy: 0, closeMae: 0, maxError: 0, perBar: [] }
  }

  let absSum = 0
  let maxAbs = 0
  let dirOk = 0
  let dirTot = 0
  const perBar: PerBarErr[] = []

  for (let i = 0; i < n; i++) {
    const pr = p[i]!
    const ac = a[i]!
    const pc = pr.close
    const acClose = ac.close
    const e = Math.abs(pc - acClose)
    absSum += e
    if (e > maxAbs) maxAbs = e

    let predDir: DirSign | undefined
    let actDir: DirSign | undefined
    let dirMatch: boolean | undefined

    if (i >= 1) {
      const dp = pc - p[i - 1]!.close
      const da = acClose - a[i - 1]!.close
      predDir = dirFromDelta(dp)
      actDir = dirFromDelta(da)
      if (predDir !== 0 && actDir !== 0) {
        dirTot += 1
        const match = predDir === actDir
        if (match) dirOk += 1
        dirMatch = match
      }
    }

    perBar.push({
      index: i,
      predClose: pc,
      actClose: acClose,
      absError: e,
      predDir,
      actDir,
      dirMatch,
    })
  }

  return {
    count: n,
    directionAccuracy: dirTot > 0 ? dirOk / dirTot : 0,
    closeMae: absSum / n,
    maxError: maxAbs,
    perBar,
  }
}

export function dirSignToArrow(s: DirSign | undefined): string {
  if (s === 1) return '↑'
  if (s === -1) return '↓'
  return '→'
}
