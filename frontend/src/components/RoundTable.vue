<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import type { PlayerId } from '@/api/types'
import { useGameStore } from '@/stores/game'
import PlayerSeat from './PlayerSeat.vue'

const store = useGameStore()

/** 座位排布：真人固定 6 点钟（正下方），其余按玩家 ID 顺时针——发言顺序即座位顺序 */
const seatOrder = computed<PlayerId[]>(() => {
  const all = store.allPlayerIds
  const me = store.realPlayerId
  if (me === null) return all
  const idx = all.indexOf(me)
  return [...all.slice(idx), ...all.slice(0, idx)]
})

const seatCount = computed(() => seatOrder.value.length)

/** k 序号座位的角度（度）：90° = 正下方，顺时针递增 */
function angleOf(k: number): number {
  return 90 + (360 / seatCount.value) * k
}

function seatPos(pid: PlayerId): { x: number; y: number } {
  const k = seatOrder.value.indexOf(pid)
  const a = (angleOf(k) * Math.PI) / 180
  return { x: 50 + 41 * Math.cos(a), y: 50 + 41 * Math.sin(a) }
}

const seatStyle = (pid: PlayerId) => {
  const { x, y } = seatPos(pid)
  return { left: `${x}%`, top: `${y}%` }
}

// 「AI 思考中」：超过 8s 无帧时在轮次信息旁提示
const now = ref(Date.now())
let timer: ReturnType<typeof setInterval>
onMounted(() => {
  timer = setInterval(() => (now.value = Date.now()), 1000)
})
onBeforeUnmount(() => clearInterval(timer))

const stageText = computed(() => {
  if (store.phase === 'gameover') return '对局结束'
  if (store.phase === 'exchange') return '赛后交流'
  if (store.phase === 'finished') return '已结束'
  if (store.stage === 'voting') return `第 ${store.gameRound} 轮 · 投票`
  return `第 ${store.gameRound} 轮 · 发言`
})

const aiThinking = computed(() => {
  if (store.pendingInterrupt) return false
  if (store.connStatus === 'reconnecting' || store.connStatus === 'conflict') return false
  if (store.audioPlayingId !== null) return false // 正在播语音＝在发言，不是在思考
  return now.value - store.lastFrameAt > 8000 && store.phase !== 'finished'
})

function quit(): void {
  if (store.phase === 'finished' || confirm('确定离开吗？当前对局会保留，回来可继续。')) {
    store.leaveGame()
  }
}
</script>

<template>
  <div class="table-wrap">
    <!-- 左上：轮次/阶段/思考中 -->
    <div class="corner corner-tl">
      <span class="stage-chip">{{ stageText }}</span>
      <span v-if="aiThinking" class="thinking"><span class="dot" />AI 思考中</span>
    </div>

    <!-- 右上：静音/退出 -->
    <div class="corner corner-tr">
      <button class="icon-btn" :title="store.muted ? '开启声音' : '静音'" @click="store.toggleMute()">
        {{ store.muted ? '🔇' : '🔊' }}
      </button>
      <button class="icon-btn quit" title="离开对局" @click="quit">退出</button>
    </div>

    <div class="felt">
      <div class="table-center">
        <template v-if="store.phase === 'gameover' || store.phase === 'exchange'">
          <div class="center-title">{{ store.reveal?.winner === 'civilian' ? '平民胜利' : '卧底胜利' }}</div>
        </template>
        <template v-else-if="store.stage === 'voting'">
          <div class="center-title">投票中</div>
          <div class="center-sub">{{ store.votedIds.length }} / {{ store.presentPlayers.length }} 已投</div>
        </template>
        <template v-else>
          <div class="center-title">第 {{ store.gameRound }} 轮</div>
          <div class="center-sub">轮流描述你的词</div>
        </template>
      </div>
      <div
        v-for="pid in seatOrder"
        :key="pid"
        class="seat"
        :style="seatStyle(pid)"
      >
        <PlayerSeat :player-id="pid" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.table-wrap {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  padding: 12px;
}

.corner {
  position: absolute;
  top: 10px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
}

.corner-tl {
  left: 14px;
}

.corner-tr {
  right: 14px;
}

.stage-chip {
  font-size: 16px;
  color: var(--accent-soft);
  background: rgba(232, 168, 82, 0.12);
  border: 1px solid rgba(232, 168, 82, 0.28);
  padding: 5px 16px;
  border-radius: 999px;
  white-space: nowrap;
}

.thinking {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-dim);
  white-space: nowrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--info);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}

.icon-btn {
  font-size: 16px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  background: var(--panel-soft);
  border: 1px solid var(--border);
  color: var(--text-dim);
}

.icon-btn:hover {
  color: var(--text);
}

.quit:hover {
  color: var(--danger);
}

.felt {
  position: relative;
  width: min(100%, 62vh);
  aspect-ratio: 1;
  max-height: 100%;
}

.felt::before {
  content: '';
  position: absolute;
  inset: 14%;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 32%, var(--table-felt) 0%, var(--table-felt-deep) 75%);
  border: 10px solid var(--table-rim);
  box-shadow:
    inset 0 0 48px rgba(0, 0, 0, 0.45),
    0 6px 24px rgba(0, 0, 0, 0.5);
}

.table-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  gap: 4px;
}

.center-title {
  font-size: 20px;
  font-weight: 700;
  color: #eaf3ec;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.center-sub {
  font-size: 12px;
  color: rgba(234, 243, 236, 0.75);
}

.seat {
  position: absolute;
  transform: translate(-50%, -50%);
}
</style>
