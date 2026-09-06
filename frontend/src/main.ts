import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { useGameStore } from './stores/game'
import './styles/variables.css'
import './styles/base.css'

const app = createApp(App)
app.use(createPinia())

// 恢复未完成的对局（有 current 指针时查 status 重连）
void useGameStore().bootstrap()

app.mount('#app')
