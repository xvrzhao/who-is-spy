<script setup lang="ts">
import { useGameStore } from '@/stores/game'
import LobbyView from '@/components/LobbyView.vue'
import GameView from '@/components/GameView.vue'

const store = useGameStore()
</script>

<template>
  <LobbyView v-if="store.phase === 'lobby'" />
  <GameView v-else />
</template>
