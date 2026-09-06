// AudioContext 解锁：浏览器自动播放策略要求首次播放前有用户手势。
// 必须在 click 等手势事件的同步调用栈里执行。

let ctx: AudioContext | null = null

export function audioCtx(): AudioContext | null {
  return ctx
}

/** 在用户手势内调用：创建 + resume + 播放静音 buffer，解锁后续自动播放 */
export function unlockAudio(): boolean {
  try {
    if (!ctx) ctx = new AudioContext()
    void ctx.resume()
    // Safari 等实现要求真正 start 过一次 source 才算解锁
    const buf = ctx.createBuffer(1, 1, 22050)
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)
    src.start(0)
    return ctx.state === 'running' || ctx.state === 'suspended'
  } catch {
    return false
  }
}

export function isUnlocked(): boolean {
  return ctx !== null && ctx.state === 'running'
}
