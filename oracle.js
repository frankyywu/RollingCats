/* 喵言机 Meowracle Machine — 本地兜底引擎(离线 / 服务不可用时)
 * 正常情况下产品创意由服务端「三池词库 + AI 破译」生成。
 * 这里只是一个零依赖的本地替身:把乱码当种子,从内置三池词库取概念,
 * 拼出一个粗糙但能用的产品创意,保证 Demo 永不空场。
 */

function hashSeed(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }
function rangePick(rng, lo, hi) { return Math.round(lo + rng() * (hi - lo)); }

/* 内置三池词库:AI 技术锚点 + 社会情绪痛点 + 资本叙事抓手 */
const AI_TECH_POOL = [
  "RAG检索增强", "AI Agent自主体", "MCP协议", "vibe coding", "提示词工程",
  "上下文窗口", "向量数据库", "模型幻觉", "fine-tune微调", "多模态理解",
  "模型蒸馏", "强化学习", "知识图谱", "情感计算", "联邦学习",
  "零样本学习", "涌现能力", "具身智能", "数字孪生", "边缘计算",
];
const SOCIAL_POOL = [
  "班味", "情绪价值", "搭子文化", "精神内耗", "松弛感",
  "淡人哲学", "电子榨菜", "反向旅游", "发疯文学", "特种兵旅游",
  "多巴胺穿搭", "寺庙经济", "微短剧", "打工人日记", "躺平哲学",
  "脆皮年轻人", "全职儿女", "互联网嘴替", "情绪垃圾桶", "显眼包",
];
const VC_NARRATIVE_POOL = [
  "层级与智能", "决策中枢", "AI 原生组织", "系统性机会", "认知杠杆",
  "软件 3.0", "业务操作系统", "智能体网络", "垂直 AI 入口", "工作流重构",
  "数据飞轮", "第二大脑", "企业记忆层", "任务编排层", "人机协同界面",
  "判断力自动化", "专家模型商品化", "AI 中间层", "新型生产关系", "组织神经系统",
];
const CONCEPT_POOLS = [AI_TECH_POOL, SOCIAL_POOL, VC_NARRATIVE_POOL];
const LOCAL_POOL = [...AI_TECH_POOL, ...SOCIAL_POOL, ...VC_NARRATIVE_POOL];

const PERSONAS = {
  ragdoll: { name: "性冷淡极简派" },
  orange:  { name: "激进颠覆派" },
  black:   { name: "暗黑增长派" },
  calico:  { name: "AI 原生派" },
  siamese: { name: "商业变现派" },
  tabby:   { name: "打工人体恤派" },
};

const TAGLINES = [
  (a, b) => `当${a}遇见${b},一切都不一样了。`,
  (a, b) => `用${a}的方式,重新发明${b}。`,
  (a) => `世界不需要又一个 App,但需要${a}。`,
  (a, b) => `${a} × ${b},下一个独角兽就差你了。`,
];
const FEATURE_TPL = [
  (a) => `把${a}做成核心交互,一秒上瘾`,
  (a) => `${a}数据可视化,老板看了都点头`,
  (a, b) => `${a}与${b}联动的隐藏玩法`,
  (a) => `一键生成${a}主题的分享卡片`,
  (a) => `基于${a}的智能推荐`,
];
const TECHVIBE = [
  "Next.js + 一个失眠的周末",
  "Vite + 三杯冰美式 + 一只猫",
  "SwiftUI + 纯靠氛围",
  "一个 HTML 文件 + 无穷的勇气",
  "Supabase + 还没想好的商业模式",
];
const CATWISDOM = [
  "这创意能成,那我以后改吃猫粮里的鱼罐头。",
  "人类啊,你连猫都不如,但这想法还行。",
  "勉强批准。出了事别说是我滚出来的。",
  "做不出来别怪猫,要怪就怪你手太慢。",
  "听起来很蠢,但最蠢的点子往往能融到钱。",
];

function pickEntries(raw) {
  const stream = [...raw].filter((ch) => ch.trim());
  let picks = [];
  if (stream.length <= 7) {
    picks = stream.map((ch, pos) => ({ ch, pos }));
  } else {
    const last = stream.length - 1;
    picks = Array.from({ length: 7 }, (_, i) => {
      const pos = Math.round((i * last) / 6);
      return { ch: stream[pos], pos };
    });
  }
  if (!picks.length) {
    return [0, 1, 2, 3, 4].map((i) => {
      const pool = CONCEPT_POOLS[i % CONCEPT_POOLS.length];
      return { char: "·", title: pool[(183 + i * 17) % pool.length] };
    });
  }
  return picks.map(({ ch, pos }, i) => {
    const pool = CONCEPT_POOLS[i % CONCEPT_POOLS.length];
    return { char: ch, title: pool[(ch.charCodeAt(0) + pos * 17) % pool.length] };
  });
}

/* 本地破译:把词条拼成一个产品创意 */
function localIdea(rawText, personaKey) {
  const raw = (rawText || "").trim();
  const rng = mulberry32(hashSeed(raw + "|" + personaKey));
  const persona = PERSONAS[personaKey] || PERSONAS.ragdoll;
  const entries = pickEntries(raw);
  const words = entries.map((e) => e.title);
  const a = words[0] || "随机性";
  const b = words[1] || words[0] || "猫";

  const tagFn = pick(rng, TAGLINES);
  // 本地兜底也不硬凑:只挑前 1-2 个词条用,其余忽略
  const usedConcepts = [...new Set([a, b])].slice(0, 2);
  const feats = [];
  const used = new Set();
  while (feats.length < 3) {
    const fn = pick(rng, FEATURE_TPL);
    const w1 = pick(rng, usedConcepts), w2 = pick(rng, usedConcepts);
    const s = fn(w1, w2);
    if (!used.has(s)) { used.add(s); feats.push(s); }
  }

  return {
    entries,
    personaName: persona.name,
    idea: {
      usedConcepts,
      productName: `${a.slice(0, 4)}${b.slice(0, 2)}`,
      tagline: tagFn(a, b),
      concept: `只取「${usedConcepts.join("」「")}」这${usedConcepts.length}个概念:做一个围绕${a}、借用${b}机制的产品。其余词条太无聊,猫一爪划掉了。`,
      coreUsage: `用户先把一个模糊需求或今天的糟心场景丢进去,系统用${a}生成第一版行动入口,再用${b}把结果包装成一个可分享的小任务。最后用户得到一张能直接发给同事、朋友或老板的执行卡片,假装这不是猫想出来的。`,
      targetUser: "没灵感又不想加班的产品经理",
      features: feats,
      techVibe: pick(rng, TECHVIBE),
      catWisdom: pick(rng, CATWISDOM),
    },
    meters: {
      feasibility: rangePick(rng, 8, 78),
      investorConfusion: rangePick(rng, 45, 98),
      vibe: rangePick(rng, 62, 99),
    },
  };
}

if (typeof window !== "undefined") { window.MeowOracle = { localIdea }; }
