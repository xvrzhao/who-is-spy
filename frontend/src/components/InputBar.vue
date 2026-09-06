<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { useGameStore } from '@/stores/game'
import { playerName } from '@/utils/players'
import PlayerAvatar from './PlayerAvatar.vue'

const store = useGameStore()

const MAX_LEN = 120
const SOFT_LEN = 100

const text = ref('')
const nextPick = ref<number | null>(null)
const textareaEl = ref<HTMLTextAreaElement | null>(null)

const isStatement = computed(() => store.pendingInterrupt === 'need_statement')
const isExchange = computed(() => store.pendingInterrupt === 'need_exchange')
const active = computed(() => isStatement.value || isExchange.value)

// 预览态：快轮到我了但 interrupt 未到（isMyTurnStatement）
const previewStatement = computed(
  () => !active.value && store.isMyTurnStatement && store.phase === 'playing',
)

// 交流点名候选：全量玩家（含已淘汰，复活聊天）排除自己
const exchangeCandidates = computed(() => store.allPlayerIds.filter((id) => id !== store.realPlayerId))

const overLen = computed(() => text.value.length > SOFT_LEN)
const canSend = computed(() => {
  if (!active.value) return false
  if (!text.value.trim()) return false
  if (isExchange.value && nextPick.value === null) return false
  return true
})

// interrupt 激活时聚焦输入框
watch(active, (v) => {
  if (v) {
    if (isExchange.value) nextPick.value = null
    void nextTick(() => textareaEl.value?.focus())
  }
})

function send(): void {
  if (!canSend.value || store.submitState === 'submitting') return
  if (isStatement.value) {
    store.submitStatement(text.value)
  } else if (isExchange.value && nextPick.value !== null) {
    store.submitExchange(text.value, nextPick.value)
  }
  text.value = ''
  nextPick.value = null
}

function onInput(e: Event): void {
  // 过滤半角 |（need_exchange 以 | 分隔，含 | 会被后端 422）
  text.value = (e.target as HTMLTextAreaElement).value.replace(/\|/g, '｜')
}

function onKeydown(e: KeyboardEvent): void {
  // 中文输入法组词中的 Enter 不发送
  if (e.isComposing) return
  send()
}
</script>

<template>
  <div v-if="active || previewStatement" class="input-bar" :class="{ preview: previewStatement }">
    <template v-if="isExchange">
      <div class="picker">
        <span class="picker-label">点名下一位：</span>
        <button
          v-for="id in exchangeCandidates"
          :key="id"
          class="pick"
          :class="{ picked: nextPick === id }"
          @click="nextPick = id"
        >
          <span class="pick-avatar"><PlayerAvatar :id="id" /></span>
          {{ playerName(id, store.realPlayerId) }}
        </button>
      </div>
    </template>

    <div class="row">
      <textarea
        ref="textareaEl"
        v-model="text"
        :disabled="!active"
        :maxlength="MAX_LEN"
        rows="2"
        :placeholder="isExchange ? '和大家聊聊这局…（会语音播报）' : '描述你的词，别太直白…'"
        @input="onInput"
        @keydown.enter.exact.prevent="onKeydown"
      />
      <button
        class="btn btn-primary send"
        :disabled="!canSend || store.submitState === 'submitting'"
        @click="send"
      >
        {{ store.submitState === 'submitting' ? '发送中' : '发送' }}
      </button>
    </div>

    <div class="meta-row">
      <span v-if="isExchange" class="tip">赛后交流：发言后点名下一位聊天的玩家</span>
      <span v-else class="tip">轮到你了，描述你的词（不要直接说出词本身）</span>
      <span class="count" :class="{ over: overLen }">{{ text.length }}/{{ SOFT_LEN }}</span>
    </div>
  </div>

  <div v-else class="input-bar idle-bar">
    <span v-if="store.phase === 'exchange'">
      赛后交流进行中{{ store.exchangeNext ? `，等 ${store.exchangeNext}号 发言…` : '…' }}
    </span>
    <span v-else-if="store.stage === 'voting'">
      投票进行中（{{ store.votedIds.length }}/{{ store.presentPlayers.length }} 已投）…
    </span>
    <span v-else>等待其他玩家发言…</span>
  </div>
</template>

<style scoped>
.input-bar {
  border-top: 1px solid var(--border-soft);
  background: var(--panel);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.idle-bar {
  font-size: 12.5px;
  color: var(--text-faint);
  text-align: center;
}

.preview :is(textarea) {
  opacity: 0.6;
}

.picker {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.picker-label {
  font-size: 12px;
  color: var(--text-dim);
}

.pick {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--panel-soft);
  border: 1px solid var(--border);
  color: var(--text-dim);
}

.pick-avatar {
  display: block;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  overflow: hidden;
  flex: none;
}

.pick.picked {
  background: rgba(232, 168, 82, 0.2);
  border-color: var(--accent);
  color: var(--accent-soft);
  font-weight: 600;
}

.row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

textarea {
  flex: 1;
  resize: none;
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 9px 12px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}

textarea:focus {
  border-color: var(--accent);
}

textarea:disabled {
  cursor: not-allowed;
}

.send {
  flex: none;
  padding: 10px 18px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--text-faint);
}

.count.over {
  color: var(--danger);
  font-weight: 700;
}
</style>
