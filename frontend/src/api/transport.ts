// SSE 传输层：后端 SSE 均为 POST（EventSource 只支持 GET，不可用），
// 用 fetch 流式读取 + 自行分帧。Transport 抽象便于 mock driver 替换。

import type { SseFrame } from './types'

export type Transport = (
  url: string,
  body: Record<string, unknown> | undefined,
  signal: AbortSignal,
) => AsyncIterable<string>

export class HttpError extends Error {
  constructor(
    public status: number,
    public bodyText: string,
  ) {
    super(`HTTP ${status}: ${bodyText.slice(0, 200)}`)
  }
}

/** 真实实现：POST + 流式读取，逐块 yield 文本 */
export const sseFetch: Transport = async function* (url, body, signal) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body ?? {}),
    signal,
  })
  if (!resp.ok || !resp.body) {
    throw new HttpError(resp.status, await resp.text().catch(() => ''))
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) return
      yield decoder.decode(value, { stream: true })
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * 分帧解析器：按 \n\n 切帧，event 名取 event: 行，payload 取 data: 行 JSON。
 * 与后端 sse_event（backend/src/utils/sse.py：event 行 + 单 data 行，data 即 payload）精确兼容，
 * 并容忍标准 SSE 变体（注释行、多 data 行）。
 */
export function createFrameParser(onFrame: (frame: SseFrame) => void) {
  let buf = ''
  return (chunk: string): void => {
    buf += chunk
    for (;;) {
      const idx = buf.indexOf('\n\n')
      if (idx < 0) break
      const raw = buf.slice(0, idx)
      buf = buf.slice(idx + 2)

      let eventName = ''
      const dataLines: string[] = []
      for (const line of raw.split('\n')) {
        if (line.startsWith(':')) continue // 注释/心跳行
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
      }
      if (!eventName || dataLines.length === 0) continue
      try {
        onFrame({ event: eventName as SseFrame['event'], payload: JSON.parse(dataLines.join('\n')) })
      } catch {
        // 非 JSON data 行直接丢弃（保持与 EventSource 容错语义一致）
      }
    }
  }
}
