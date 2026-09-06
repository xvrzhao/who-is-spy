// 游戏状态机：唯一 Pinia store。
// 全部 SSE 事件在此 reduce 成 UI 状态；resume 派发、gate 确认、断线重连、快照恢复也集中于此。
//
// 关键设计（与后端语义严格镜像）：
//  - statementCursor（本轮已发言数）唯一推进点 = speech gate 确认动作（confirmGate），
//    与后端 active_player_ptr 在 gate 后推进观测等价，不受 TTS 快慢影响
//  - 真人发言/投票无事件回执：提交后本地回显/本地标记；真人交流发言有回执，不本地回显
//  - 断线续跑会重放超步：所有时间线消息携带语义 key（round+pid/turn），append 前查重丢弃
//  - Agent 链路可 1-2 分钟无帧：不做无帧超时重连，只提示「AI 思考中」；网络错由 fetch 抛错兜底

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getStatus, resumeGame, startGame } from '@/api/game'
import { HttpError } from '@/api/transport'
import type {
  EventName,
  GameSnapshot,
  Identity,
  InterruptType,
  PError,
  PGameOver,
  PVoteEnd,
  PlayerId,
  SseFrame,
  TimelineMsg,
} from '@/api/types'
import { SpeechQueue, speechItemFromEvent } from '@/audio/speech-queue'
import { unlockAudio } from '@/audio/unlock'
import { throttleTrailing } from '@/utils/misc'
import { clearCurrent, loadCurrent, loadSnapshot, saveCurrent, saveSnapshot } from '@/utils/storage'

export type Phase = 'lobby' | 'playing' | 'gameover' | 'exchange' | 'finished'
export type ConnStatus = 'idle' | 'starting' | 'streaming' | 'reconnecting' | 'conflict' | 'error'

const RECONNECT_BACKOFFS = [1000, 2000, 5000, 10000]
const STATUS_POLL_MS = 3000

export const useGameStore = defineStore('game', () => {
  // ---- 状态 ----
  const connStatus = ref<ConnStatus>('idle')
  const phase = ref<Phase>('lobby')
  const gameId = ref<string | null>(null)
  const playerTotal = ref(0)
  const realPlayerId = ref<PlayerId | null>(null)
  const myWord = ref<string | null>(null)

  const gameRound = ref(0)
  const stage = ref<'statement' | 'voting' | 'exchange'>('statement')
  const presentPlayers = ref<PlayerId[]>([])
  const statementCursor = ref(0)
  const speakingPlayerId = ref<PlayerId | null>(null)

  const votedIds = ref<PlayerId[]>([])
  const votingNow = ref<PlayerId[]>([])
  const lastVote = ref<{ round: number; collect: Record<string, PlayerId[]>; abstain: PlayerId[] } | null>(null)
  const myLastVote = ref<number | null>(null)
  const eliminated = ref<Record<number, { round: number; identity: Identity }>>({})

  const reveal = ref<PGameOver | null>(null)
  const exchangeNext = ref<PlayerId | null>(null)
  const exchangeCount = ref(0)

  const messages = ref<TimelineMsg[]>([])

  const restorable = ref<{ gameId: string; playerTotal: number; gameRound: number } | null>(null)

  const audioPlayingId = ref<PlayerId | null>(null) // 正在播语音的玩家（座位麦克风标识）
  const lastSpeech = ref<{ playerId: PlayerId; text: string; hasAudio: boolean } | null>(null)
  const wordRevealed = ref(false) // 开局词弹框是否已关闭（之后词缩为底部大词牌）
  const roundPopupBusy = ref(false) // 轮内弹窗（投票结果/淘汰）播放中，终局弹窗等它结束
  const stageToast = ref<{ id: number; text: string } | null>(null) // 阶段切换提示（发言/投票/交流）
  let stageToastSeq = 0

  const pendingInterrupt = ref<InterruptType | null>(null)
  const submitState = ref<'idle' | 'submitting'>('idle')
  const muted = ref(false)
  const lastFrameAt = ref(0)
  const lastError = ref<PError | null>(null)

  // ---- 派生 ----
  const activeSpeakerId = computed<PlayerId | null>(() => {
    if (speakingPlayerId.value !== null) return speakingPlayerId.value
    if (stage.value === 'statement' && statementCursor.value < presentPlayers.value.length) {
      return presentPlayers.value[statementCursor.value]
    }
    // 交流：已知下一位点名对象时，生成期间省略号指向他
    if (stage.value === 'exchange' && exchangeNext.value !== null) return exchangeNext.value
    return null
  })

  /** 快轮到我了：预渲染禁用态输入框（interrupt 未到时） */
  const isMyTurnStatement = computed(
    () =>
      phase.value === 'playing' &&
      stage.value === 'statement' &&
      realPlayerId.value !== null &&
      presentPlayers.value[statementCursor.value] === realPlayerId.value,
  )

  const allPlayerIds = computed(() => Array.from({ length: playerTotal.value }, (_, i) => i + 1))

  // ---- 音频队列 ----
  const speech = new SpeechQueue()
  speech.onGateReady = () => confirmGate()
  speech.onPlayStart = (item) => {
    audioPlayingId.value = item.playerId
  }
  speech.onPlayEnd = () => {
    audioPlayingId.value = null
  }

  // ---- 连接管理（模块级单例资源，不放响应式 state）----
  let abortCtl: AbortController | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempt = 0
  let statusPollTimer: ReturnType<typeof setInterval> | null = null
  // 主动 abort 守卫：resume 换段会 abort 旧流，而 abort 常发生在「最后一帧已处理、done 尚未被
  // 读取」的窗口里——旧流的收尾若按断线处理会安排重连，重连定时器随后会杀死健康的新流，
  // 造成「反复重连+游戏停滞」。abortedSeq 记录被我方 abort 的流序号，其收尾视为正常换段。
  let streamSeq = 0
  let abortedSeq: number | null = null

  function abortStream(): void {
    if (abortCtl) {
      abortedSeq = streamSeq // 当前活跃流将被我方 abort
      abortCtl.abort()
      abortCtl = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (statusPollTimer) {
      clearInterval(statusPollTimer)
      statusPollTimer = null
    }
  }

  async function drive(iter: AsyncIterable<SseFrame>): Promise<void> {
    const mySeq = ++streamSeq
    connStatus.value = 'streaming'
    let err: unknown = null
    try {
      for await (const frame of iter) {
        lastFrameAt.value = Date.now()
        reconnectAttempt = 0
        applyFrame(frame)
      }
    } catch (e) {
      err = e
    }

    const intentional = abortedSeq !== null && mySeq <= abortedSeq
    const st = connStatus.value as ConnStatus // applyFrame 可能已改值，避免 TS 窄化误判
    if (intentional) {
      // 我方主动换段：新流由 resume/start 开启，旧流收尾不触发重连、不覆盖连接状态
    } else if (err instanceof Error && !(err instanceof DOMException && err.name === 'AbortError')) {
      handleConnError(err)
    } else if (phase.value !== 'finished' && !pendingInterrupt.value && st !== 'error' && st !== 'conflict') {
      // 流自然结束且无挂起 interrupt = 正常段尾之外的情形，视为中途断线
      scheduleReconnect()
    } else if (st === 'streaming') {
      connStatus.value = 'idle'
    }
    persistNow()
  }

  function resume(value: unknown): void {
    if (!gameId.value || phase.value === 'finished') return
    abortStream()
    pendingInterrupt.value = null
    abortCtl = new AbortController()
    void drive(resumeGame(gameId.value, value, abortCtl.signal))
  }

  function scheduleReconnect(): void {
    if (reconnectTimer) return
    const delay = RECONNECT_BACKOFFS[Math.min(reconnectAttempt, RECONNECT_BACKOFFS.length - 1)]
    reconnectAttempt += 1
    connStatus.value = 'reconnecting'
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      resume(undefined) // 省略 resume：有 interrupt 幂等重发，无则从断点续跑
    }, delay)
  }

  function handleConnError(err: Error): void {
    if (err instanceof DOMException && err.name === 'AbortError') return // 主动 abort，忽略
    if (err instanceof HttpError) {
      if (err.status === 404) {
        // 未知局：清库回大厅
        leaveGame()
        return
      }
      if (err.status === 409) {
        // 另一 run 活跃（旧标签页等）：轮询 status，等它让位
        startConflictPolling()
        return
      }
      if (err.status >= 400 && err.status < 500) {
        // 4xx（如 422 校验失败）：请求被拒，重试同样的请求只会死循环；
        // interrupt 仍挂起在后端，转为错误提示，用户可「从断点继续」重新取回现场
        lastError.value = { type: `HTTP ${err.status}`, message: err.bodyText.slice(0, 200) }
        connStatus.value = 'error'
        return
      }
    }
    if (phase.value !== 'finished' && phase.value !== 'lobby') scheduleReconnect()
  }

  function startConflictPolling(): void {
    if (statusPollTimer) return
    connStatus.value = 'conflict'
    statusPollTimer = setInterval(() => {
      void getStatus(gameId.value!)
        .then((st) => {
          if (st.status === 'finished') {
            stopConflictPolling()
            phase.value = 'finished'
            connStatus.value = 'idle'
          } else if (st.status !== 'running') {
            stopConflictPolling()
            resume(undefined)
          }
        })
        .catch(() => {
          stopConflictPolling()
          scheduleReconnect()
        })
    }, STATUS_POLL_MS)
  }

  function stopConflictPolling(): void {
    if (statusPollTimer) {
      clearInterval(statusPollTimer)
      statusPollTimer = null
    }
  }

  // ---- 事件 reducer ----
  function appendMsg(msg: TimelineMsg): void {
    // 语义 key 去重：断线续跑会重放超步，重复帧直接丢弃
    if (messages.value.some((m) => m.key === msg.key)) return
    messages.value.push(msg)
  }

  const systemMsg = (key: string, text: string): TimelineMsg => ({ key, kind: 'system', text })

  function applyFrame(frame: SseFrame): void {
    const p = frame.payload
    switch (frame.event as EventName) {
      case 'game_started': {
        gameId.value = p.game_id as string
        playerTotal.value = p.player_total as number
        phase.value = 'playing'
        saveCurrent(gameId.value, playerTotal.value)
        break
      }
      case 'init_end': {
        realPlayerId.value = p.real_player_id
        myWord.value = p.real_player_word
        presentPlayers.value = Array.from({ length: playerTotal.value }, (_, i) => i + 1)
        statementCursor.value = 0
        break
      }
      case 'statement_start': {
        gameRound.value = p.game_round
        stage.value = 'statement'
        statementCursor.value = 0
        votedIds.value = []
        votingNow.value = []
        lastVote.value = null
        myLastVote.value = null
        speakingPlayerId.value = null
        stageToast.value = { id: ++stageToastSeq, text: `第 ${p.game_round} 轮 · 发言阶段` }
        appendMsg(systemMsg(`sst:${p.game_round}`, `—— 第 ${p.game_round} 轮发言 ——`))
        break
      }
      case 'statement_player_start': {
        speakingPlayerId.value = p.player_id
        break
      }
      case 'statement_player_end': {
        appendMsg({
          key: `st:${gameRound.value}:${p.player_id}`,
          kind: 'statement',
          round: gameRound.value,
          playerId: p.player_id,
          text: p.statement,
          mine: false,
        })
        break
      }
      case 'statement_end': {
        stage.value = 'voting'
        speakingPlayerId.value = null
        appendMsg(systemMsg(`sen:${p.game_round}`, `第 ${p.game_round} 轮发言结束，进入投票`))
        break
      }
      case 'vote_start': {
        votedIds.value = []
        votingNow.value = []
        stageToast.value = { id: ++stageToastSeq, text: `第 ${p.game_round} 轮 · 投票阶段` }
        appendMsg(systemMsg(`vst:${p.game_round}`, `—— 第 ${p.game_round} 轮投票 ——`))
        break
      }
      case 'vote_player_start': {
        if (!votingNow.value.includes(p.player_id)) votingNow.value.push(p.player_id)
        break
      }
      case 'vote_player_end': {
        votingNow.value = votingNow.value.filter((id) => id !== p.player_id)
        if (!votedIds.value.includes(p.player_id)) votedIds.value.push(p.player_id)
        break
      }
      case 'vote_end': {
        applyVoteEnd(p as PVoteEnd)
        break
      }
      case 'game_over': {
        phase.value = 'gameover'
        reveal.value = p
        speakingPlayerId.value = null
        appendMsg({ key: 'reveal', kind: 'reveal', data: p })
        persistNow()
        break
      }
      case 'exchange_session_start': {
        phase.value = 'exchange'
        stage.value = 'exchange'
        exchangeCount.value = 0
        speakingPlayerId.value = null
        stageToast.value = { id: ++stageToastSeq, text: '赛后交流' }
        appendMsg(systemMsg('exs', '游戏结束，进入赛后交流'))
        break
      }
      case 'exchange_session_player_start': {
        speakingPlayerId.value = p.player_id
        exchangeNext.value = p.player_id
        break
      }
      case 'exchange_session_player_end': {
        appendMsg({
          key: `ex:${exchangeCount.value}`,
          kind: 'exchange',
          playerId: p.player_id,
          text: p.content,
          nextPlayerId: p.next_player_id,
        })
        exchangeCount.value += 1
        exchangeNext.value = p.next_player_id
        if (realPlayerId.value !== null && p.player_id === realPlayerId.value) {
          submitState.value = 'idle' // 真人交流回执到达
        }
        break
      }
      case 'exchange_session_end': {
        appendMsg(systemMsg('exe', '交流结束'))
        break
      }
      case 'player_speech': {
        lastSpeech.value = {
          playerId: p.player_id as PlayerId,
          text: p.text as string,
          hasAudio: Boolean(p.audio_base64),
        }
        speech.muted = muted.value
        speech.enqueue(speechItemFromEvent(p))
        break
      }
      case 'interrupt': {
        onInterrupt((p as { interrupt: InterruptType }).interrupt)
        break
      }
      case 'finished': {
        phase.value = 'finished'
        connStatus.value = 'idle'
        abortStream()
        speech.clearAndFlush()
        clearCurrent() // 快照保留供回看
        break
      }
      case 'error': {
        lastError.value = p
        connStatus.value = 'error'
        break
      }
      case 'init_start':
      default:
        break
    }
    persist() // 节流落盘；中断/结束等关键点由 persistNow 立即写
  }

  function applyVoteEnd(p: PVoteEnd): void {
    lastVote.value = { round: p.game_round, collect: p.vote_collect, abstain: p.abstain_voters }
    appendMsg({
      key: `ve:${p.game_round}`,
      kind: 'vote-result',
      round: p.game_round,
      collect: p.vote_collect,
      abstain: p.abstain_voters,
    })
    if (p.eliminated_player != null && p.eliminated_player_identity != null) {
      eliminated.value[p.eliminated_player] = {
        round: p.game_round,
        identity: p.eliminated_player_identity,
      }
      appendMsg({
        key: `el:${p.eliminated_player}`,
        kind: 'elimination',
        round: p.game_round,
        playerId: p.eliminated_player,
        identity: p.eliminated_player_identity,
      })
    }
    // 在场列表以 vote_end 为权威（覆盖写，天然幂等）
    presentPlayers.value = p.present_players.slice()
    gameRound.value = p.game_round
    votingNow.value = []
  }

  // ---- interrupt 处理（状态机核心） ----
  function onInterrupt(type: InterruptType): void {
    pendingInterrupt.value = type
    submitState.value = 'idle'
    persistNow()

    switch (type) {
      case 'need_statement':
      case 'need_exchange':
        speakingPlayerId.value = realPlayerId.value
        break
      case 'need_vote':
        speakingPlayerId.value = null
        break
      case 'speech_playback_done':
        if (muted.value || speech.idle) confirmGate()
        else speech.armGate()
        break
    }
  }

  function confirmGate(): void {
    if (pendingInterrupt.value !== 'speech_playback_done') return
    pendingInterrupt.value = null
    speech.disarmGate()
    // 清掉上一个发言者，省略号立即落到「正在生成的下一位」而不是滞留在旧座位
    speakingPlayerId.value = null
    if (stage.value === 'statement') statementCursor.value += 1 // 游标唯一推进点
    resume(true)
  }

  // ---- 本地动作 ----
  function startGameAction(total: number): void {
    unlockAudio() // 用户手势内解锁自动播放
    abortStream()
    speech.clearAndFlush()
    resetState()
    phase.value = 'playing'
    connStatus.value = 'starting'
    abortCtl = new AbortController()
    const ctl = abortCtl
    void drive(startGame(total, ctl.signal))
  }

  function resetState(): void {
    gameId.value = null
    playerTotal.value = 0
    realPlayerId.value = null
    myWord.value = null
    gameRound.value = 0
    stage.value = 'statement'
    presentPlayers.value = []
    statementCursor.value = 0
    speakingPlayerId.value = null
    votedIds.value = []
    votingNow.value = []
    lastVote.value = null
    myLastVote.value = null
    eliminated.value = {}
    reveal.value = null
    exchangeNext.value = null
    exchangeCount.value = 0
    messages.value = []
    restorable.value = null
    audioPlayingId.value = null
    lastSpeech.value = null
    wordRevealed.value = false
    pendingInterrupt.value = null
    submitState.value = 'idle'
    lastError.value = null
    reconnectAttempt = 0
  }

  function leaveGame(): void {
    abortStream()
    speech.clearAndFlush()
    clearCurrent()
    resetState()
    phase.value = 'lobby'
    connStatus.value = 'idle'
  }

  /** 真人发言（无后端回执，本地回显） */
  function submitStatement(textRaw: string): void {
    if (pendingInterrupt.value !== 'need_statement' || !realPlayerId.value) return
    const text = sanitizeInput(textRaw)
    if (!text) return
    appendMsg({
      key: `st:${gameRound.value}:${realPlayerId.value}`,
      kind: 'statement',
      round: gameRound.value,
      playerId: realPlayerId.value,
      text,
      mine: true,
    })
    submitState.value = 'submitting'
    speakingPlayerId.value = null // 省略号转到正在生成的下一位
    resume(text)
  }

  function submitVote(target: number): void {
    if (pendingInterrupt.value !== 'need_vote' || realPlayerId.value === null) return
    myLastVote.value = target
    if (!votedIds.value.includes(realPlayerId.value)) votedIds.value.push(realPlayerId.value)
    submitState.value = 'submitting'
    resume(target)
  }

  /** 赛后交流（有后端回执，不本地回显） */
  function submitExchange(textRaw: string, nextId: number): void {
    if (pendingInterrupt.value !== 'need_exchange') return
    const text = sanitizeInput(textRaw)
    if (!text) return
    submitState.value = 'submitting'
    speakingPlayerId.value = null
    exchangeNext.value = nextId // 省略号落到我点名的下一位
    resume(`${text}|${nextId}`)
  }

  function toggleMute(): void {
    muted.value = !muted.value
    speech.muted = muted.value
    if (muted.value) {
      // 切静音：清空播放；若 gate 已 arm 立即确认（clearAndFlush 内触发 onGateReady）
      speech.clearAndFlush()
    }
  }

  function retryAfterError(): void {
    lastError.value = null
    connStatus.value = 'idle'
    resume(undefined)
  }

  // ---- 快照持久化与恢复 ----
  function snapshot(): GameSnapshot {
    return {
      version: 1,
      phase: phase.value === 'lobby' ? 'playing' : (phase.value as GameSnapshot['phase']),
      gameId: gameId.value ?? '',
      playerTotal: playerTotal.value,
      realPlayerId: realPlayerId.value,
      myWord: myWord.value,
      gameRound: gameRound.value,
      stage: stage.value,
      presentPlayers: presentPlayers.value.slice(),
      statementCursor: statementCursor.value,
      eliminated: { ...eliminated.value },
      reveal: reveal.value,
      exchangeNext: exchangeNext.value,
      exchangeCount: exchangeCount.value,
      messages: messages.value.slice(),
      savedAt: Date.now(),
    }
  }

  function persistNow(): void {
    if (!gameId.value || phase.value === 'lobby') return
    saveSnapshot(snapshot())
  }

  const persistThrottled = throttleTrailing(() => persistNow(), 500)
  function persist(): void {
    persistThrottled()
  }

  function restore(snap: GameSnapshot): void {
    resetState()
    gameId.value = snap.gameId
    playerTotal.value = snap.playerTotal
    realPlayerId.value = snap.realPlayerId
    myWord.value = snap.myWord
    gameRound.value = snap.gameRound
    stage.value = snap.stage
    presentPlayers.value = snap.presentPlayers.slice()
    statementCursor.value = snap.statementCursor
    eliminated.value = { ...snap.eliminated }
    reveal.value = snap.reveal
    exchangeNext.value = snap.exchangeNext
    exchangeCount.value = snap.exchangeCount
    messages.value = snap.messages.slice()
    phase.value = snap.phase === 'finished' ? 'finished' : snap.phase
    if (snap.phase === 'gameover') phase.value = 'gameover'
    if (snap.phase === 'exchange') phase.value = 'exchange'
  }

  /** 启动时恢复：读 current → status 查询 → 按状态分派 */
  /** 启动检查：不自动进入旧对局（大厅开新局是主流程），仅登记「可恢复的对局」供大厅展示 */
  async function bootstrap(): Promise<void> {
    const cur = loadCurrent()
    if (!cur) return
    const snap = loadSnapshot(cur.gameId)
    let status: Awaited<ReturnType<typeof getStatus>> | null = null
    try {
      status = await getStatus(cur.gameId)
    } catch {
      status = null
    }
    if (!status || status.status === 'finished' || !snap) {
      clearCurrent() // 局已结束/后端未知/无快照：无可恢复
      return
    }
    restorable.value = {
      gameId: cur.gameId,
      playerTotal: snap.playerTotal,
      gameRound: status.state?.game_round ?? snap.gameRound,
    }
  }

  /** 用户在大厅点「继续对局」：恢复快照并重连找回现场 */
  async function resumeRestorable(): Promise<void> {
    const info = restorable.value
    if (!info) return
    const snap = loadSnapshot(info.gameId)
    let status: Awaited<ReturnType<typeof getStatus>> | null = null
    try {
      status = await getStatus(info.gameId)
    } catch {
      status = null
    }
    if (!snap || !status || status.status === 'finished') {
      restorable.value = null
      clearCurrent()
      return
    }
    restorable.value = null
    restore(snap)
    // 用 status 权威校准漂移（stage 在交流期不可信，不校准）
    if (status.state) {
      gameRound.value = status.state.game_round
      presentPlayers.value = status.state.present_players.slice()
    }
    if (status.status === 'running') {
      startConflictPolling()
      return
    }
    // waiting_input / continuable：重连找回现场（幂等重发 interrupt / 断点续跑）
    connStatus.value = 'reconnecting'
    resume(undefined)
  }

  function discardRestorable(): void {
    restorable.value = null
    clearCurrent()
  }

  return {
    // state
    connStatus,
    phase,
    gameId,
    playerTotal,
    realPlayerId,
    myWord,
    gameRound,
    stage,
    presentPlayers,
    statementCursor,
    speakingPlayerId,
    votedIds,
    votingNow,
    lastVote,
    myLastVote,
    eliminated,
    reveal,
    exchangeNext,
    exchangeCount,
    messages,
    pendingInterrupt,
    submitState,
    muted,
    lastFrameAt,
    lastError,
    // state（音频/弹框/恢复）
    restorable,
    audioPlayingId,
    lastSpeech,
    wordRevealed,
    roundPopupBusy,
    stageToast,
    // getters
    activeSpeakerId,
    isMyTurnStatement,
    allPlayerIds,
    // actions
    startGame: startGameAction,
    submitStatement,
    submitVote,
    submitExchange,
    toggleMute,
    leaveGame,
    retryAfterError,
    bootstrap,
    resumeRestorable,
    discardRestorable,
    persist,
    persistNow,
    dismissWordPopup: () => {
      wordRevealed.value = true
    },
  }
})

/** 输入清洗：去首尾空白、滤 |（need_exchange 以 | 分隔，输入含 | 会被后端 422） */
function sanitizeInput(raw: string): string {
  return raw.replace(/\|/g, '｜').trim()
}
