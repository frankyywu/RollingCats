#!/usr/bin/env python3
"""喵言机 本地服务器：静态托管 + 两层「破译」管线。

概念：猫在键盘上乱滚 → 乱码当随机种子 → 每个字母回到三池词库
取出一个 AI 黑话 / 社会情绪 / 资本叙事概念 → 再用 AI 把它们「破译」成一个全新的产品创意。
给没灵感的产品经理：让猫滚键盘，滚出你的下一个 vibe coding 创意。

- GET /            -> 静态文件（index.html / oracle.js / styles.css）
- POST /api/oracle -> 三池词库 + NVIDIA LLM 破译产品创意

API key 留在服务端，不进浏览器。仅供本机 Demo 使用。
"""
import hashlib
import json
import os
import random
import re
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# API key 绝不写进代码（这是 public repo）。按顺序从以下来源读取：
#   1) 环境变量 NVIDIA_API_KEY
#   2) 项目根目录下的 .nvidia_key 文件（已在 .gitignore 中，不会被提交）
#   3) ~/.nvidia_key
def load_api_key():
    k = os.environ.get("NVIDIA_API_KEY")
    if k:
        return k.strip()
    for p in (".nvidia_key", os.path.expanduser("~/.nvidia_key")):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    return ""


NVIDIA_API_KEY = load_api_key()
NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
PORT = int(os.environ.get("PORT", "8000"))

MAX_CONCEPTS = 7  # 最多取多少个词条参与破译

# 猫军师人格 → 产品创意的风格走向（取代原来的占卜人格）
PERSONA_STYLE = {
    "ragdoll": "性冷淡极简派（冷淡布偶猫）：主张做减法、克制、高级感，产品要少即是多、性冷淡美学。",
    "orange":  "激进颠覆派（暴躁橘猫）：要颠覆整个行业，口号炸裂、不破不立，语气火爆自大。",
    "black":   "暗黑增长派（阴湿黑猫）：擅长抓人性弱点、上瘾机制、增长黑客，略带反派得意感。",
    "calico":  "AI 原生派（赛博三花）：一切皆 AI agent，赛博朋克、未来感拉满，满嘴黑话。",
    "siamese": "商业变现派（油腻暹罗）：张口闭口商业模式、融资、增长飞轮、TAM，油嘴滑舌。",
    "tabby":   "打工人体恤派（加班狸花）：做能减少加班、对打工人友好的工具，语气疲惫但温柔。",
}
PERSONA_NAME = {
    "ragdoll": "性冷淡极简派",
    "orange":  "激进颠覆派",
    "black":   "暗黑增长派",
    "calico":  "AI 原生派",
    "siamese": "商业变现派",
    "tabby":   "打工人体恤派",
}

# 三池词库：技术锚点 + 人性痛点 + 资本叙事，避免维基随机词条过度跑偏。
AI_TECH_POOL = [
    "RAG检索增强", "AI Agent自主体", "MCP协议", "vibe coding", "提示词工程",
    "上下文窗口", "向量数据库", "模型幻觉", "fine-tune微调", "多模态理解",
    "模型蒸馏", "强化学习", "知识图谱", "情感计算", "联邦学习",
    "零样本学习", "涌现能力", "具身智能", "数字孪生", "边缘计算",
    "神经接口", "合成数据", "推理加速", "注意力机制", "越狱攻击",
    "对齐税", "工具调用", "记忆管理", "智能体编排", "流式输出",
    "语义搜索", "意图识别", "提示注入", "视觉接地", "冷启动问题",
    "模型坍塌", "幻觉率", "大语言模型", "增量预训练", "强化对齐",
]
SOCIAL_POOL = [
    "班味", "情绪价值", "搭子文化", "精神内耗", "松弛感",
    "淡人哲学", "电子榨菜", "反向旅游", "发疯文学", "特种兵旅游",
    "多巴胺穿搭", "寺庙经济", "微短剧", "打工人日记", "躺平哲学",
    "脆皮年轻人", "全职儿女", "互联网嘴替", "情绪垃圾桶", "显眼包",
    "整顿职场", "宠物经济", "City Walk", "爷青回", "知识付费",
    "副业焦虑", "即时满足", "信息茧房", "数字极简", "下班经济",
    "成分党", "被迫营业", "佛系生存", "数字游民", "社恐社牛",
    "科技特种兵", "搭子经济", "黑神话效应", "拿捏感", "脑洞消费",
]
VC_NARRATIVE_POOL = [
    "层级与智能", "决策中枢", "AI 原生组织", "系统性机会", "认知杠杆",
    "软件 3.0", "业务操作系统", "智能体网络", "垂直 AI 入口", "工作流重构",
    "数据飞轮", "第二大脑", "企业记忆层", "任务编排层", "人机协同界面",
    "判断力自动化", "专家模型商品化", "AI 中间层", "新型生产关系", "组织神经系统",
    "知识工作自动化", "AI 超级员工", "默认自动化", "实时决策流", "上下文资产化",
    "端到端闭环", "复合型 AI 应用", "分发即产品", "用户意图入口", "模型路由层",
    "AI 劳动力市场", "个人董事会", "隐形 SaaS", "可编程公司", "场景级操作系统",
    "从工具到同事", "AI 原生消费入口", "长尾知识变现", "组织级 Copilot", "执行力基础设施",
]
CONCEPT_POOLS = (AI_TECH_POOL, SOCIAL_POOL, VC_NARRATIVE_POOL)

SYSTEM_PROMPT = """你是“喵言机 Meowracle Machine”的产品破译引擎。
背景：一只猫在键盘上乱滚，系统把乱码当随机种子，让每个按键回到三池词库里取出一个概念：AI/科技原生黑话、当代中国社会情绪词、红杉/AI 投资圈常见的资本叙事关键词。
现在交给你一组跨池混合概念，你要从中破译出一个【全新的、马上能 vibe coding 动手做】的产品创意——给没有灵感的产品经理用。

【最重要的原则：不要硬凑！】这些概念天然来自三种不同语境：技术怎么做、用户为什么在乎、融资叙事怎么讲。
请只挑出其中真正“能擦出火花”的 2-4 个概念，最好同时覆盖技术锚点、人性痛点、战略抓手；其余概念要【主动忽略】，绝不要为了用上而强行编进去。
宁可只用 2 个好概念做出一个干净的创意，也不要把 7 个全塞进一段牵强的话里。

【产品深度要求】
不要把词条改写成“检测 X、分析 Y、给出建议”这种浮在表面的助手。你必须把创意落到一个很窄、很具体的使用场景里：谁在什么尴尬/高频/付费意愿强的时刻打开它，输入什么，系统做哪一步判断，最后吐出什么可执行产物。
每个创意都必须有一个“可演示闭环”：输入 → 处理 → 输出 → 下一步动作。输出物要具体，比如“决策卡、群聊回复、任务清单、风险雷达、脚本、路由面板、对比表、30秒复盘卡”，不要只说“建议”。
如果采用资本叙事词（如决策中枢、层级与智能、组织神经系统），它只能作为产品机制或定位，不要写成空洞口号。必须回答：这个“中枢”到底接入哪些信息？替用户做哪类决定？决定以什么 UI 呈现？
如果采用社会情绪词（如社恐社牛、班味、精神内耗），必须把它翻译成一个可观察的行为信号或产品触发条件，不要停留在人设标签。
如果采用 AI 技术词（如视觉接地、模型坍塌、RAG），必须说明它在产品里负责哪一步，不要只是把词贴在文案里。

【禁用套路】
不要输出“检测用户状态 + 分析倾向 + 给出建议”的三件套。
不要输出“帮助用户更好地理解自己/提升效率/优化体验”这类无信息量句子。
不要把产品写成万能聊天机器人、通用助手、镜子、仪表盘，除非你能说清楚它只解决一个非常具体的场景。

风格：一本正经、脑洞大、好笑，但听起来像一个周末真的能做出 demo。绝不说教。
必须严格输出 JSON 对象，不要任何额外文字，不要 markdown 代码块。
每个字段的“值”里只放正文内容本身，绝对不要把字段名写进值里。字段：
- usedConcepts：你真正采用的概念（字符串数组，必须逐字照抄输入里的原词条名；没采用的不要列）
- productName：产品名（中文，朗朗上口，可带一点英文）
- tagline：一句话定位 / slogan，要有具体场景或动作，不要空泛愿景
- concept：核心创意，2-3 句，必须包含明确用户、具体场景、产品输出物
- coreUsage：核心用法，2-3 句，必须按“用户输入什么 → 系统如何处理 → 输出什么 → 用户下一步做什么”的顺序讲清楚
- targetUser：目标用户，一句话，必须具体到一个窄人群，不要写“年轻都市人/职场人士/创作者”这种泛人群
- features：3 个关键功能，字符串数组，每个都必须像一个能点开的功能名 + 具体结果，不要写“分析/推荐/优化”
- techVibe：技术栈氛围，一句话调侃（如“Next.js + 一个周末 + 三杯冰美式”）
- catWisdom：猫对这个创意的毒舌点评，一句话（可以吐槽那些被你忽略的无聊词条）

输出示例（仅示意风格，内容要根据真实词条重新生成；注意它只采用了 7 个里的 3 个）：
{"usedConcepts":["RAG检索增强","班味","决策中枢"],"productName":"班味中枢","tagline":"把办公室废话压缩成下一步行动","concept":"只取‘RAG检索增强’、‘班味’和‘决策中枢’三个概念，做一个专门吞掉会议纪要、群聊和老板口头禅的团队决策入口。它不再帮你整理信息，而是直接告诉你谁该做什么、什么时候必须交，以及这件事到底是不是又在制造班味。","coreUsage":"用户把会议录音、飞书群聊或一段老板语音丢进去，系统先检索历史项目上下文，再生成一张可执行决策卡。卡片会列出责任人、截止时间、风险点和一句能发回群里的体面回复。","targetUser":"每天被会议和群消息淹死的中层产品经理","features":["群聊自动提炼决策卡","跨项目上下文检索","班味浓度预警"],"techVibe":"Next.js + RAG + 一个不想再开会的周末","catWisdom":"你们人类把废话叫协作，我一般叫打翻水盆。"}"""


def pick_entries(raw):
    """每个（首次出现的）字母 → 按位置轮询三池词库，取出一个概念。"""
    seen = []
    for ch in raw:
        if ch.strip() and ch not in seen:
            seen.append(ch)
    chars = seen[:MAX_CONCEPTS]
    if not chars:
        chars = ["·"] * 5
    entries = []
    for i, ch in enumerate(chars):
        pool = CONCEPT_POOLS[i % len(CONCEPT_POOLS)]
        entries.append({"char": ch, "title": pool[(ord(ch) + i * 17) % len(pool)]})
    return entries


def make_meters(raw, persona):
    h = int(hashlib.md5((raw + "|" + persona).encode("utf-8")).hexdigest(), 16)
    r = random.Random(h)
    return {
        "feasibility": r.randint(8, 78),       # 落地可行性
        "investorConfusion": r.randint(45, 98),  # 投资人困惑度
        "vibe": r.randint(62, 99),               # vibe 浓度
    }


def build_user_prompt(entries, persona_key):
    style = PERSONA_STYLE.get(persona_key, PERSONA_STYLE["ragdoll"])
    titles = "、".join(e["title"] for e in entries)
    return (
        f"今日产品军师：{style}\n\n"
        f"猫滚键盘后，从 AI黑话 × 社会情绪词 × 资本叙事 三池词库里破译出的随机概念：{titles}。\n\n"
        f"请按上述人格的风格，把这些概念破译成一个产品创意。不要复述概念名，不要写泛泛的 AI 助手；请给出一个窄场景、一个明确输入、一个具体输出物和一个用户下一步动作，严格输出 JSON。"
    )


def call_nvidia(entries, persona_key):
    if not NVIDIA_API_KEY:
        raise RuntimeError("缺少 NVIDIA API key：请设置环境变量 NVIDIA_API_KEY 或创建 .nvidia_key 文件")
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(entries, persona_key)},
        ],
        "temperature": 1.05,
        "top_p": 0.95,
        "max_tokens": 800,
    }
    req = urllib.request.Request(
        f"{NVIDIA_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return extract_json(data["choices"][0]["message"]["content"])


def extract_json(content):
    """LLM 偶尔包裹多余文字/代码块，稳健地抠出第一个 JSON 对象。"""
    s = content.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*", "", s).strip().strip("`").strip()
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]
    return json.loads(s)


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {
                "ok": True,
                "hasApiKey": bool(NVIDIA_API_KEY),
                "model": NVIDIA_MODEL,
            })
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/oracle":
            self.send_error(404, "Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            raw = body.get("raw", "")
            persona = body.get("persona", "ragdoll")
            entries = pick_entries(raw)
            idea = call_nvidia(entries, persona)
            self._json(200, {
                "ok": True,
                "entries": entries,
                "personaName": PERSONA_NAME.get(persona, "神秘猫军师"),
                "idea": idea,
                "meters": make_meters(raw, persona),
            })
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:500]
            self._json(502, {"ok": False, "error": f"NVIDIA API {e.code}: {detail}"})
        except Exception as e:  # noqa: BLE001 —— Demo：任何失败都回退到本地引擎
            self._json(500, {"ok": False, "error": str(e)})

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # 安静一点


if __name__ == "__main__":
    print(f"喵言机 running at http://localhost:{PORT}/  (model: {NVIDIA_MODEL})")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
