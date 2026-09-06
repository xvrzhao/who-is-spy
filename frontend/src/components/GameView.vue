<script setup lang="ts">
import { computed } from 'vue'

import { useGameStore } from '@/stores/game'
import GameOverReveal from './GameOverReveal.vue'
import InputBar from './InputBar.vue'
import RoundPopup from './RoundPopup.vue'
import RoundTable from './RoundTable.vue'
import StageToast from './StageToast.vue'
import VotePanel from './VotePanel.vue'
import WordReveal from './WordReveal.vue'

const store = useGameStore()

// 底部大词牌：开局弹框关闭后显示，对局/交流阶段常驻（终局已揭示双方词语，隐藏）
const showWordPlate = computed(
  () =>
    store.myWord !== null &&
    store.wordRevealed &&
    (store.phase === 'playing' || store.phase === 'exchange'),
)
</script>

<template>
  <div class="game-view">
    <RoundTable class="table-area" />

    <!-- 我的词：圆桌整体正下方、输入栏上方，居中大词牌；赛后交流阶段附上卧底词 -->
    <div v-if="showWordPlate" class="word-plates">
      <div class="word-plate">
        <span class="wp-label">你的词</span>
        <span class="wp-word">{{ store.myWord }}</span>
      </div>
      <div v-if="store.phase === 'exchange' && store.reveal" class="word-plate spy">
        <span class="wp-label">卧底词</span>
        <span class="wp-word">{{ store.reveal.word_spy }}</span>
      </div>
    </div>

    <InputBar />

    <VotePanel />
    <RoundPopup />
    <GameOverReveal />
    <WordReveal />
    <StageToast />

    <!-- 连接状态提示 -->
    <Transition name="fade">
      <div v-if="store.connStatus === 'conflict'" class="overlay-banner">
        ⚠️ 这局游戏正在另一个窗口/标签页运行。关掉那边，或等待它在等待输入时接管。
      </div>
      <div v-else-if="store.connStatus === 'reconnecting'" class="overlay-banner warn">
        连接中断，正在重连…
      </div>
    </Transition>

    <!-- 后端错误覆盖层 -->
    <Transition name="fade">
      <div v-if="store.lastError" class="overlay-mask">
        <div class="overlay-card">
          <h3>出错了 😵</h3>
          <p class="err">{{ store.lastError.type }}: {{ store.lastError.message }}</p>
          <div class="btns">
            <button class="btn btn-primary" @click="store.retryAfterError()">从断点继续</button>
            <button class="btn btn-ghost" @click="store.leaveGame()">离开对局</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 终局回到大厅入口 -->
    <Transition name="fade">
      <div v-if="store.phase === 'finished'" class="finished-bar">
        对局已结束
        <button class="btn btn-primary small" @click="store.leaveGame()">再来一局</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.game-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
}

.table-area {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

/* 词牌区：圆桌下方、输入栏上方，居中（赛后交流追加卧底词一排） */
.word-plates {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  pointer-events: none;
}

.word-plate {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(108, 199, 125, 0.12);
  border: 1.5px solid rgba(108, 199, 125, 0.45);
  border-radius: 999px;
  padding: 8px 26px;
  box-shadow: var(--shadow-md);
}

/* 赛后交流的卧底词牌（略小、红调） */
.word-plate.spy {
  background: rgba(217, 95, 95, 0.12);
  border-color: rgba(217, 95, 95, 0.5);
  padding: 5px 20px;
}

.wp-label {
  font-size: 13px;
  color: var(--you);
  letter-spacing: 2px;
}

.word-plate.spy .wp-label {
  color: var(--spy);
}

.wp-word {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 4px;
  color: var(--accent-soft);
  text-shadow: 0 2px 12px rgba(232, 168, 82, 0.3);
}

.word-plate.spy .wp-word {
  font-size: 20px;
  color: var(--spy);
  text-shadow: none;
}

.overlay-banner {
  position: absolute;
  top: 52px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  background: rgba(106, 169, 217, 0.15);
  border: 1px solid rgba(106, 169, 217, 0.35);
  color: var(--info);
  font-size: 13px;
  border-radius: 999px;
  padding: 6px 18px;
  white-space: nowrap;
  max-width: calc(100% - 24px);
  text-overflow: ellipsis;
  overflow: hidden;
}

.overlay-banner.warn {
  background: rgba(232, 168, 82, 0.15);
  border-color: rgba(232, 168, 82, 0.4);
  color: var(--accent-soft);
}

.overlay-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}

.overlay-card {
  width: min(420px, calc(100% - 32px));
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  text-align: center;
}

.err {
  font-size: 13px;
  color: var(--danger);
  margin: 12px 0 18px;
  word-break: break-all;
}

.btns {
  display: flex;
  gap: 10px;
}

.btns .btn {
  flex: 1;
}

.finished-bar {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 8px 12px 8px 20px;
  font-size: 13px;
  color: var(--text-dim);
  box-shadow: var(--shadow-md);
}

.small {
  padding: 6px 16px;
  font-size: 13px;
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
