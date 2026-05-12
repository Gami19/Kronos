import { WINDOW, windowFitsRows } from '../components/TimeWindowSlider'

/** `/finetune` ステッパー遷移に使うコンテキスト（FinetunePage の state から組み立てる） */
export type FinetuneWizardGuardCtx = {
  filePath: string
  modelLoaded: boolean
  loadedSuccess: boolean
  dataInfoRows: number | undefined
}

export function canNavigateToFinetuneStep(
  targetIndex: number,
  ctx: FinetuneWizardGuardCtx,
): { ok: boolean; reason?: string } {
  if (targetIndex === 0) {
    return { ok: true }
  }

  const fp = ctx.filePath.trim()
  if (!fp) {
    return { ok: false, reason: 'ステップ1で file_path を指定（取り込み・検証・パス入力）してください' }
  }

  if (targetIndex === 1 || targetIndex === 2) {
    return { ok: true }
  }

  if (targetIndex === 3 || targetIndex === 4) {
    if (!ctx.modelLoaded) {
      return { ok: false, reason: 'ステップ2でモデルを読み込んでから進んでください' }
    }
    if (!ctx.loadedSuccess || ctx.dataInfoRows == null) {
      return { ok: false, reason: 'ステップ1でプレビュー読込に成功してから進んでください' }
    }
    if (!windowFitsRows(ctx.dataInfoRows)) {
      return {
        ok: false,
        reason: `データ本数が不足しています（時間窓に最低 ${WINDOW} 本必要です）`,
      }
    }
    return { ok: true }
  }

  if (targetIndex === 5) {
    return { ok: true }
  }

  return { ok: false, reason: '不明なステップです' }
}
