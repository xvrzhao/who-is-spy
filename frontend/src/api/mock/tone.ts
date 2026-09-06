// mock 专用：运行时生成短音效 WAV 并 base64。
// decodeAudioData 按字节嗅探容器（与 audio_format 字段无关），mock 无需真实 mp3 资源。
// 不同玩家用不同基频，听感上区分发言人。

export function toneWavBase64(freq = 440, durationSec = 0.7): string {
  const sampleRate = 22050
  const n = Math.floor(sampleRate * durationSec)
  const dataBytes = n * 2
  const buf = new ArrayBuffer(44 + dataBytes)
  const v = new DataView(buf)
  const wstr = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i))
  }
  wstr(0, 'RIFF')
  v.setUint32(4, 36 + dataBytes, true)
  wstr(8, 'WAVE')
  wstr(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true) // PCM
  v.setUint16(22, 1, true) // mono
  v.setUint32(24, sampleRate, true)
  v.setUint32(28, sampleRate * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  wstr(36, 'data')
  v.setUint32(40, dataBytes, true)
  for (let i = 0; i < n; i++) {
    const t = i / sampleRate
    // attack/release 包络去爆音
    const env = Math.min(1, t / 0.03) * Math.min(1, (durationSec - t) / 0.1)
    const s = (Math.sin(2 * Math.PI * freq * t) + 0.5 * Math.sin(2 * Math.PI * freq * 1.5 * t)) / 1.5
    v.setInt16(44 + i * 2, Math.round(s * env * 0.35 * 32767), true)
  }
  let bin = ''
  const u8 = new Uint8Array(buf)
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i])
  return btoa(bin)
}

/** 按玩家 ID 确定的音色（mock） */
export function playerToneBase64(playerId: number): string {
  return toneWavBase64(330 + ((playerId * 97) % 240))
}
