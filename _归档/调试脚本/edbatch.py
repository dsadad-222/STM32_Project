#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edbatch.py —— 顺序执行一批 editor_sdk MCP 调用。

用法:
    python3 edbatch.py ops.json

ops.json 格式:
    [ {"tool": "doc_replace_text", "args": {...}}, ... ]
每个元素执行一次 tools/call，结果逐条打印；单条失败会记为 FAILED 但继续执行，
最后汇总退出码（有失败则 1）。
"""
import json
import os
import sys

HERE = r"D:\.Download\WorkBuddy\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\tencent-local-office-edit"
sys.path.insert(0, HERE)

import edsdk  # noqa: E402

_real = edsdk._request
edsdk._request = lambda ep, m, p=None, timeout=30: _real(ep, m, p, timeout=300)


def main(path):
    ops = json.load(open(path, "r", encoding="utf-8"))
    bad = 0
    for i, op in enumerate(ops):
        tool, args = op["tool"], op.get("args", {})
        try:
            res = edsdk._rpc("tools/call", {"name": tool, "arguments": args})
            texts = [c.get("text", "") for c in (res.get("content") or [])
                     if isinstance(c, dict) and c.get("type") == "text"]
            out = "\n".join(texts) if texts else json.dumps(res, ensure_ascii=False)
            tag = "ok"
        except SystemExit:
            out, tag = "(调用失败，见上一行 stderr)", "FAILED"
            bad += 1
        preview = out.replace("\n", " ")[:180]
        print(f"[{i+1}/{len(ops)}] {tag} {tool} :: {preview}")
    print(f"\n共 {len(ops)} 条，失败 {bad} 条")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
