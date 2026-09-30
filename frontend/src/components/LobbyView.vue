<script setup lang="ts">
import { ref } from 'vue'

import { useGameStore } from '@/stores/game'

const store = useGameStore()
const playerTotal = ref(6)
const TOTAL_CHOICES = [4, 6]

function start(): void {
  store.startGame(playerTotal.value)
}
</script>

<template>
  <div class="lobby">
    <div class="lobby-card">
      <div class="logo">🕵️</div>
      <h1>谁是卧底</h1>
      <p class="tagline">你和一桌 AI 玩「谁是卧底」——描述你的词，找出那个词不一样的人</p>

      <div class="field">
        <label>本局人数（含你，其余为 AI 玩家）</label>
        <div class="picker">
          <button
            v-for="n in TOTAL_CHOICES"
            :key="n"
            class="pick"
            :class="{ active: playerTotal === n }"
            @click="playerTotal = n"
          >
            {{ n }} 人
          </button>
        </div>
      </div>

      <button class="btn btn-primary start" :disabled="store.connStatus === 'starting'" @click="start">
        {{ store.connStatus === 'starting' ? '开局中…' : '开始游戏' }}
      </button>
      <p class="hint">开局即代表一轮完整对局：轮流发言 → 投票 → 淘汰，直到揪出卧底或卧底存活到最后</p>
    </div>
  </div>
</template>

<style scoped>
.lobby {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.lobby-card {
  width: min(440px, 100%);
  background: var(--panel);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 36px 32px;
  text-align: center;
}

.logo {
  font-size: 56px;
  margin-bottom: 8px;
}

h1 {
  font-size: 26px;
  letter-spacing: 4px;
  margin-bottom: 8px;
}

.tagline {
  color: var(--text-dim);
  font-size: 14px;
  margin-bottom: 28px;
}

.field {
  text-align: left;
  margin-bottom: 24px;
}

.field label {
  display: block;
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 10px;
}

.picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pick {
  flex: 1;
  min-width: 64px;
  padding: 10px 0;
  border-radius: var(--radius-md);
  background: var(--panel-soft);
  border: 1px solid var(--border);
  color: var(--text-dim);
  transition: all 0.15s var(--ease-out);
}

.pick.active {
  background: linear-gradient(160deg, var(--accent-soft), var(--accent));
  border-color: transparent;
  color: #3d2b12;
  font-weight: 700;
}

.start {
  width: 100%;
  font-size: 17px;
  padding: 13px;
}

.hint {
  margin-top: 16px;
  font-size: 12px;
  color: var(--text-faint);
}
</style>
