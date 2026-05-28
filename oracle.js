/* 喵机妙算 Meowracle Machine — 解读引擎
 * 纯前端、零依赖。核心承诺:不同的乱码 → 明显不同的命运。
 * 做法:先从乱码里抽取“真实字符特征”,再用一个由乱码本身播种的伪随机数
 * 从特征对应的句库里取词。同一串乱码永远给同一份命运(像真的一样),
 * 不同乱码因为特征不同、种子不同,解读会明显分叉。
 */

/* ---------- 可复现的伪随机:同一串乱码 = 同一份命运 ---------- */
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

/* ---------- 特征抽取:让“具体字符”真的进入解读 ---------- */
function extractFeatures(raw) {
  const text = raw || "";
  const chars = [...text];
  const f = {
    length: chars.length,
    brackets: (text.match(/[\[\]\(\)\{\}<>]/g) || []).length,
    digits: (text.match(/[0-9]/g) || []).length,
    zeros: (text.match(/0{2,}/g) || ["", ""].slice(0, 0)).length, // 连续0
    hasZeroRun: /0{3,}/.test(text),
    equals: (text.match(/=/g) || []).length,
    dashes: (text.match(/[-_~]/g) || []).length,
    spaces: (text.match(/\s/g) || []).length,
    uppers: (text.match(/[A-Z]/g) || []).length,
    letters: (text.match(/[a-zA-Z]/g) || []).length,
    symbols: (text.match(/[^a-zA-Z0-9\s]/g) || []).length,
    pCount: (text.match(/p/gi) || []).length,
  };

  // 最长重复段(执念 / 重复劳动的来源)
  let longestRun = 0, runChar = "";
  let cur = 1;
  for (let i = 1; i <= chars.length; i++) {
    if (i < chars.length && chars[i] === chars[i - 1]) {
      cur++;
    } else {
      if (cur > longestRun) { longestRun = cur; runChar = chars[i - 1]; }
      cur = 1;
    }
  }
  f.longestRun = longestRun;
  f.runChar = runChar;

  // 末尾字符(命运的“等号后面”)
  f.lastChar = chars.length ? chars[chars.length - 1] : "";
  // 唯一字符数(混乱度)
  f.unique = new Set(chars.filter((c) => !/\s/.test(c))).size;
  return f;
}

/* ---------- 句库:每条特征 → 一组可替换的解读句子 ---------- */
// pick: 由种子决定取哪一条,保证可复现
function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }

function buildReadings(f, rng) {
  const lines = [];
  const keywords = [];

  if (f.longestRun >= 4) {
    const ch = f.runChar.trim() || "空白";
    lines.push(pick(rng, [
      `连续的「${ch}」重复了 ${f.longestRun} 次——你最近在某件事上反复横跳,宇宙说:别再按了,你已经按够了。`,
      `「${ch}」的长串说明你正困在一段重复劳动里,而重复本身就是一种提问:它真的值得吗?`,
      `${f.longestRun} 个「${ch}」叠在一起,是执念的形状。猫神看穿了,你在等一个本不会来的回复。`,
    ]));
    keywords.push("执念", "重复");
  }

  if (f.brackets >= 2) {
    lines.push(pick(rng, [
      `${f.brackets} 个括号代表你正在打开或关闭某些未完成的关系,注意:括号总是成对的,但你的人际不一定。`,
      `这些括号是边界。今天适合把某个一直敞着的“(”合上,哪怕里面什么都没写完。`,
      `括号丛生,说明你习惯把真心话放进“补充说明”里。猫神建议:把主句说出来。`,
    ]));
    keywords.push("边界", "未完成");
  }

  if (f.hasZeroRun) {
    lines.push(pick(rng, [
      `一连串的 0 是宇宙开给你的空白支票——金额未填,意味着今天怎么活都不算亏。`,
      `归零的 0 阵列在提醒你:有些进度条清空了反而轻松,删掉它,别存档。`,
    ]));
    keywords.push("归零", "空白支票");
  }

  if (f.equals >= 1) {
    lines.push(pick(rng, [
      `等号出现了,意味着某件悬而未决的事即将进入“结算阶段”。等号后面是空的,所以结果由你填。`,
      `「=」是今天的暗示:别急着求答案,先把等式两边各自的人哄好。`,
    ]));
    keywords.push("结算");
  }

  if (f.dashes >= 2) {
    lines.push(pick(rng, [
      `横线连成一片——猫神的意思很直白:今天别立着硬扛,先横着活,横着也是一种姿态。`,
      `这些破折号是未说完的话的尾巴。有句话你今天最好不要补完。`,
    ]));
    keywords.push("横着活");
  }

  if (f.pCount >= 2) {
    lines.push(pick(rng, [
      `反复出现的 p 是 pretend 的开头——你今天很想装作一切都好,猫神准许你装,但只准到下午三点。`,
      `p 像是没说出口的“please”。今天你会向某人低头,而那并不丢人。`,
    ]));
    keywords.push("假装", "请求");
  }

  if (f.uppers >= 3) {
    lines.push(pick(rng, [
      `大写字母扎堆,说明你心里在喊。喊出来无妨,但别对着错的人喊。`,
    ]));
    keywords.push("情绪上头");
  }

  // 混乱度兜底:保证再短的乱码也有话说
  if (lines.length < 2) {
    if (f.unique <= 2 && f.length > 0) {
      lines.push(pick(rng, [
        `字符如此单调,说明你今天的世界很专注,也可能只是很困。专注与困倦,猫神分不清,你也别分了。`,
        `只用了寥寥几个键,极简即是答案:今天别把简单的事复杂化。`,
      ]));
      keywords.push("极简", "专注");
    } else {
      lines.push(pick(rng, [
        `这串混沌没有明显规律,这本身就是预兆:今天不要试图给一切都找一个解释——包括这条神谕。`,
        `字符四散奔逃,像你今天的注意力。接受它,混乱里也藏着自由。`,
      ]));
      keywords.push("混沌", "自由");
    }
  }

  if (f.lastChar && f.lastChar.trim()) {
    lines.push(pick(rng, [
      `而结尾落在「${f.lastChar}」上——这是猫神的句号,意思是:今天到这里,就别再往后想了。`,
    ]));
  }

  return { text: lines.join("\n\n"), keywords: [...new Set(keywords)] };
}

/* ---------- 各类“神棍配件” ---------- */
const LUCKY = ["一根数据线", "左边那只袜子", "微温的美式", "一张没发出去的便签", "充到 38% 的手机", "楼下的橘猫", "一把忘了买的伞", "昨天的剩饭", "一支没水的笔", "下午四点的阳光"];
const TABOO = ["解释自己", "回那封邮件", "相信“很快就好”", "称体重", "翻旧聊天记录", "在群里发长语音", "答应周末加班", "二次确认已经确认过的事", "对镜子做决定", "空腹做规划"];
const ADVICE = ["先吃饭,再焦虑。", "把一件拖了三天的小事做掉。", "今天适合喝冰美式,不适合开复杂会议。", "别主动开启新的复杂对话。", "给一个人发“在吗”,然后立刻发正文。", "把手机倒扣两小时。", "对一件小事说“算了”。", "早睡是今天唯一正确的玄学。"];
const MISREAD = [
  "你以为这是爱情预兆。其实猫只是踩到了删除键。",
  "你以为这是事业上升信号。其实猫在追一只看不见的虫子。",
  "你以为命运在暗示你换工作。其实猫只是嫌键盘是热的。",
  "你以为今天会有好事。猫表示它没这个意思,但也没反对。",
  "你以为这条神谕很准。准的不是神谕,是你本来就想这么干。",
];
const JUDGE = [
  "你今天看起来像一个没睡醒的中层管理者。",
  "你散发着一种“假装在忙”的能量。",
  "你今天的状态:能用,但需要重启。",
  "你看上去像周日晚上的自己。",
  "你身上有种刚被已读不回的气场。",
];
const RELATION = [
  "愿意和你共处一室,但不愿意承认你是家人。",
  "把你当成会自动出现的饭票,偶尔也当暖气。",
  "对你的容忍度今天上调了 2%,别得寸进尺。",
  "认可你的存在,如同认可一件家具。一件会喂饭的家具。",
  "今天罕见地想靠近你,但绝不会让你知道是它先想的。",
];

/* ---------- 猫神人格:决定语气与三条自黑指标的区间 ---------- */
const PERSONAS = {
  ragdoll: { name: "冷淡布偶神", sign: "（它看了你一眼,移开了视线。）", trust: [8, 22], comfort: [70, 95], nonsense: [60, 80] },
  orange:  { name: "暴躁橘猫神", sign: "（它一巴掌拍翻了水杯以示批准。）", trust: [5, 18], comfort: [55, 80], nonsense: [82, 96] },
  black:   { name: "阴湿黑猫神", sign: "（它在阴影里点了点头,你没看清。）", trust: [10, 28], comfort: [60, 85], nonsense: [70, 90] },
  calico:  { name: "赛博三花神", sign: "（它的瞳孔里闪过一行报错日志。）", trust: [12, 30], comfort: [65, 88], nonsense: [66, 84] },
  siamese: { name: "油腻暹罗神", sign: "（它压低嗓音说:都懂的,都懂的。）", trust: [6, 20], comfort: [58, 82], nonsense: [80, 95] },
  tabby:   { name: "加班狸花神", sign: "（它打了个哈欠,继续替你扛着。）", trust: [9, 24], comfort: [72, 92], nonsense: [64, 82] },
};

function rangePick(rng, [lo, hi]) { return Math.round(lo + rng() * (hi - lo)); }

/* ---------- 主入口 ---------- */
function interpret(rawText, personaKey, mode) {
  const text = (rawText || "").trim();
  const persona = PERSONAS[personaKey] || PERSONAS.ragdoll;
  const seed = hashSeed(text + "|" + personaKey);
  const rng = mulberry32(seed);
  const f = extractFeatures(text);
  const reading = buildReadings(f, rng);

  const result = {
    raw: text,
    personaName: persona.name,
    personaSign: persona.sign,
    reading: reading.text,
    keywords: reading.keywords.length ? reading.keywords : ["未知"],
    advice: pick(rng, ADVICE),
    lucky: pick(rng, LUCKY),
    taboo: pick(rng, TABOO),
    misread: pick(rng, MISREAD),
    judge: pick(rng, JUDGE),
    judgeScore: rangePick(rng, [11, 96]),
    relation: pick(rng, RELATION),
    trust: rangePick(rng, persona.trust),
    comfort: rangePick(rng, persona.comfort),
    nonsense: rangePick(rng, persona.nonsense),
    modeNote: mode === "human"
      ? "（系统检测到这串乱码过于工整。人类伪装猫输入——猫神鄙视你,但还是会算。）"
      : "",
  };
  return result;
}

if (typeof window !== "undefined") { window.MeowOracle = { interpret }; }
