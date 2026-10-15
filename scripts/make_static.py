"""Build the public GitHub Pages version (docs/index.html) from src/sponsor-finder.html.

The claude.ai Artifact host wraps the page in its own <head>; GitHub Pages does not,
so this adds the document skeleton and the small reset the page relies on.
Google Fonts are dropped here because fonts.googleapis.com is blocked in mainland China
and would stall the first paint; the page's font stacks fall back to system fonts.

Usage: python3 scripts/make_static.py
"""
import re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "sponsor-finder.html").read_text(encoding="utf-8")

# Drop Google Fonts (preconnect + stylesheet).
body = re.sub(r'<link[^>]+fonts\.(googleapis|gstatic)\.com[^>]*>\s*', "", src)

# Pull <title> and the claude viewport meta out so they can live in <head>.
title = re.search(r"<title>.*?</title>", body, re.S).group(0)
body = body.replace(title, "", 1)
body = re.sub(r'<meta name="claude:viewport-fit-sides"[^>]*>\s*', "", body)

head = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{title}
<meta name="description" content="按行业、城市、签证路线筛选英国 gov.uk 持牌工签担保雇主，附官网、招聘页、LinkedIn 和 Companies House 链接。每日自动更新。">
<style>
:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}
body{{margin:0;font:14px system-ui,-apple-system,sans-serif}}
img{{max-width:100%}}
[hidden]{{display:none!important}}
</style>
</head>
<body>
"""
out = head + body.strip() + "\n</body>\n</html>\n"
(ROOT / "docs" / "index.html").write_text(out, encoding="utf-8")
print("wrote docs/index.html", len(out), "bytes")
