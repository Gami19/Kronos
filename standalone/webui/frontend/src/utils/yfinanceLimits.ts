/** yfinance 日付レンジ制限（バックエンド yfinance_limits と同値） */

const INTRADAY_RULES: Record<string, { maxLookbackDays: number; maxRangeDays: number }> = {
  '1m': { maxLookbackDays: 30, maxRangeDays: 7 },
  '2m': { maxLookbackDays: 60, maxRangeDays: 60 },
  '5m': { maxLookbackDays: 60, maxRangeDays: 60 },
  '15m': { maxLookbackDays: 60, maxRangeDays: 60 },
  '30m': { maxLookbackDays: 60, maxRangeDays: 60 },
  '90m': { maxLookbackDays: 60, maxRangeDays: 60 },
  '60m': { maxLookbackDays: 730, maxRangeDays: 730 },
  '1h': { maxLookbackDays: 730, maxRangeDays: 730 },
}

const UNLIMITED_INTERVALS = new Set(['1d', '5d', '1wk', '1mo', '3mo'])

export const YFINANCE_INTERVAL_RULES = INTRADAY_RULES

function utcMidnight(d: Date): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()))
}

/** `YYYY-MM-DD` または先頭が日付の ISO 文字列を UTC 日付の開始に正規化 */
export function parseBoundaryUtc(iso: string): Date {
  const m = String(iso).trim().match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) {
    throw new Error(`日付を解釈できません: ${JSON.stringify(iso)}`)
  }
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (!Number.isFinite(y) || !Number.isFinite(mo) || !Number.isFinite(d)) {
    throw new Error(`日付を解釈できません: ${JSON.stringify(iso)}`)
  }
  return new Date(Date.UTC(y, mo - 1, d))
}

function dayDiff(a: Date, b: Date): number {
  return Math.floor((b.getTime() - a.getTime()) / 86_400_000)
}

export type YfinanceRangeValidation =
  | { ok: true; error?: undefined }
  | { ok: false; error: string }

/**
 * カレンダー UI 用の事前検証（サーバ validate_yfinance_range と同じ判定）
 */
export function validateYfinanceRange(
  interval: string,
  startISO: string,
  endISO: string,
  now: Date = new Date(),
): YfinanceRangeValidation {
  const ref = utcMidnight(now)

  let startTs: Date
  let endTs: Date
  try {
    startTs = parseBoundaryUtc(startISO)
    endTs = parseBoundaryUtc(endISO)
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return { ok: false, error: msg }
  }

  if (startTs > endTs) {
    return { ok: false, error: 'start は end 以下である必要があります' }
  }

  if (UNLIMITED_INTERVALS.has(interval)) {
    if (endTs > ref) {
      return { ok: false, error: 'end は今日以前の日付を指定してください' }
    }
    return { ok: true }
  }

  const rule = INTRADAY_RULES[interval]
  if (!rule) {
    return {
      ok: false,
      error: `interval ${JSON.stringify(interval)} には start/end レンジ制限が未定義です（サポート外の可能性があります）`,
    }
  }

  if (endTs > ref) {
    return { ok: false, error: 'end は今日以前の日付を指定してください' }
  }

  const spanDays = dayDiff(startTs, endTs)
  if (spanDays > rule.maxRangeDays) {
    return {
      ok: false,
      error: `この interval（${interval}）では取得レンジは最大 ${rule.maxRangeDays} 日までです（現在: ${spanDays} 日）。期間を短くするか、日足（1d）を選んでください。`,
    }
  }

  const ageDays = dayDiff(startTs, ref)
  if (ageDays > rule.maxLookbackDays) {
    return {
      ok: false,
      error: `この interval（${interval}）では開始日は直近 ${rule.maxLookbackDays} 日以内である必要があります（開始が約 ${ageDays} 日前です）。`,
    }
  }

  return { ok: true }
}

export function rangeRuleHint(interval: string): string {
  if (UNLIMITED_INTERVALS.has(interval)) {
    return `interval=${interval}: 日付レンジに実務上の厳しい上限はありません（yfinance の提供範囲内）。`
  }
  const rule = INTRADAY_RULES[interval]
  if (!rule) {
    return `interval=${interval}: 制限情報なし。`
  }
  return `interval=${interval}: 開始は直近 ${rule.maxLookbackDays} 日以内、レンジ幅は最大 ${rule.maxRangeDays} 日まで（1 リクエスト）。`
}
