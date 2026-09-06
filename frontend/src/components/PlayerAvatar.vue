<script setup lang="ts">
// 圆形头像：真人固定 real_player.png，AI 用 ID 对应图片；无图时兜底显示座位号
import { computed } from 'vue'

import type { PlayerId } from '@/api/types'
import { useGameStore } from '@/stores/game'
import { playerAvatar } from '@/utils/players'

const props = defineProps<{ id: PlayerId }>()
const store = useGameStore()

const url = computed(() => playerAvatar(props.id, store.realPlayerId))
</script>

<template>
  <img v-if="url" class="p-avatar" :src="url" :alt="String(id)" />
  <span v-else class="p-avatar p-avatar-fallback">{{ id }}</span>
</template>

<style scoped>
.p-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.p-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-dim);
}
</style>
