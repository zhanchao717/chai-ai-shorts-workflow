#!/usr/bin/env python3
"""③ 档「GitHub 涨星榜」系列格式门禁（A 方案，2026-09-13 起）。

背景：对标「开源情报局 GitHub 周榜 EP5」（实测 45.2s / 8 条 / 每条 5.2s / 纯卡片）后，
用户裁决走 **A 方案** —— 保留我们 ③ 档（90–180s）结构不变，只改三件事：
  1. **每条口播 = 「第 N 名 + 你能拿它干什么」句式**（对方最值钱的一条；
     对方示例：「第八名，想要什么零件直接说」「第六名，直接给AI配个营销部」）；
  2. **涨星数成为视觉主角**（卡片上最大字号，画面另一套自检在 frames 侧）；
  3. **系列标识带集数 `EP n`**。
本脚本把 1 和 3（以及口播的其它硬规矩）变成**可机检**的门禁，2 由 frames 侧字号断言覆盖。

用法：
  python3 scripts/chai_rank_series_check.py --script <SCRIPT.md> --spec specs/178.json [--ep 178]
退出码：0 = PASS；1 = FAIL（有任何一条硬项不满足）
"""
from __future__ import annotations
import argparse, json, re, sys

# 口播禁项（沿用《抖音开头达标规范》的黑名单，只查开场句）
OPEN_BAN = ["大家好", "今天给大家", "最近", "我是柴主编", "hello", "哈喽"]

# 名次句式：句首 12 字内出现「第 N 名」（中文数字或阿拉伯数字）
RANK = re.compile(r"^.{0,12}?第\s*[0-9一二三四五六七八九十百]+名")
# 「能干啥」信号：动作/用途词
CAN_DO = re.compile(r"能|可以|用来|直接|帮你|给你|做|生成|画|查|装|下载|搞定|搞定|省|提升|换|管")
# 精确大数（4 位以上连写或带千分位）——口播里应改成口语化数字
EXACT_BIG = re.compile(r"\d{4,}|\d{1,3},\d{3}")
# 口语化数字
COLLOQ_NUM = re.compile(
    r"九成|八成|一半|两倍|三倍|一倍|几倍|万|千|百|几十|几百|几千|几万|几十万|"
    r"分钟|小时|秒钟|秒|步|张|条|个|件|遍|轮|成")


def parse_script(path: str) -> list[tuple[str, str]]:
    """SCRIPT.md 的 `NN.txt：口播` 缩进行 → [(编号, 文本)]。"""
    out = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"^\s*(\d{2})\.txt[：:]\s*(.+?)\s*$", ln)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def flatten_spec(path: str):
    d = json.load(open(path, encoding="utf-8"))
    scenes = []
    if d.get("chapters"):
        for c in d["chapters"]:
            for k, v in (c.get("scenes") or {}).items():
                scenes.append((k, v))
    else:
        for k, v in (d.get("scenes") or {}).items():
            scenes.append((k, v))
    return d, scenes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--ep", default="")
    a = ap.parse_args()

    lines = parse_script(a.script)
    spec, scenes = flatten_spec(a.spec)
    fails, warns, oks = [], [], []

    # ---------- 1. 系列标识 EP n ----------
    blob = json.dumps(spec, ensure_ascii=False) + open(a.script, encoding="utf-8").read()
    ep_hits = re.findall(r"EP\s*\d+", blob)
    if ep_hits:
        oks.append(f"系列标识：找到 {sorted(set(ep_hits))}")
    else:
        fails.append("系列标识：全篇找不到 `EP n`（A 方案要求每条/首帧带集数；对标账号用「EP5」做系列感）")

    # ---------- 2. 开场禁项 ----------
    if lines:
        first = lines[0][1]
        hit = [w for w in OPEN_BAN if w in first]
        if hit:
            fails.append(f"开场句话（{lines[0][0]}）含禁项 {hit}：{first[:30]}…")
        else:
            oks.append("开场句无铺垫禁项")

    # ---------- 3. 条目口播句式 ----------
    item_lines = [(n, t) for n, t in lines if RANK.search(t)]
    if not item_lines:
        fails.append("条目句式：没有任何一句是以「第 N 名…」开头的 —— A 方案的核心句式未落地")
    for i, (n, t) in enumerate(item_lines):
        # 3a 句首给名次（RANK 已保证）；3b 同句要能看出「能干啥」
        if not CAN_DO.search(t):
            fails.append(f"[{n}] 缺「能干啥」信号（对方句式：`第八名，想要什么零件直接说`）：{t[:42]}…")
        else:
            oks.append(f"[{n}] 名次 + 能干啥 ✓")
        # 3c 口播里不许出现精确大数（应口语化）
        m = EXACT_BIG.search(t)
        if m:
            fails.append(f"[{n}] 口播出现精确大数「{m.group(0)}」→ 口播要口语化（一万六/九成八/快三十万星），精确值留给画面：{t[:42]}…")
        # 3d 每条最后一句要有口语化量化收尾
        nxt = lines[lines.index((n, t)) + 1][1] if lines.index((n, t)) + 1 < len(lines) else ""
        if not COLLOQ_NUM.search(t + nxt):
            fails.append(f"[{n}] 附近缺口语化收尾数字（对方示例：`五十个技能随叫随到`、`这组测试省了九成八`）：{t[:42]}…")
    if item_lines:
        oks.append(f"条目句式：共识别 {len(item_lines)} 条名次句")

    # ---------- 4. 卡片侧：条目场要有大数字 + repo ----------
    facts = [(k, v) for k, v in scenes if "repo_big" in v or "tag_a" in v]
    if not facts:
        warns.append("卡片：spec 里没有找到条目卡场景（字段 repo_big/tag_a）—— 若本期不是榜单形态可忽略")
    else:
        for k, v in facts:
            miss = [f for f in ("repo_big", "tag_a") if not v.get(f)]
            if miss:
                fails.append(f"[{k}] 条目卡缺字段 {miss}（A 方案：涨星数当视觉主角 + repo 路径可搜）")
        oks.append(f"卡片：{len(facts)} 张条目卡都有大数字与 repo 字段")

    # ---------- 输出 ----------
    print("③ 档 GitHub 涨星榜 · A 方案格式门禁")
    print(f"  口播 {len(lines)} 句 · spec 场 {len(scenes)} 个 · 条目句 {len(item_lines)} 条\n")
    for s in oks:
        print(f"  ✅ {s}")
    for s in warns:
        print(f"  ℹ️  {s}")
    for s in fails:
        print(f"  ❌ {s}")
    verdict = "PASS" if not fails else "FAIL"
    print(f"\n结论：{verdict}（❌ {len(fails)} · ℹ️ {len(warns)}）")
    if fails:
        print("→ A 方案要求「第 N 名 + 你能拿它干什么」+ 口语化数字收尾 + `EP n` 集数；**改稿后重跑本门禁**。")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
