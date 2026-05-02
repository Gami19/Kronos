import type { OhlcRow } from '../api/types'

export interface ErrorStats {
  mae: number
  rmse: number
  mape: number
}

export function getPredictionQuality(predictions: OhlcRow[], actuals: OhlcRow[]): ErrorStats {
  if (!predictions?.length || !actuals?.length) {
    return { mae: 0, rmse: 0, mape: 0 }
  }

  const minLen = Math.min(predictions.length, actuals.length)
  let mae = 0
  let rmse = 0
  let mape = 0

  for (let i = 0; i < minLen; i++) {
    const pred = predictions[i]
    const act = actuals[i]
    const error = Math.abs(pred.close - act.close)
    const percentError = act.close !== 0 ? (error / act.close) * 100 : 0
    mae += error
    rmse += error * error
    mape += percentError
  }

  mae /= minLen
  rmse = Math.sqrt(rmse / minLen)
  mape /= minLen

  return { mae, rmse, mape }
}
