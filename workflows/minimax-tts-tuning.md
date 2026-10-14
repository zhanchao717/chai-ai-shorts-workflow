# MiniMax TTS 自然度调法指南（2026-09-06 调研）

调研来源：MiniMax t2a_v2 官方参数 schema（novita/docs 镜像）、GitHub 实测代码（AstrBot / openclaw-master-skills / logancyang-minimax-tts-skill / YangAgent-pipeline）、本仓库 scripts/minimax_tts.py（已扩展支持以下全部参数）。

## 参数杠杆（按对「去 AI 味」的贡献排序）

| 杠杆 | 用法 | 原理 |
|---|---|---|
| **情绪自动匹配** | `--emotion-auto`（省略 emotion 参数） | 官方 schema 原话「模型会根据输入文本自动匹配合适的情绪，一般无需手动指定」——每期固定 calm 是播报腔来源之一 |
| **情绪 fluent** | `--emotion fluent` | 「生动」模式，speech-2.8-hd 支持（whisper 不支持 2.8）；比 calm 有人味 |
| **language_boost=auto** | `--language-boost auto` | 自动检测语言；中英混排（HydraFusion/Ollama 等）英文段更自然。当前默认 Chinese 会压英文质感 |
| **english_normalization** | `--english-normalization` | 英文规范化，数字/缩写读法更顺（略增延迟） |
| **停顿标记** | 台词内插 `<#x#>`，x=秒数（如 `不达标<#0.3#>再升级`） | 手动控制节奏停顿；⚠️ 未与 build_chai_timeline 字幕管线验证兼容，用前先测词级 JSON 是否被污染 |
| **音色混合** | `--timber-weights '[{"voice_id":"...","weight":1},...]'` | 多音色叠加去模板感；**voice_id 仍必填**（与 timber 并存叠加）；权重整数 |
| **换音色** | `--voice-id presenter_male / audiobook_male_1 / male-qn-jingying` | 系统音色列表还包括 presenter/audiobook 系；换音色是最直接的差异化 |
| **音色克隆** | voice_clone 接口：10s–5min 参考音频 → 自定义 voice_id（7 天活跃保留）；需 MINIMAX_GROUP_ID | 最彻底的去 AI 味——用用户自己的声音；参考音频 mp3/m4a/wav ≤20MB |
| **pitch/speed 微调** | `--pitch -2..2` / `--speed 1.0` | speed 1.08 偏快损自然度，可试 1.0；pitch 小幅偏离默认 |

## 久经确认的 API 细节

- emotion 全集：happy/sad/angry/fearful/disgusted/surprised/neutral/calm/**fluent**/whisper（whisper 不支持 speech-2.8）。
- `timber_weights` 为顶层参数，与 `voice_setting.voice_id` **并存叠加**（2.8 上 voice_id 必填）。
- `english_normalization`、`latex_read`、`text_normalization` 均在 voice_setting 内。
- voice clone 需 `MINIMAX_GROUP_ID`（Keychain 未存，用时向用户要）。

## 本仓库现状与 A/B 样音

- `scripts/minimax_tts.py` 已支持上述全部参数（--emotion-auto / --language-boost / --english-normalization / --timber-weights / --emotion fluent）。
- 试听样音：`content/tts-ab-20260906/`（同一句 EP.131 L2 台词，6 版）：
  A 现状基线（calm+Chinese）｜B 自动情绪｜C 自动情绪+auto 语言｜D fluent+规范化｜E1 音色混合（qingse+jingying）｜F presenter_male。
- 用户选定后把胜出参数写入本文件与每期 SCRIPT.md 的 Voice settings 行。
