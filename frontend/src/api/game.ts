// 高层 API：开局 / 应答。VITE_USE_MOCK=1 时切换到剧本驱动。

import type { PlayerId, SseFrame } from './types'
import { createFrameParser, sseFetch, type Transport } from './transport'
import { mockTransport } from './mock/driver'

/** mock 模式：.env 的 VITE_USE_MOCK=1，或运行时 localStorage['wis:mock:force']='1'（无需重启） */
export const USE_MOCK: boolean = (() => {
  try {
    if ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_USE_MOCK === '1') {
      return true
    }
    return globalThis.localStorage?.getItem('wis:mock:force') === '1'
  } catch {
    return false
  }
})()

/** API 前缀覆盖：默认 ''（同源，走 vite proxy）；可设 localStorage['wis:api:base']='http://x:8000' 直连远程后端 */
const API_BASE: string = USE_MOCK
  ? ''
  : (() => {
      try {
        return globalThis.localStorage?.getItem('wis:api:base') ?? ''
      } catch {
        return ''
      }
    })()

export const apiUrl = (path: string) => `${API_BASE}${path}`

const transport: Transport = USE_MOCK
  ? (mockTransport as unknown as Transport)
  : sseFetch

/** 开局：POST /api/games，返回 SSE 帧流（/api 前缀由 backend/src/domains/__init__.py 挂载） */
export function startGame(playerTotal: number, signal: AbortSignal): AsyncIterable<SseFrame> {
  return streamFrames(apiUrl('/api/games'), { player_total: playerTotal }, signal)
}

/**
 * 应答 interrupt：POST /api/games/{id}/resume
 * resume 必填（后端无缺省），取值类型由挂起的 interrupt 决定：发言文本 / 投票玩家ID / "内容||ID" / true
 */
export function resumeGame(gameId: string, resume: unknown, signal: AbortSignal): AsyncIterable<SseFrame> {
  return streamFrames(apiUrl(`/api/games/${gameId}/resume`), { resume }, signal)
}

/** transport 文本块流 → SSE 帧流（每个 chunk 到达后立刻排空已解析帧） */
async function* streamFrames(
  url: string,
  body: Record<string, unknown>,
  signal: AbortSignal,
): AsyncIterable<SseFrame> {
  const frames: SseFrame[] = []
  const parse = createFrameParser((frame) => frames.push(frame))
  for await (const chunk of transport(url, body, signal)) {
    parse(chunk)
    while (frames.length > 0) yield frames.shift()!
  }
}

// 便捷重导出：store 中 resume 值的类型约束（镜像后端 RESUME_VALIDATORS）
export type ResumeValue = string | number | boolean
export type { PlayerId }
