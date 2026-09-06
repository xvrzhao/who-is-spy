<script setup lang="ts">
import { computed, ref } from 'vue'

import { useGameStore } from '@/stores/game'
import { playerColor, playerName } from '@/utils/players'
import PlayerAvatar from './PlayerAvatar.vue'

const store = useGameStore()
const pick = ref<number | null>(null)

const show = computed(() => store.pendingInterrupt === 'need_vote')

// 候选：在场玩家排除自己
const candidates = computed(() =>
  store.presentPlayers.filter((id) => id !== store.realPlayerId),
)

function vote(target: number): void {
  if (store.submitState === 'submitting') return
  store.submitVote(target)
  pick.value = null
}
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="mask">
      <div class="panel">
        <h3>投票</h3>
        <p class="sub">
          你觉得谁是卧底？已投 {{ store.votedIds.length }}/{{ store.presentPlayers.length }} 人
        </p>
        <div class="grid">
          <button
            v-for="id in candidates"
            :key="id"
            class="cand"
            :style="{ borderColor: playerColor(id) }"
            @click="vote(id)"
          >
            <span class="emoji"><PlayerAvatar :id="id" /></span>
            <span class="cname">{{ id }}号 {{ playerName(id) }}</span>
          </button>
        </div>
        <button class="abstain btn btn-ghost" @click="vote(0)">弃票（拿不准就不投）</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}

.panel {
  width: min(480px, calc(100% - 32px));
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 22px 24px;
  animation: rise 0.25s var(--ease-out);
}

@keyframes rise {
  from {
    transform: translateY(16px);
    opacity: 0;
  }
}

h3 {
  font-size: 18px;
  margin-bottom: 4px;
}

.sub {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.cand {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 6px 10px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--border);
  background: var(--panel-soft);
  transition: all 0.15s var(--ease-out);
}

.cand:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  background: var(--bg-soft);
}

.emoji {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
}

.cname {
  font-size: 12px;
  color: var(--text-dim);
}

.abstain {
  width: 100%;
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
