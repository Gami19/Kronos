/**
 * catch 節や fetch 失敗から UI 向けの短文を得る（空や未知の値でも破綻しない）
 */
export function formatUserFacingError(error: unknown): string {
  if (error instanceof Error) {
    const m = error.message.trim()
    if (m) return m
    return error.name || 'エラーが発生しました'
  }
  if (typeof error === 'string') {
    const m = error.trim()
    return m || 'エラーが発生しました'
  }
  if (error != null && typeof error === 'object' && 'message' in error) {
    const raw = (error as { message: unknown }).message
    if (typeof raw === 'string' && raw.trim()) return raw.trim()
  }
  if (typeof error === 'number' || typeof error === 'boolean') {
    return String(error)
  }
  return 'エラーが発生しました'
}
