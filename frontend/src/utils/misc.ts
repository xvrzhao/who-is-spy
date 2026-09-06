// base64 -> ArrayBuffer（直接 atob + Uint8Array，避免超长 data URL 的 fetch 限制）
export function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes.buffer
}

/** 节流：delay 内多次调用只执行最后一次 */
export function throttleTrailing<T extends (...args: any[]) => void>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<T>
  return ((...args: Parameters<T>) => {
    lastArgs = args
    if (timer) return
    timer = setTimeout(() => {
      timer = null
      fn(...lastArgs)
    }, delay)
  }) as T
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
