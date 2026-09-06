<script setup lang="ts">
// 轮内弹窗序列：vote_end 后先弹「投票结果」（左侧获票者，右侧投票者头像队列），
// 定时自动切到「淘汰弹窗」（或平票/全员弃票小提示），点击任意处可跳过当前步骤。
// 播放期间置 store.roundPopupBusy，终局弹窗等本序列结束再出现。
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import type { PlayerId } from '@/api/types'
import { useGameStore } from '@/stores/game'
import { playerColor, playerName } from '@/utils/players'
import PlayerAvatar from './PlayerAvatar.vue'

const VOTE_MS = 3500
const ELIM_MS = 2500
const TIE_MS = 1500

const store = useGameStore()

type Step =
  | { kind: 'vote'; round: number; rows: { target: PlayerId; voters: PlayerId[] }[]; abstain: PlayerId[] }
  | { kind: 'elim'; playerId: PlayerId; identity: 'civilian' | 'spy'; round: number }
  | { kind: 'tie'; allAbstain: boolean; round: number }

const step = ref<Step | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null
let shownRound = 0

function clearTimer(): void {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

function finish(): void {
  clearTimer()
  step.value = null
  store.roundPopupBusy = false
}

/** 跳过当前步骤 → 进入下一步或结束 */
function advance(): void {
  clearTimer()
  if (!step.value) return
  const cur = step.value
  if (cur.kind === 'vote') {
    // 淘汰信息以 store.eliminated 记录的本轮淘汰者为准（vote_end 帧同时写入两者）
    const eliminatedId = Object.keys(store.eliminated)
      .map(Number)
      .find((pid) => store.eliminated[pid]?.round === cur.round)
    if (eliminatedId !== undefined) {
      showElim(eliminatedId, cur.round)
      return
    }
    showTie(cur.round)
    return
  }
  finish() // elim / tie 之后序列结束
}

function showElim(pid: PlayerId, round: number): void {
  const identity = store.eliminated[pid]?.identity ?? 'civilian'
  step.value = { kind: 'elim', playerId: pid, identity, round }
  timer = setTimeout(finish, ELIM_MS)
}

function showTie(round: number): void {
  const vote = store.lastVote
  const allAbstain = !!vote && Object.keys(vote.collect).length === 0
  step.value = { kind: 'tie', allAbstain, round }
  timer = setTimeout(finish, TIE_MS)
}

watch(
  () => store.lastVote,
  (vote) => {
    if (!vote || vote.round === shownRound) return
    shownRound = vote.round
    const rows = Object.entries(vote.collect)
      .map(([target, voters]) => ({ target: Number(target), voters }))
      .sort((a, b) => b.voters.length - a.voters.length || a.target - b.target)
    if (rows.length === 0) {
      // 全员弃票：直接小提示
      store.roundPopupBusy = true
      showTie(vote.round)
      return
    }
    store.roundPopupBusy = true
    step.value = { kind: 'vote', round: vote.round, rows, abstain: vote.abstain }
    timer = setTimeout(advance, VOTE_MS)
  },
)

onBeforeUnmount(finish)

const elimIdentityText = computed(() => (step.value?.kind === 'elim' ? (step.value.identity === 'spy' ? '卧底' : '平民') : ''))

/** 投票人头像超宽时按住左右拖动滚动（不满一行时无滚动，行为不变） */
function onVotersPointerDown(e: PointerEvent): void {
  const el = e.currentTarget as HTMLElement
  if (el.scrollWidth <= el.clientWidth) return
  let lastX = e.clientX
  const move = (ev: PointerEvent): void => {
    el.scrollLeft -= ev.clientX - lastX
    lastX = ev.clientX
  }
  const up = (): void => {
    el.removeEventListener('pointermove', move)
    el.removeEventListener('pointerup', up)
    el.removeEventListener('pointercancel', up)
  }
  el.addEventListener('pointermove', move)
  el.addEventListener('pointerup', up)
  el.addEventListener('pointercancel', up)
}
</script>

<template>
  <Transition name="fade">
    <div v-if="step" class="mask" @click="advance">

      <!-- 投票结果 -->
      <div v-if="step.kind === 'vote'" class="card">
        <h3>第 {{ step.round }} 轮 · 投票结果</h3>
        <div class="rows">
          <div v-for="row in step.rows" :key="row.target" class="row">
            <div class="target">
              <span class="avatar" :style="{ borderColor: playerColor(row.target) }">
                <PlayerAvatar :id="row.target" />
              </span>
              <span class="who">{{ row.target }}号 {{ playerName(row.target, store.realPlayerId) }}</span>
            </div>
            <span class="count">{{ row.voters.length }}票</span>
            <div class="voters" @pointerdown="onVotersPointerDown" @click.stop>
              <span v-for="v in row.voters" :key="v" class="voter" :title="`${v}号 投了 ${row.target}号`">
                <span class="avatar sm" :style="{ borderColor: playerColor(v) }">
                  <PlayerAvatar :id="v" />
                </span>
                <span class="vid">{{ v }}</span>
              </span>
            </div>
          </div>
        </div>
        <div v-if="step.abstain.length" class="abstain">弃票：{{ step.abstain.map((v) => `${v}号`).join('、') }}</div>
        <div class="tap-hint">点击继续</div>
      </div>

      <!-- 淘汰 -->
      <div v-else-if="step.kind === 'elim'" class="card elim">
        <div class="avatar big" :style="{ borderColor: playerColor(step.playerId) }">
          <PlayerAvatar :id="step.playerId" />
        </div>
        <div class="elim-name">{{ step.playerId }}号 {{ playerName(step.playerId, store.realPlayerId) }}</div>
        <div class="elim-identity" :class="step.identity">{{ elimIdentityText }}</div>
        <div class="elim-sub">被淘汰出局</div>
        <div class="tap-hint">点击继续</div>
      </div>

      <!-- 平票 / 全员弃票 -->
      <div v-else class="card tie">
        <div class="tie-text">{{ step.allAbstain ? '全员弃票，无人淘汰' : '平票，无人淘汰' }}</div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 42;
  cursor: pointer;
}

.card {
  width: min(520px, calc(100% - 32px));
  max-height: calc(100% - 48px);
  overflow-y: auto;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 20px 24px;
  animation: rise 0.25s var(--ease-out);
}

@keyframes rise {
  from {
    transform: translateY(14px);
    opacity: 0;
  }
}

h3 {
  font-size: 16px;
  margin-bottom: 14px;
  text-align: center;
}

.rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-soft);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 8px 12px;
}

.target {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 112px;
}

.who {
  font-size: 13.5px;
  white-space: nowrap;
}

.count {
  flex: none;
  margin: 0 2px 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #3d2b12;
  background: var(--accent-soft);
  border-radius: 999px;
  padding: 1px 10px;
}

/* 投票人一列：单行不换行，放不下时左右拖动 */
.voters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  cursor: grab;
  scrollbar-width: none;
  padding: 2px 0;
}

.voters::-webkit-scrollbar {
  display: none;
}

.voters:active {
  cursor: grabbing;
}

.voter {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: none;
}

.vid {
  font-size: 11px;
  color: var(--text-dim);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--panel-soft);
  border: 2px solid;
  overflow: hidden;
  flex: none;
}

.avatar.sm {
  width: 32px;
  height: 32px;
}

.avatar.big {
  width: 84px;
  height: 84px;
  margin: 4px auto 10px;
  border-width: 3px;
}

.abstain {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--text-faint);
  text-align: center;
}

.tap-hint {
  margin-top: 12px;
  font-size: 11px;
  color: var(--text-faint);
  text-align: center;
}

.card.elim {
  text-align: center;
}

.elim-name {
  font-size: 18px;
  font-weight: 700;
}

.elim-identity {
  display: inline-block;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 700;
  border-radius: 999px;
  padding: 3px 18px;
}

.elim-identity.spy {
  background: rgba(217, 95, 95, 0.2);
  color: var(--spy);
}

.elim-identity.civilian {
  background: rgba(108, 191, 158, 0.18);
  color: var(--civilian);
}

.elim-sub {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-dim);
}

.card.tie {
  padding: 22px 32px;
}

.tie-text {
  font-size: 17px;
  color: var(--text);
  white-space: nowrap;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
