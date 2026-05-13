/** finetune CustomKlineDataset の int 分割に合わせたクライアント側チェック用 */

export const DEFAULT_TRAIN_RATIO = 0.85
export const DEFAULT_VAL_RATIO = 0.15
export const DEFAULT_TEST_RATIO = 0

const RATIO_SUM_EPS = 1e-5

export function finetuneTimeSplitLengths(
  n: number,
  trainRatio: number,
  valRatio: number,
): { trainEnd: number; valEnd: number; valLen: number } {
  const trainEnd = Math.trunc(n * trainRatio)
  const valEnd = Math.trunc(n * (trainRatio + valRatio))
  const valLen = valEnd - trainEnd
  return { trainEnd, valEnd, valLen }
}

/**
 * 学習ジョブの窓・分割が成立しないときのユーザー向けメッセージ。成立なら null。
 */
export function trainWindowClientMessage(
  n: number,
  lookbackWindow: number,
  predictWindow: number,
  trainRatio: number,
  valRatio: number,
  testRatio: number,
): string | null {
  const window = lookbackWindow + predictWindow + 1
  const sum = trainRatio + valRatio + testRatio
  if (Math.abs(sum - 1) > RATIO_SUM_EPS) {
    return `train_ratio + val_ratio + test_ratio の合計は 1.0 である必要があります（現在: ${sum.toFixed(6)}）`
  }
  if (n <= 0) {
    return 'データ行数が取得できません。プレビューを読み込むか、サーバ側の検証に任せてください。'
  }
  const { trainEnd, valLen } = finetuneTimeSplitLengths(n, trainRatio, valRatio)
  if (trainEnd < window) {
    return (
      `学習区間の行数（約 ${trainEnd} 行）が窓長 ${window}（lookback ${lookbackWindow} + predict ${predictWindow} + 1）未満です。` +
      ' train_ratio を下げる・データを増やす・窓を縮小してください。'
    )
  }
  if (valLen < window) {
    return (
      `検証区間の行数（約 ${valLen} 行）が窓長 ${window} 未満です（全行の目安: ${n}）。` +
      ' val_ratio を上げる・データを増やす・窓を縮小してください。'
    )
  }
  return null
}
