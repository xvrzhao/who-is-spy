// 与后端契约一一对应：
//   事件 payload ↔ src/game/events.py（pydantic model_dump(mode="json")）
//   status 响应 ↔ src/domains/game/endpoints.py 白名单字段

export type PlayerId = number
export type Identity = 'civilian' | 'spy'

export type InterruptType =
  | 'need_statement'
  | 'need_vote'
  | 'need_exchange'
  | 'speech_playback_done'

export type EventName =
  | 'game_started'
  | 'init_start'
  | 'init_end'
  | 'statement_start'
  | 'statement_player_start'
  | 'statement_player_end'
  | 'statement_end'
  | 'vote_start'
  | 'vote_player_start'
  | 'vote_player_end'
  | 'vote_end'
  | 'game_over'
  | 'exchange_session_start'
  | 'exchange_session_player_start'
  | 'exchange_session_player_end'
  | 'exchange_session_end'
  | 'player_speech'
  | 'interrupt'
  | 'finished'
  | 'error'

export interface SseFrame {
  event: EventName
  payload: any
}

// —— 各事件 payload ——

export interface PGameStarted {
  game_id: string
  player_total: number
}

export interface PInitEnd {
  real_player_id: PlayerId
  real_player_word: string
}

export interface PRoundEvent {
  game_round: number
}

export interface PPlayerEvent {
  player_id: PlayerId
}

export interface PStatementPlayerEnd {
  player_id: PlayerId
  statement: string
}

export interface PVoteEnd {
  game_round: number
  vote_collect: Record<string, PlayerId[]> // 被投人ID -> 投票人ID列表（JSON 对象键必为字符串）
  abstain_voters: PlayerId[]
  eliminated_player: PlayerId | null
  eliminated_player_identity: Identity | null
  present_players: PlayerId[]
}

export interface PGameOver {
  winner: Identity
  real_player_identity: Identity
  is_real_player_win: boolean
  real_player_id: PlayerId
  spy_id: PlayerId
  word_spy: string
  word_civilian: string
}

export interface PExchangePlayerEnd {
  player_id: PlayerId
  content: string
  next_player_id: PlayerId
}

export interface PPlayerSpeech {
  player_id: PlayerId
  text: string
  audio_base64: string // '' = TTS 降级，无音频
  audio_format: 'mp3'
  audio_length_ms: number
}

export interface PInterrupt {
  interrupt: InterruptType
}

export interface PError {
  type: string
  message: string
}

// —— status 端点 ——

export type RunStatus = 'running' | 'waiting_input' | 'continuable' | 'finished'

export interface StatusResponse {
  game_id: string
  status: RunStatus
  interrupt: PInterrupt | null
  state: {
    player_total: number
    real_player_id: PlayerId
    game_round: number
    stage: 'statement' | 'voting' // 注意：交流阶段后端不改 stage，此字段在交流期不可信
    present_players: PlayerId[]
    winner: Identity | null
  } | null
}

// —— 时间线消息（渲染与断线去重的统一载体，key 全局唯一） ——

export type TimelineMsg =
  | { key: string; kind: 'statement'; round: number; playerId: PlayerId; text: string; mine: boolean }
  | { key: string; kind: 'exchange'; playerId: PlayerId; text: string; nextPlayerId?: PlayerId }
  | { key: string; kind: 'system'; text: string }
  | { key: string; kind: 'vote-result'; round: number; collect: Record<string, PlayerId[]>; abstain: PlayerId[] }
  | { key: string; kind: 'elimination'; round: number; playerId: PlayerId; identity: Identity }
  | { key: string; kind: 'reveal'; data: PGameOver }

// —— 持久化快照 ——

export interface GameSnapshot {
  version: 1
  phase: 'playing' | 'gameover' | 'exchange' | 'finished'
  gameId: string
  playerTotal: number
  realPlayerId: PlayerId | null
  myWord: string | null
  gameRound: number
  stage: 'statement' | 'voting' | 'exchange'
  presentPlayers: PlayerId[]
  statementCursor: number
  eliminated: Record<number, { round: number; identity: Identity }>
  reveal: PGameOver | null
  exchangeNext: PlayerId | null
  exchangeCount: number
  messages: TimelineMsg[]
  savedAt: number
}
