<script setup lang="ts">
// 阶段切换提示：进入发言/投票/赛后交流时顶部居中短暂弹条（约 2.2s，不挡操作）。
// 开局词弹框未关闭时先压住不显示（会被遮罩盖住浪费掉），关闭后再弹出。
import { ref, watch } from 'vue'

import { useGameStore } from '@/stores/game'

const store = useGameStore()

const visible = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null
let shownId = 0

function clearTimer(): void {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

function show(id: number): void {
  shownId = id
  visible.value = true
  clearTimer()
  timer = setTimeout(() => (visible.value = false), 2200)
}

watch(
  () => store.stageToast,
  (toast) => {
    if (!toast || toast.id === shownId) return
    if (!store.wordRevealed && store.phase === 'playing') return // 等词弹框关闭
    show(toast.id)
  },
)

// 词弹框关闭后，补显被压住的提示
watch(
  () => store.wordRevealed,
  (revealed) => {
    const toast = store.stageToast
    if (revealed && toast && toast.id !== shownId) show(toast.id)
  },
)
</script>

<template>
  <Transition name="toast">
    <div v-if="visible && store.stageToast" class="stage-toast">
      <span class="stage-text">{{ store.stageToast.text }}</span>
    </div>
  </Transition>
</template>

<style scoped>
.stage-toast {
  position: absolute;
  top: 54px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 28;
  pointer-events: none;
  background: rgba(28, 26, 24, 0.9);
  border: 1.5px solid var(--accent);
  border-radius: 999px;
  padding: 9px 30px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
}

.stage-text {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 3px;
  color: var(--accent-soft);
}

.toast-enter-active {
  transition: all 0.3s var(--ease-out);
}

.toast-leave-active {
  transition: all 0.35s ease-in;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>
