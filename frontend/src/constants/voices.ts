export type VoiceOption = {
  id: string
  name: string
  gender: string
  desc: string
  tier?: 'basic' | 'special'
}

export const DEFAULT_VOICES: VoiceOption[] = [
  { id: 'xiaoyan', name: '讯飞小燕', gender: 'female', desc: '温暖亲切女声', tier: 'basic' },
  { id: 'aisxping', name: '讯飞小萍', gender: 'female', desc: '明亮活泼女声', tier: 'basic' },
  { id: 'aisjinger', name: '讯飞小婧', gender: 'female', desc: '年轻甜美女声', tier: 'basic' },
  { id: 'aisjiuxu', name: '讯飞许久', gender: 'male', desc: '磁性沉稳男声', tier: 'basic' },
  { id: 'xiaoyu', name: '讯飞小宇', gender: 'male', desc: '亲切自然男声', tier: 'basic' },
  { id: 'xiaofeng', name: '讯飞小峰', gender: 'male', desc: '成熟稳重男声', tier: 'basic' },
  { id: 'x4_yezi', name: '讯飞小露', gender: 'female', desc: '亲切女声', tier: 'special' },
  { id: 'x6_lingxiaoxuan_assist', name: '聆小璇', gender: 'female', desc: '助理女声', tier: 'special' },
  { id: 'x6_lingxiaoyao_emo', name: '聆小瑶', gender: 'female', desc: '情感女声', tier: 'special' },
  { id: 'x4_lingfeizhe_emo', name: '聆飞哲', gender: 'male', desc: '情感男声', tier: 'special' },
  { id: 'x4_qige', name: '讯飞七哥', gender: 'male', desc: '磁性男声', tier: 'special' }
]
