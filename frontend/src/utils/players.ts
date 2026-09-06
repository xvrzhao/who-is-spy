// 玩家档案：头像与昵称来自 src/assets/avatars/ 下的图片（文件名「id-玩家昵称.ext」），
// 真人玩家头像固定使用 real_player.png。同一局内按 ID 确定、永不变化。
import type { PlayerId } from '@/api/types'

// eager 全量收进构建：key 形如 /src/assets/avatars/1-Xavier.jpg，value 为构建后 URL
const modules = import.meta.glob('@/assets/avatars/*', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>

const AVATARS = new Map<number, string>()
const NAMES = new Map<number, string>()
let REAL_AVATAR = ''

for (const [path, url] of Object.entries(modules)) {
  const file = path.slice(path.lastIndexOf('/') + 1)
  if (file === 'real_player.png') {
    REAL_AVATAR = url
    continue
  }
  const m = /^(\d+)-(.+)\.[^.]+$/.exec(file)
  if (!m) continue
  AVATARS.set(Number(m[1]), url)
  NAMES.set(Number(m[1]), m[2])
}

/** 昵称（取自头像文件名）；真人玩家显示「你」 */
export function playerName(id: PlayerId, realId: PlayerId | null = null): string {
  if (id === realId) return '你'
  return NAMES.get(id) ?? `${id}号`
}

/** 头像图片 URL；真人固定 real_player.png */
export function playerAvatar(id: PlayerId, realId: PlayerId | null): string {
  if (id === realId) return REAL_AVATAR
  return AVATARS.get(id) ?? ''
}

/** 座位描边色（暗底上的中低饱和色相按 ID 区分） */
export function playerColor(id: PlayerId): string {
  return `hsl(${(id * 60) % 360} 45% 62%)`
}
