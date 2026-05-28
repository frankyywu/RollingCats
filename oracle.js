/* 喵机妙算 Meowracle Machine — 本地兜底引擎(离线 / 服务不可用时)
 * 正常情况下产品创意由服务端「维基随机词条 + AI 破译」生成。
 * 这里只是一个零依赖的本地替身:把乱码当种子,从内置词库取概念,
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

/* 内置词库:维基拿不到时的概念来源 */
const LOCAL_POOL = [
  "潮汐发电", "巴洛克音乐", "蚂蚁信息素", "黑胶唱片", "二十四节气", "活字印刷",
  "深海热泉", "莫比乌斯环", "多巴胺", "瑞士军刀", "信天翁", "拜占庭马赛克",
  "光合作用", "关东煮", "摩斯密码", "陨石坑", "盲文", "发酵食品",
  "候鸟迁徙", "齿轮", "极光", "失物招领处", "潜水钟", "竹简",
];

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

function pickEntries(raw, pool, rng) {
  const seen = [];
  for (const ch of raw) {
    if (ch.trim() && !seen.includes(ch)) seen.push(ch);
  }
  const chars = seen.slice(0, 7);
  if (!chars.length) {
    return [0, 1, 2, 3, 4].map((i) => ({ char: "·", title: pool[Math.floor(rng() * pool.length)] }));
  }
  return chars.map((ch) => ({ char: ch, title: pool[ch.charCodeAt(0) % pool.length] }));
}

/* 本地破译:把词条拼成一个产品创意 */
function localIdea(rawText, personaKey) {
  const raw = (rawText || "").trim();
  const rng = mulberry32(hashSeed(raw + "|" + personaKey));
  const persona = PERSONAS[personaKey] || PERSONAS.ragdoll;
  const entries = pickEntries(raw, LOCAL_POOL, rng);
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
