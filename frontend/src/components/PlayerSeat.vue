<script setup lang="ts">
import { computed } from 'vue'

import type { PlayerId } from '@/api/types'
import { playerColor, playerName } from '@/utils/players'
import { useGameStore } from '@/stores/game'
import PlayerAvatar from './PlayerAvatar.vue'

const props = defineProps<{ playerId: PlayerId }>()
const store = useGameStore()

const isMe = computed(() => store.realPlayerId === props.playerId)
const isOut = computed(() => store.eliminated[props.playerId] != null)
const isSpeaking = computed(() => store.activeSpeakerId === props.playerId && !isOut.value)
const isAudioPlaying = computed(() => store.audioPlayingId === props.playerId)

// 思考中气泡：轮到此人但语音未到（或真人待输入）
const isThinking = computed(
  () =>
    isSpeaking.value &&
    !isAudioPlaying.value &&
    !(store.lastSpeech?.playerId === props.playerId && !store.lastSpeech.hasAudio),
)

// TTS 降级兜底：无音频时显示文字（正常情况只播语音不显示文字）
const degradedText = computed(() => {
  if (!isSpeaking.value || isAudioPlaying.value) return null
  const s = store.lastSpeech
  return s && s.playerId === props.playerId && !s.hasAudio ? s.text : null
})

const hasVoted = computed(() => store.stage === 'voting' && store.votedIds.includes(props.playerId))
const isVotingNow = computed(
  () => store.stage === 'voting' && store.votingNow.includes(props.playerId),
)

// 身份揭示：game_over 后全场公开；已淘汰者身份在 vote_end 已公布
const identity = computed(() => {
  if (store.reveal) return store.reveal.spy_id === props.playerId ? 'spy' : 'civilian'
  return store.eliminated[props.playerId]?.identity ?? null
})

// 投票结果：投给我的人（vote_end 后、下一轮发言前显示）
const voters = computed<PlayerId[]>(() => {
  const vote = store.lastVote
  if (!vote || store.stage !== 'voting') return []
  if (store.phase === 'gameover' || store.phase === 'exchange' || store.phase === 'finished') return []
  return vote.collect[String(props.playerId)] ?? []
})
const iAbstained = computed(() => {
  const vote = store.lastVote
  return !!vote && vote.abstain.includes(props.playerId)
})
</script>

<template>
  <div class="seat-unit" :class="{ out: isOut, me: isMe }">
    <!-- 正在播语音：气泡 + 麦克风 -->
    <div v-if="isAudioPlaying" class="bubble mic-bubble">
      <span class="mic">🎤</span>
    </div>
    <!-- 思考中气泡 -->
    <div v-else-if="isThinking" class="bubble empty">
      <span class="dots"><i /><i /><i /></span>
    </div>
    <!-- TTS 降级兜底：文字气泡 -->
    <div v-else-if="degradedText" class="bubble">{{ degradedText }}</div>

    <div class="avatar-ring" :class="{ speaking: isSpeaking }">
      <div class="avatar" :style="{ borderColor: playerColor(playerId) }">
        <PlayerAvatar :id="playerId" />
      </div>
      <span v-if="isMe" class="badge-you">你</span>
      <span class="badge-id">{{ playerId }}</span>
      <span v-if="hasVoted" class="badge-voted" title="已投票">✓</span>
    </div>

    <div class="name">
      {{ playerName(playerId, store.realPlayerId) }}
      <span v-if="isVotingNow" class="voting-dots">…</span>
    </div>

    <!-- 身份 -->
    <div v-if="isOut || identity" class="identity" :class="identity">
      <template v-if="identity === 'spy'">卧底</template>
      <template v-else-if="identity === 'civilian'">平民</template>
      <template v-else>出局</template>
    </div>

    <!-- 投给我的票：投票者号码 -->
    <div v-if="voters.length > 0" class="votes">
      <span
        v-for="v in voters"
        :key="v"
        class="vote-chip"
        :style="{ background: playerColor(v) }"
        :title="`${v}号 投了 ${playerId}号`"
      >
        {{ v }}
      </span>
    </div>
    <div v-else-if="iAbstained" class="votes abstain-tag">弃票</div>
  </div>
</template>

<style scoped>
.seat-unit {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  width: 88px;
}

.avatar-ring {
  position: relative;
  padding: 3px;
  border-radius: 50%;
}

/* 轮到该玩家：仅头像外的圆环淡出淡入呼吸，头像本体不闪烁 */
.avatar-ring.speaking::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 3.5px solid var(--accent);
  box-shadow: 0 0 16px rgba(232, 168, 82, 0.65);
  animation: ring-breathe 1.4s ease-in-out infinite;
  pointer-events: none;
}

@keyframes ring-breathe {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

.avatar {
  width: var(--seat-size);
  height: var(--seat-size);
  border-radius: 50%;
  background: var(--panel-soft);
  border: 2px solid;
  overflow: hidden;
}

.badge-you {
  position: absolute;
  top: -7px;
  right: -18px;
  font-size: 13px;
  background: var(--you);
  color: #14351c;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 9px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  z-index: 2;
}

/* ID 徽章：挂在头像下方（不遮挡头像），浅底高对比 */
.badge-id {
  position: absolute;
  bottom: -14px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 14px;
  font-weight: 700;
  background: #efe9dc;
  border: 1px solid rgba(0, 0, 0, 0.35);
  color: #2a2724;
  border-radius: 999px;
  padding: 0 9px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  z-index: 2;
}

.badge-voted {
  position: absolute;
  top: -4px;
  left: -12px;
  font-size: 11px;
  background: var(--info);
  color: #10293c;
  font-weight: 700;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.name {
  margin-top: 15px; /* 给挂在头像下方的 ID 徽章留出空间，避免遮住昵称 */
  font-size: 12px;
  color: var(--text-dim);
  white-space: nowrap;
}

.voting-dots {
  color: var(--accent-soft);
}

/* 麦克风 */
.mic {
  display: inline-block;
  font-size: 22px;
  animation: mic-pulse 1s ease-in-out infinite;
}

@keyframes mic-pulse {
  50% {
    transform: scale(1.18);
  }
}

/* 头顶气泡（麦克风 / 思考中 / TTS 降级文字） */
.bubble {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 150px;
  max-width: 24vw;
  background: #f7f3ea;
  color: #33302e;
  font-size: 12px;
  line-height: 1.45;
  padding: 7px 10px;
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  z-index: 5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-align: left;
}

/* 麦克风气泡：紧凑、内容居中（需在 .bubble 之后覆盖宽度和 display） */
.bubble.mic-bubble {
  width: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px 12px;
}

.bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #f7f3ea;
}

.bubble.empty {
  width: auto;
  padding: 6px 10px;
}

.dots {
  display: inline-flex;
  gap: 4px;
}

.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #8a8177;
  animation: pulse 1s ease-in-out infinite;
}

.dots i:nth-child(2) {
  animation-delay: 0.18s;
}

.dots i:nth-child(3) {
  animation-delay: 0.36s;
}

@keyframes pulse {
  50% {
    opacity: 0.25;
  }
}

.identity {
  font-size: 10px;
  padding: 0 8px;
  border-radius: 999px;
  font-weight: 600;
}

.identity.spy {
  background: rgba(217, 95, 95, 0.2);
  color: var(--spy);
}

.identity.civilian {
  background: rgba(108, 191, 158, 0.18);
  color: var(--civilian);
}

/* 投票者号码徽章 */
.votes {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 92px;
}

.vote-chip {
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 999px;
  color: #241d14;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}

.abstain-tag {
  font-size: 10px;
  color: var(--text-faint);
}

.out :is(.avatar, .name) {
  filter: grayscale(1);
  opacity: 0.45;
}
</style>
