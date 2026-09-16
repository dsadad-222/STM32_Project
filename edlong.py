#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edlong.py —— 和 edsdk.py call 等价，但把 HTTP 超时放宽到 300s。

doc_to_image 这类要上传/云端转换的工具，30s 默认超时不够。
用法:
    python3 edlong.py call <工具名> --json-file args.json
"""
import json
import os
import sys
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import edsdk  # noqa: E402

_real_request = edsdk._request


def _slow_request(endpoint, method, params=None, timeout=30):
    return _real_request(endpoint, method, params, timeout=300)


edsdk._request = _slow_request


def main(argv):
    if len(argv) < 3 or argv[1] != "call":
        print("用法: python3 edlong.py call <工具名> [--json-file x.json] [--json '{...}'] [k=v ...]")
        return 2
    tool = argv[2]
    arguments = {}
    i = 3
    while i < len(argv):
        a = argv[i]
        if a == "--json-file":
            with open(argv[i + 1], "r", encoding="utf-8") as f:
                arguments.update(json.load(f))
            i += 2
        elif a == "--json":
            arguments.update(json.loads(argv[i + 1]))
            i += 2
        elif "=" in a:
            k, v = a.split("=", 1)
            try:
                arguments[k] = json.loads(v)
            except json.JSONDecodeError:
                arguments[k] = v
            i += 1
        else:
            print(f"无法解析的参数: {a!r}")
            return 2
    try:
        result = edsdk._rpc("tools/call", {"name": tool, "arguments": arguments})
    except SystemExit as e:
        return e.code
    texts = [c.get("text", "") for c in (result.get("content") or [])
             if isinstance(c, dict) and c.get("type") == "text"]
    print("\n".join(texts) if texts else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
