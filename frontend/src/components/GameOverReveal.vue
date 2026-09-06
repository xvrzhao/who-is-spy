<script setup lang="ts">
import { computed, ref } from 'vue'

import { useGameStore } from '@/stores/game'
import { playerName } from '@/utils/players'
import PlayerAvatar from './PlayerAvatar.vue'

const store = useGameStore()
const dismissed = ref(false)

// 等轮内弹窗（投票结果/淘汰）播完再出现，避免两层弹窗叠加
const show = computed(
  () =>
    store.reveal !== null &&
    !dismissed.value &&
    store.phase === 'gameover' &&
    !store.roundPopupBusy,
)

const iWin = computed(() => store.reveal?.is_real_player_win ?? false)
const myIdentity = computed(() => (store.reveal?.real_player_identity === 'spy' ? '卧底' : '平民'))

// 对方 = 敌对阵营：我是平民 → 对方是卧底（头像+ID）；我是卧底 → 对方是平民阵营
const iAmSpy = computed(() => store.reveal?.real_player_identity === 'spy')
const otherWord = computed(() => {
  const r = store.reveal
  if (!r) return ''
  return iAmSpy.value ? r.word_civilian : r.word_spy
})
const otherWordLabel = computed(() => (iAmSpy.value ? '平民词' : '卧底词'))
</script>

<template>
  <Transition name="fade">
    <div v-if="show && store.reveal" class="mask">
      <div class="card">
        <div class="banner" :class="store.reveal.winner">
          {{ store.reveal.winner === 'civilian' ? '平民胜利' : '卧底胜利' }}
        </div>
        <div class="result">{{ iWin ? '🎉 你赢了' : '😢 你输了' }}</div>

        <div class="sides">
          <!-- 我 -->
          <div class="side me-side">
            <div class="side-label">你</div>
            <div class="avatar big" :class="store.reveal.real_player_identity">
              <PlayerAvatar :id="store.reveal.real_player_id" />
            </div>
            <div class="side-name">{{ store.reveal.real_player_id }}号 {{ playerName(store.reveal.real_player_id, store.reveal.real_player_id) }}</div>
            <div class="identity" :class="store.reveal.real_player_identity">{{ myIdentity }}</div>
            <div class="word-chip mine">你的词：{{ iAmSpy ? store.reveal.word_spy : store.reveal.word_civilian }}</div>
          </div>

          <div class="vs">VS</div>

          <!-- 对方（敌对阵营） -->
          <div class="side">
            <div class="side-label">对方</div>
            <template v-if="!iAmSpy">
              <div class="avatar big spy">
                <PlayerAvatar :id="store.reveal.spy_id" />
              </div>
              <div class="side-name">{{ store.reveal.spy_id }}号 {{ playerName(store.reveal.spy_id, store.reveal.real_player_id) }}</div>
              <div class="identity spy">卧底</div>
            </template>
            <template v-else>
              <div class="avatar big civilian">👥</div>
              <div class="side-name">平民阵营（{{ store.playerTotal - 1 }} 人）</div>
              <div class="identity civilian">平民</div>
            </template>
            <div class="word-chip other">{{ otherWordLabel }}：{{ otherWord }}</div>
          </div>
        </div>

        <button class="btn btn-primary" @click="dismissed = true">进入赛后交流</button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 45;
}

.card {
  width: min(520px, calc(100% - 32px));
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 26px 28px;
  text-align: center;
  animation: rise 0.3s var(--ease-out);
}

@keyframes rise {
  from {
    transform: translateY(20px) scale(0.96);
    opacity: 0;
  }
}

.banner {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 6px;
  margin-bottom: 4px;
}

.banner.civilian {
  color: var(--civilian);
}

.banner.spy {
  color: var(--spy);
}

.result {
  font-size: 15px;
  color: var(--text-dim);
  margin-bottom: 18px;
}

.sides {
  display: flex;
  align-items: stretch;
  gap: 10px;
  margin-bottom: 20px;
}

.side {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  background: var(--bg-soft);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  padding: 14px 10px;
}

.me-side {
  border-color: rgba(108, 199, 125, 0.4);
}

.side-label {
  font-size: 12px;
  color: var(--text-faint);
  letter-spacing: 2px;
}

.vs {
  align-self: center;
  font-size: 14px;
  font-weight: 800;
  color: var(--text-faint);
}

.avatar.big {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--panel-soft);
  border: 3px solid;
  overflow: hidden;
}

.avatar.big.spy {
  border-color: var(--spy);
}

.avatar.big.civilian {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  border-color: var(--civilian);
}

.side-name {
  font-size: 13.5px;
  color: var(--text);
}

.identity {
  font-size: 14px;
  font-weight: 700;
  border-radius: 999px;
  padding: 1px 16px;
}

.identity.spy {
  background: rgba(217, 95, 95, 0.2);
  color: var(--spy);
}

.identity.civilian {
  background: rgba(108, 191, 158, 0.18);
  color: var(--civilian);
}

.word-chip {
  font-size: 12.5px;
  border-radius: 999px;
  padding: 3px 12px;
  white-space: nowrap;
}

.word-chip.mine {
  color: var(--you);
  background: rgba(108, 199, 125, 0.12);
  border: 1px solid rgba(108, 199, 125, 0.35);
}

.word-chip.other {
  color: var(--accent-soft);
  background: rgba(232, 168, 82, 0.1);
  border: 1px solid rgba(232, 168, 82, 0.3);
}

.btn {
  width: 100%;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
