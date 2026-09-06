// mock 剧本：决定模拟对局的走向。开局时读 localStorage['wis:mock:scenario'] 选择剧本，
// 便于不改代码切换测试场景（默认 standard）。

export interface MockOpts {
  playerTotal: number
  realPlayerId: number
  spyId: number
  wordCivilian: string
  wordSpy: string
  ttsFail: boolean // true = 所有 player_speech 的 audio_base64 为空串（TTS 降级）
  /** 每轮被淘汰的玩家 ID；-1 表示该轮平票无人淘汰。淘汰到分出胜负为止（多余的项忽略） */
  eliminations: number[]
  winner: 'civilian' | 'spy'
  /** 赛后交流第一个发言的玩家 ID */
  exchangeStart: number
}

const BASE: Omit<MockOpts, 'eliminations'> = {
  playerTotal: 6,
  realPlayerId: 3,
  spyId: 5,
  wordCivilian: '苹果',
  wordSpy: '梨子',
  ttsFail: false,
  winner: 'civilian',
  exchangeStart: 2,
}

export const SCENARIOS: Record<string, MockOpts> = {
  // 标准局：6 人，第 1 轮淘汰平民 2，第 2 轮淘汰卧底 5，平民胜
  standard: { ...BASE, eliminations: [2, 5] },
  // 平票局：第 1 轮平票无人淘汰，之后正常
  tie: { ...BASE, eliminations: [-1, 2, 5] },
  // TTS 全降级：无任何音频，验证降级路径与 gate 即时确认
  ttsFail: { ...BASE, ttsFail: true, eliminations: [2, 5] },
  // 卧底胜利线：连续淘汰平民至仅剩 2 人
  spyWin: {
    ...BASE,
    realPlayerId: 2,
    spyId: 6,
    eliminations: [1, 3, 4],
    winner: 'spy',
  },
}

export function pickScenario(): MockOpts {
  const name = localStorage.getItem('wis:mock:scenario')
  return (name && SCENARIOS[name]) || SCENARIOS.standard
}

export const AGENT_STATEMENTS = [
  '这东西我天天见，说熟悉也熟悉，说陌生也陌生。',
  '说实话我不太敢描述太细，怕被某些人钻空子。',
  '我拿到的时候还挺意外的，大家应该都见过吧？',
  '有一个特征很明显，但我说出来怕暴露太多。',
  '上次提到它还是很久以前，感觉挺怀念的。',
  '反正我的词挺好的，你们猜猜我为什么这么淡定。',
  '结合前面几位的发言，我大概有点想法了。',
  '我不针对任何人，但确实有位的发言让我很在意。',
]

export const AGENT_EXCHANGE = [
  '哈哈这局演得累死我了，都不敢说太具体。',
  '我一直以为拿到的是同一个词，投票的时候才发现不对劲。',
  '输了但是心服口服，卧底藏得是真好。',
  '早知道第一轮我就该投出去了，悔啊。',
  '下次再来一局？我想当卧底试试。',
  '你们发言都太稳了，我全程都在跟着跑。',
]
