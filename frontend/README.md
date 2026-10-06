# 游戏前端

> 声明：前端代码完全由 Coding Agent 生成，未经作者 Review，此文档亦是，故前端代码作者不做任何解释。

「谁是卧底」AI 对战游戏前端：Vue 3 + Vite + TypeScript + Pinia，拟真圆桌 + 聊天时间线，Agent 语音自动连播（speech gate 同步）。

## 运行

```bash
cd frontend
npm install

# 1) 连真实后端（默认）：先起后端
#    docker compose up -d postgres && cd backend && uvicorn src.main:app --port 8000
npm run dev            # → http://localhost:5173（/api/* 经 vite proxy 到 8000，后端路由挂在 /api 前缀下）

# 2) mock 模式（无需后端 / LLM key）
VITE_USE_MOCK=1 npm run dev
# 或已在跑的页面里执行：localStorage.setItem('wis:mock:force','1') 后刷新
```

## mock 调试开关（localStorage）

| key | 取值 | 说明 |
| --- | --- | --- |
| `wis:mock:force` | `'1'` | 强制 mock 模式（免改 .env 重启） |
| `wis:mock:scenario` | `standard` / `tie` / `ttsFail` / `spyWin` | 剧本：标准局 / 平票轮 / TTS 全降级 / 卧底胜 |
| `wis:mock:speed` | 如 `'0.1'` | 延迟倍速（加速跑局） |

## 结构

```
src/
├── api/        # types（后端契约）、transport（POST SSE 流式解析）、game（API）、mock/（剧本驱动）
├── stores/     # game.ts：全事件 reducer + interrupt 状态机
├── audio/      # unlock（手势解锁）、speech-queue（串行播放 + speech gate 协调）
├── components/ # LobbyView / GameView / RoundTable / PlayerSeat / ChatTimeline / InputBar / VotePanel …
└── utils/      # players（昵称/头像）、storage（localStorage 快照留档）、misc
```

## 关键机制（与后端契约对应）

- **SSE 为 POST**：`EventSource` 不可用，`api/transport.ts` 用 fetch 流式读取自行分帧（event 名在 `event:` 行，`data:` 行 JSON 即 payload）
- **speech gate**：每个 Agent 发言后必发 `player_speech` + `speech_playback_done` interrupt；前端播放完音频才 `resume(true)`（静音/TTS 降级立即确认）
- **真人无回执**：发言/投票提交后本地回显；交流发言等后端 `exchange_session_player_end`
- **无断线恢复**：后端 resume 必填且不支持断点续跑，连接中断/刷新即本局作废；对局快照仅写 localStorage 留档
- **输入约束**：发言过滤半角 `|`（`need_exchange` 以 `||` 分隔，会被后端 422）

## 其他命令

```bash
npm run build     # vue-tsc 类型检查 + 产物构建
npm run preview   # 预览构建产物
```
