// 语音播放队列：严格串行（上一条 ended 才播下一条），并与后端 speech gate 协调。
//
// gate 协调（四情形）：
//   A 正常连播：player_speech 入队播放……gate 到达仍在播 → armGate → 排空后回调确认
//   B gate 先到：gate 到达时队列已空 → armGate 立即触发确认回调
//   C 真人后的 gate：无音频，队列必 idle → 立即确认
//   D 静音：不入队；切换瞬间 clearAndFlush → 已 arm 的 gate 立即确认
//
// 关键不变量：同一时刻至多一个未确认 gate；确认回调只从「armGate 时 idle」「arm 后排空」
// 「切静音 flush」三条路径触发，均在主线程串行执行，无竞态。

import { base64ToArrayBuffer } from '@/utils/misc'
import { audioCtx } from './unlock'

export interface SpeechItem {
  playerId: number
  text: string
  audio: ArrayBuffer | null // null = TTS 降级，不入队
}

export class SpeechQueue {
  private queue: SpeechItem[] = []
  private current: { src: AudioBufferSourceNode; item: SpeechItem } | null = null
  private activeItem: SpeechItem | null = null // 解码中或播放中的条目（idle 判定用）
  private gateArmed = false
  private stopped = false

  muted = false

  /** 播放开始/结束（驱动座位光环与字幕） */
  onPlayStart: (item: SpeechItem) => void = () => {}
  onPlayEnd: (item: SpeechItem) => void = () => {}
  /** gate armed 且队列已排空 → 通知上层确认 speech_playback_done */
  onGateReady: () => void = () => {}

  /** idle = 既无解码/播放中的条目，也无排队条目。解码耗时不可忽略（约 1MB mp3），
   *  若只看 current 会在解码窗口内误判 idle，导致 gate 提前确认、音频滞后于局面推进 */
  get idle(): boolean {
    return this.activeItem === null && this.queue.length === 0
  }

  enqueue(item: SpeechItem): void {
    if (this.stopped) return
    if (this.muted || item.audio === null) return // 静音或降级：不入队（gate 语义不受影响）
    this.queue.push(item)
    void this.pump()
  }

  private async pump(): Promise<void> {
    if (this.activeItem !== null || this.queue.length === 0) return
    const ctx = audioCtx()
    const item = this.queue.shift()!
    if (item.audio === null) return // 理论不可达（enqueue 已过滤），防御性兜底
    this.activeItem = item
    try {
      if (!ctx) {
        // 无 AudioContext（未解锁/node 环境）：直接视为播放完成，避免卡死 gate
        this.onPlayStart(item)
        this.onPlayEnd(item)
      } else {
        const buffer = await ctx.decodeAudioData(item.audio.slice(0))
        if (this.stopped) {
          this.activeItem = null
          return
        }
        await new Promise<void>((resolve) => {
          const src = ctx.createBufferSource()
          src.buffer = buffer
          src.connect(ctx.destination)
          src.onended = () => resolve()
          this.current = { src, item }
          this.onPlayStart(item)
          src.start()
        })
      }
    } catch {
      // 解码/播放失败：跳过该条，不阻塞流程
    }
    this.activeItem = null
    this.current = null
    this.onPlayEnd(item)
    this.afterItemDone()
  }

  private afterItemDone(): void {
    if (this.queue.length === 0) {
      if (this.gateArmed) {
        this.gateArmed = false
        this.onGateReady()
      }
    } else {
      void this.pump()
    }
  }

  /** gate interrupt 到达：队列空则立即就绪，否则等排空 */
  armGate(): void {
    if (this.idle) {
      this.onGateReady()
      return
    }
    this.gateArmed = true
  }

  /** 上层已确认/放弃（如断线重建） */
  disarmGate(): void {
    this.gateArmed = false
  }

  /** 切静音：清空并停止当前播放；若 gate 已 arm 立即就绪 */
  clearAndFlush(): void {
    this.queue = []
    if (this.current) {
      try {
        this.current.src.onended = null
        this.current.src.stop()
      } catch {
        // 已停止
      }
      this.current = null
    }
    this.activeItem = null // 解码中的条目也一并放弃（stopped 守卫兜底 decode 完成路径）
    if (this.gateArmed) {
      this.gateArmed = false
      this.onGateReady()
    }
  }

  /** 彻底停用（对局结束） */
  destroy(): void {
    this.stopped = true
    this.clearAndFlush()
  }
}

/** player_speech payload → 队列条目（降级时 audio=null） */
export function speechItemFromEvent(p: {
  player_id: number
  text: string
  audio_base64: string
}): SpeechItem {
  return {
    playerId: p.player_id,
    text: p.text,
    audio: p.audio_base64 ? base64ToArrayBuffer(p.audio_base64) : null,
  }
}
