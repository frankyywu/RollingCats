#!/usr/bin/env python3
"""喵机妙算 本地服务器：静态托管 + 两层「破译」管线。

概念：猫在键盘上乱滚 → 乱码当随机种子 → 每个字母回到词库（维基百科随机词条）
取出一个真实概念 → 再用 AI 把这堆毫不相关的随机概念「破译」成一个全新的产品创意。
给没灵感的产品经理：让猫滚键盘，滚出你的下一个 vibe coding 创意。

- GET /            -> 静态文件（index.html / oracle.js / styles.css）
- POST /api/oracle -> 维基随机词条 + NVIDIA LLM 破译产品创意

API key 留在服务端，不进浏览器。仅供本机 Demo 使用。
"""
import hashlib
import json
import os
import random
import re
import urllib.parse
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
WIKI_API = os.environ.get("WIKI_API", "https://zh.wikipedia.org/w/api.php")
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

# 维基拿不到时的兜底词库
FALLBACK_POOL = [
    "潮汐发电", "巴洛克音乐", "蚂蚁信息素", "黑胶唱片", "二十四节气", "活字印刷",
    "深海热泉", "莫比乌斯环", "多巴胺", "瑞士军刀", "信天翁", "拜占庭马赛克",
    "光合作用", "便利店关东煮", "电报摩斯密码", "陨石坑", "盲文", "发酵食品",
    "候鸟迁徙", "齿轮", "极光", "失物招领处", "潜水钟", "竹简",
]

SYSTEM_PROMPT = """你是“喵机妙算 Meowracle Machine”的产品破译引擎。
背景：一只猫在键盘上乱滚，系统把乱码当随机种子，让每个按键回到“词库”（维基百科随机词条）里取出一个真实存在的概念。
现在交给你一堆彼此毫不相关的随机概念，你要从中破译出一个【全新的、马上能 vibe coding 动手做】的产品创意——给没有灵感的产品经理用。

【最重要的原则：不要硬凑！】这些随机概念里，大多数是没有信息价值的噪声——冷门人名、地名、行政区、车站、编号、某支部队等，它们提供不了任何产品启发。
请只挑出其中真正“有信息价值、能擦出火花”的 1-3 个概念（比如一种现象、机制、技术、文化、物件、行为），围绕它们构建创意；其余无意义的概念要【主动忽略】，绝不要为了用上而强行编进去。
宁可只用 1 个好概念做出一个干净的创意，也不要把 7 个全塞进一段牵强的话里。如果一个有价值的概念都没有，就坦诚地基于最不无聊的那个发挥。

风格：一本正经、脑洞大、好笑，但听起来像那么回事。绝不说教。
必须严格输出 JSON 对象，不要任何额外文字，不要 markdown 代码块。
每个字段的“值”里只放正文内容本身，绝对不要把字段名写进值里。字段：
- usedConcepts：你真正采用的概念（字符串数组，必须逐字照抄输入里的原词条名；没采用的不要列）
- productName：产品名（中文，朗朗上口，可带一点英文）
- tagline：一句话定位 / slogan
- concept：核心创意，2-3 句，只说你采用的那几个概念怎么联系、解决什么场景
- targetUser：目标用户，一句话
- features：3 个关键功能，字符串数组，每个一句话
- techVibe：技术栈氛围，一句话调侃（如“Next.js + 一个周末 + 三杯冰美式”）
- catWisdom：猫对这个创意的毒舌点评，一句话（可以吐槽那些被你忽略的无聊词条）

输出示例（仅示意风格，内容要根据真实词条重新生成；注意它只采用了 7 个里的 2 个）：
{"usedConcepts":["潮汐发电","多巴胺"],"productName":"潮汐闹钟","tagline":"让你跟着月亮起床","concept":"只取‘潮汐发电’和‘多巴胺’两个概念，做一个按潮汐节律唤醒、并用多巴胺奖励机制让你舍不得赖床的闹钟。其余词条太无聊，已被猫一爪划掉。","targetUser":"作息混乱的数字游民","features":["潮汐节律唤醒曲线","起床多巴胺打卡","赖床惩罚白噪音"],"techVibe":"SwiftUI + 一个失眠的周末","catWisdom":"剩下那几个地名？连我都懒得踩。"}"""


def fetch_wiki_pool(n=50):
    """从中文维基百科抓一批随机词条作为“词库”。失败则用兜底词库。"""
    params = {
        "action": "query",
        "list": "random",
        "rnnamespace": "0",
        "rnlimit": str(n),
        "format": "json",
    }
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "MeowracleDemo/1.0 (local demo)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        titles = [x["title"] for x in data["query"]["random"]]
        titles = [t for t in titles if _good_title(t)]
        if len(titles) >= 5:
            return titles
    except Exception:
        pass
    return list(FALLBACK_POOL)


def _good_title(t):
    """过滤掉噪声词条：小行星编号、年份、列表/消歧义/模板页等。"""
    if re.fullmatch(r"\d{4}年.*", t):
        return False
    if any(k in t for k in ("消歧义", "消歧義", "列表", "模板", "分类", "Template", "小行星")):
        return False
    if re.search(r"\d{3,}", t):  # 一堆数字编号的多半很无聊
        return False
    return True


def pick_entries(raw, pool):
    """每个（首次出现的）字母 → 用字符码索引词库，取出一个词条。"""
    seen = []
    for ch in raw:
        if ch.strip() and ch not in seen:
            seen.append(ch)
    chars = seen[:MAX_CONCEPTS]
    if not chars:
        return [{"char": "·", "title": t} for t in pool[:5]]
    return [{"char": ch, "title": pool[ord(ch) % len(pool)]} for ch in chars]


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
        f"猫滚键盘后，从词库里破译出的随机概念：{titles}。\n\n"
        f"请按上述人格的风格，把这些概念强行破译成一个产品创意，严格输出 JSON。"
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
    def do_POST(self):
        if self.path != "/api/oracle":
            self.send_error(404, "Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            raw = body.get("raw", "")
            persona = body.get("persona", "ragdoll")
            pool = fetch_wiki_pool(50)
            entries = pick_entries(raw, pool)
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
    print(f"喵机妙算 running at http://localhost:{PORT}/  (model: {NVIDIA_MODEL})")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
