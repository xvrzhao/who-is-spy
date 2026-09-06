<script setup lang="ts">
import { computed } from 'vue'

import { useGameStore } from '@/stores/game'

const store = useGameStore()

const show = computed(
  () => store.myWord !== null && !store.wordRevealed && store.phase === 'playing',
)
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="mask">
      <div class="card">
        <div class="label">本局你拿到的词是</div>
        <div class="word">{{ store.myWord }}</div>
        <p class="hint">别直接说出这个词——用描述让大家相信你是平民，同时找出和你词不一样的人</p>
        <button class="btn btn-primary" @click="store.dismissWordPopup()">记住了，开始</button>
        <div class="mini">之后词会一直显示在圆桌下方</div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 45;
}

.card {
  width: min(420px, calc(100% - 32px));
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 32px 28px 24px;
  text-align: center;
  animation: rise 0.35s var(--ease-out);
}

@keyframes rise {
  from {
    transform: translateY(24px) scale(0.94);
    opacity: 0;
  }
}

.label {
  font-size: 14px;
  color: var(--text-dim);
  letter-spacing: 2px;
  margin-bottom: 12px;
}

.word {
  font-size: 44px;
  font-weight: 800;
  letter-spacing: 6px;
  color: var(--accent-soft);
  text-shadow: 0 4px 24px rgba(232, 168, 82, 0.35);
  margin-bottom: 14px;
}

.hint {
  font-size: 13px;
  color: var(--text-faint);
  margin-bottom: 22px;
}

.btn {
  width: 100%;
}

.mini {
  margin-top: 12px;
  font-size: 11px;
  color: var(--text-faint);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
