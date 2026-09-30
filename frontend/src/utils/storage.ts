// localStorage 快照留档：后端不支持断点恢复，快照仅作为对局过程的本地记录
import type { GameSnapshot } from '@/api/types'

const keySnapshot = (gameId: string) => `wis:snapshot:${gameId}`

export function saveSnapshot(snapshot: GameSnapshot): void {
  try {
    localStorage.setItem(keySnapshot(snapshot.gameId), JSON.stringify(snapshot))
  } catch {
    // 超配额等异常：静默失败，快照只是留档增强
  }
}
