// localStorage 持久化：当前局指针 + 全量快照（断线/刷新恢复现场）
import type { GameSnapshot } from '@/api/types'

const KEY_CURRENT = 'wis:current'
const keySnapshot = (gameId: string) => `wis:snapshot:${gameId}`

export interface CurrentGame {
  gameId: string
  playerTotal: number
  updatedAt: number
}

export function saveCurrent(gameId: string, playerTotal: number): void {
  localStorage.setItem(
    KEY_CURRENT,
    JSON.stringify({ gameId, playerTotal, updatedAt: Date.now() } satisfies CurrentGame),
  )
}

export function loadCurrent(): CurrentGame | null {
  const raw = localStorage.getItem(KEY_CURRENT)
  if (!raw) return null
  try {
    return JSON.parse(raw) as CurrentGame
  } catch {
    return null
  }
}

export function clearCurrent(): void {
  localStorage.removeItem(KEY_CURRENT)
}

export function saveSnapshot(snapshot: GameSnapshot): void {
  try {
    localStorage.setItem(keySnapshot(snapshot.gameId), JSON.stringify(snapshot))
  } catch {
    // 超配额等异常：静默失败，快照只是恢复体验的增强
  }
}

export function loadSnapshot(gameId: string): GameSnapshot | null {
  const raw = localStorage.getItem(keySnapshot(gameId))
  if (!raw) return null
  try {
    const snap = JSON.parse(raw) as GameSnapshot
    return snap.version === 1 ? snap : null
  } catch {
    return null
  }
}
