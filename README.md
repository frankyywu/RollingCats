# 喵言机 Meowracle Machine

让猫在键盘上滚一圈，把乱码破译成你的下一个产品创意。

这是一个本地运行的趣味 Demo：前端负责捕捉猫踩键盘产生的随机字符，服务端把字符映射到「AI 黑话 × 社会情绪词 × 资本叙事」三池词库，再调用 NVIDIA API 生成一个可执行的产品创意。没有配置 API key 时，也会自动使用浏览器内置的本地兜底引擎。

<img width="1488" height="1070" alt="Screenshot 2026-05-28 at 14 33 18" src="https://github.com/user-attachments/assets/f7bd548e-c843-4aa6-9809-b45a492ddda2" />


## 功能

- 像素猫选择器：不同猫代表不同创意风格和界面主题。
- 实时键盘捕捉：把猫踩出的字符流变成随机种子。
- 三池词库破译：从技术锚点、社会情绪、资本叙事中召唤概念。
- AI 创意生成：通过 NVIDIA 兼容接口生成结构化产品创意。
- 本地兜底模式：服务端或 API key 不可用时仍可演示。


https://github.com/user-attachments/assets/b78530e8-a218-44ab-9b8b-ffe8026e2770



## 运行

需要 Python 3，无需安装额外依赖。

```bash
python3 server.py
```

然后打开：

```text
http://localhost:8000/
```

也可以直接打开 `index.html` 体验本地兜底模式，但浏览器无法直接读取服务端环境变量，因此不会启用 AI 破译。

## 配置 NVIDIA API

推荐使用环境变量：

```bash
export NVIDIA_API_KEY="你的 API key"
python3 server.py
```

也可以在项目根目录创建 `.nvidia_key`，或在用户目录创建 `~/.nvidia_key`。项目已通过 `.gitignore` 忽略本地密钥文件，请不要把真实 key 提交到仓库。

可选环境变量：

```bash
export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
export NVIDIA_MODEL="meta/llama-3.3-70b-instruct"
export PORT="8000"
```

## 项目结构

```text
index.html   页面结构、像素猫、交互逻辑
styles.css   像素风界面样式
oracle.js    浏览器端本地兜底创意引擎
server.py    静态文件服务 + NVIDIA API 代理
```

## 注意

本项目生成的产品创意仅供娱乐和灵感发散，不构成商业建议。猫不为融资失败负责。
