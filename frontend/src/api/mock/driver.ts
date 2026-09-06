// mock driver：用 async generator 模拟后端整局游戏，实现与真实后端一致的帧序列语义：
//  - interrupt 帧必是 SSE 段最后一帧（段结束，generator 挂起在 yield 处）
//  - 下一次 resume 调用的值通过 gen.next(value) 送回，成为该 yield 表达式的值
//  - resume 省略且挂起在 interrupt 上 = 幂等重发 interrupt（断线重连）
//  - 真人发言/投票无事件回执（只有 interrupt）；真人交流发言有 exchange_session_player_end 回执
//  - 每个 Agent 发言后必有 player_speech + speech_playback_done gate（真人发言后也过 gate）

import type { SseFrame, StatusResponse } from '@/api/types'
import { sleep } from '@/utils/misc'
import { AGENT_EXCHANGE, AGENT_STATEMENTS, pickScenario, type MockOpts } from './scenarios'
import { playerToneBase64 } from './tone'

interface Frame extends SseFrame {
  delayMs?: number // 该帧吐出前的等待（模拟 LLM/TTS 延迟）
}

const f = (event: SseFrame['event'], payload: any, delayMs = 0): Frame => ({ event, payload, delayMs })

const encode = (frame: Frame): string =>
  `event: ${frame.event}\ndata: ${JSON.stringify({ event: frame.event, payload: frame.payload })}\n\n`

interface Session {
  gameId: string
  opts: MockOpts
  gen: AsyncGenerator<Frame, void, unknown>
  lastInterrupt: Frame | null // 挂起中的 interrupt（waiting_input 判据 + 幂等重发）
  finished: boolean
  presentPlayers: number[]
  gameRound: number
}

const sessions = new Map<string, Session>()

/** 延迟倍速（测试加速用）：localStorage['wis:mock:speed']，默认 1 */
const speedScale = (() => {
  try {
    const v = Number(localStorage.getItem('wis:mock:speed'))
    return Number.isFinite(v) && v > 0 ? v : 1
  } catch {
    return 1
  }
})()

const pacing = (ms: number) => Math.round(ms * speedScale)

/** Agent 发言文本：按 (轮次, 玩家) 取模，保证重放时文本一致 */
const stmtText = (round: number, player: number) =>
  AGENT_STATEMENTS[(round * 3 + player) % AGENT_STATEMENTS.length]

async function* mockGame(s: Session): AsyncGenerator<Frame, void, unknown> {
  const { opts } = s
  const me = opts.realPlayerId
  const N = opts.playerTotal

  yield f('game_started', { game_id: s.gameId, player_total: N })
  yield f('init_start', {}, 500)

  const myWord = me === opts.spyId ? opts.wordSpy : opts.wordCivilian
  yield f('init_end', { real_player_id: me, real_player_word: myWord }, 1200)

  let round = 0
  let over = false

  while (!over) {
    round += 1
    s.gameRound = round
    yield f('statement_start', { game_round: round }, 600)

    for (const p of s.presentPlayers) {
      if (p === me) {
        // 真人发言：无任何前置事件，直接 interrupt（镜像后端）
        const statement = yield f('interrupt', { interrupt: 'need_statement' })
        console.info(`[mock] 真人发言: ${statement}`)
        // 真人发言后仍会经过 speech gate（无音频，前端应立即确认）
        yield f('interrupt', { interrupt: 'speech_playback_done' })
      } else {
        yield f('statement_player_start', { player_id: p }, 300)
        const text = stmtText(round, p)
        yield f('statement_player_end', { player_id: p, statement: text }, 1400)
        yield f(
          'player_speech',
          {
            player_id: p,
            text,
            audio_base64: opts.ttsFail ? '' : playerToneBase64(p),
            audio_format: 'mp3',
            audio_length_ms: opts.ttsFail ? 0 : 700,
          },
          600,
        )
        yield f('interrupt', { interrupt: 'speech_playback_done' })
      }
    }
    yield f('statement_end', { game_round: round }, 400)

    // 投票
    yield f('vote_start', { game_round: round }, 400)
    for (const p of s.presentPlayers) {
      if (p === me) continue
      yield f('vote_player_start', { player_id: p }, 200)
      yield f('vote_player_end', { player_id: p }, 900)
    }
    const myVote = yield f('interrupt', { interrupt: 'need_vote' })
    console.info(`[mock] 真人投票: ${myVote}`)

    // 汇总：剧本决定淘汰结果；真人票也计入展示
    const target = opts.eliminations[round - 1]
    const agents = s.presentPlayers.filter((p) => p !== me)
    const voteCollect: Record<string, number[]> = {}
    if (target === -1) {
      // 平票：agent 票分摊到两个目标
      const half = Math.ceil(agents.length / 2)
      voteCollect[agents[0]] = agents.slice(0, half)
      voteCollect[agents[1]] = agents.slice(half)
    } else if (target != null) {
      voteCollect[target] = agents.slice() // agent 全投剧本目标
    }
    const myVoteNum = Number(myVote)
    if (myVoteNum > 0) {
      voteCollect[myVoteNum] = [...(voteCollect[myVoteNum] ?? []), me]
    }
    const abstain = myVoteNum === 0 ? [me] : []

    const eliminated = target != null && target !== -1 ? target : null
    const isSpyOut = eliminated === opts.spyId
    if (eliminated != null) {
      s.presentPlayers = s.presentPlayers.filter((p) => p !== eliminated)
    }

    const spyWins = !isSpyOut && s.presentPlayers.length <= 2
    over = isSpyOut || spyWins
    yield f(
      'vote_end',
      {
        game_round: round,
        vote_collect: voteCollect,
        abstain_voters: abstain,
        eliminated_player: eliminated,
        eliminated_player_identity:
          eliminated == null ? null : eliminated === opts.spyId ? 'spy' : 'civilian',
        present_players: s.presentPlayers.slice(),
      },
      800,
    )

    if (over) {
      const winner = isSpyOut ? 'civilian' : 'spy'
      const myIdentity = me === opts.spyId ? 'spy' : 'civilian'
      yield f(
        'game_over',
        {
          winner,
          real_player_identity: myIdentity,
          is_real_player_win: winner === myIdentity,
          real_player_id: me,
          spy_id: opts.spyId,
          word_spy: opts.wordSpy,
          word_civilian: opts.wordCivilian,
        },
        900,
      )
    }
  }

  // 赛后交流：共 N+1 次发言，agent 发言指定下一位
  yield f('exchange_session_start', {}, 600)
  let next = opts.exchangeStart
  for (let turn = 0; turn <= N; turn++) {
    if (next === me) {
      // 真人交流：resume 格式 "内容|下一位ID"；有 exchange_session_player_end 回执
      const raw = String(yield f('interrupt', { interrupt: 'need_exchange' }))
      const sep = raw.lastIndexOf('|')
      const content = sep >= 0 ? raw.slice(0, sep) : raw
      const nextId = sep >= 0 ? Number(raw.slice(sep + 1)) : next
      yield f('exchange_session_player_end', { player_id: me, content, next_player_id: nextId }, 300)
      next = nextId
      // 真人交流发言后同样过 speech gate
      yield f('interrupt', { interrupt: 'speech_playback_done' })
    } else {
      yield f('exchange_session_player_start', { player_id: next }, 300)
      const content = AGENT_EXCHANGE[turn % AGENT_EXCHANGE.length]
      const candidates = Array.from({ length: N }, (_, i) => i + 1).filter((p) => p !== next)
      const nextId = turn === 0 ? me : candidates[(next + turn) % candidates.length] // 首个 agent 保证点名真人
      yield f('exchange_session_player_end', { player_id: next, content, next_player_id: nextId }, 1200)
      yield f(
        'player_speech',
        {
          player_id: next,
          text: content,
          audio_base64: opts.ttsFail ? '' : playerToneBase64(next),
          audio_format: 'mp3',
          audio_length_ms: opts.ttsFail ? 0 : 700,
        },
        500,
      )
      yield f('interrupt', { interrupt: 'speech_playback_done' })
      next = nextId
    }
  }
  yield f('exchange_session_end', {}, 400)
  yield f('finished', {})
  s.finished = true
}

/** 模拟 Transport：解析 url/body 分派到对应 session */
export async function* mockTransport(
  url: string,
  body: Record<string, unknown> | undefined,
  _signal: AbortSignal,
): AsyncGenerator<string> {
  if (url === '/api/games') {
    const opts = pickScenario()
    const gameId = `mock-${Date.now().toString(36)}`
    const s: Session = {
      gameId,
      opts,
      gen: null as unknown as Session['gen'],
      lastInterrupt: null,
      finished: false,
      presentPlayers: Array.from({ length: opts.playerTotal }, (_, i) => i + 1),
      gameRound: 0,
    }
    s.gen = mockGame(s)
    sessions.set(gameId, s)

    for (;;) {
      const r = await s.gen.next()
      if (r.done) break
      await sleep(pacing(r.value.delayMs ?? 60))
      yield encode(r.value)
      if (r.value.event === 'interrupt') {
        s.lastInterrupt = r.value
        return // 段结束：interrupt 必为最后一帧
      }
    }
    return
  }

  // resume: /api/games/{id}/resume
  const id = url.split('/')[3]
  const s = sessions.get(id)
  if (!s || s.finished) {
    yield encode({ event: 'error', payload: { type: 'MockError', message: `unknown or finished game ${id}` } })
    return
  }
  const resume = body?.resume

  if (s.lastInterrupt && resume === undefined) {
    // 断线重连：幂等重发 interrupt，不消费
    yield encode(s.lastInterrupt)
    return
  }

  // resume 值只能送进第一个 next()（当前挂起的 interrupt）；后续 pull 一律 undefined，
  // 否则会把值错注入到下一个 gate 的 yield 表达式上
  let inject = resume
  for (;;) {
    const r = await s.gen.next(inject)
    inject = undefined
    if (r.done) break
    await sleep(pacing(r.value.delayMs ?? 60))
    yield encode(r.value)
    if (r.value.event === 'interrupt') {
      s.lastInterrupt = r.value
      return
    }
  }
}

/** 模拟 GET /games/{id}/status */
export async function mockStatus(gameId: string): Promise<StatusResponse> {
  const s = sessions.get(gameId)
  if (!s) throw new Error('404')
  return {
    game_id: gameId,
    status: s.finished ? 'finished' : s.lastInterrupt ? 'waiting_input' : 'continuable',
    interrupt: (s.lastInterrupt?.payload as StatusResponse['interrupt']) ?? null,
    state: {
      player_total: s.opts.playerTotal,
      real_player_id: s.opts.realPlayerId,
      game_round: s.gameRound,
      stage: 'statement',
      present_players: s.presentPlayers.slice(),
      winner: null,
    },
  }
}
