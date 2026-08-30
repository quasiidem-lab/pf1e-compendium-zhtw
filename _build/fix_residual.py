# -*- coding: utf-8 -*-
"""只把 translations/ 裡未轉換的簡體字轉成正體，其餘一律不動。

為什麼不用 build_compendium.py 重建：
  現行 translations/ 不是純管線產出，裡面有大量人工修訂的台灣用詞——
  訊息（上游：消息/信息）、目前（當前）、範本（模板）、儲存（保存）、
  搜尋（搜索）、設定陷阱（設置陷阱）等，共約 455 條。
  重建會忠實照上游轉換，把這些修訂全部蓋回大陸用詞。

因此這支腳本只做一件事：對「純字形轉換後會改變、且該字確實是簡體」的
字元做替換，不套任何用語替換表，也不碰已經是正體的字。

保護：HTML 標籤、@ 連結的文件 ID、網址內部一律不動
（`#TOC-黑暗视觉` 是 d20pfsrd 錨點，轉了連結會失效）。
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
import opencc

HERE = os.path.dirname(os.path.abspath(__file__))
TR_DIR = os.path.join(os.path.dirname(HERE), 'translations')

cc = opencc.OpenCC('s2tw')

# 不可轉換的片段：HTML 標籤、@連結的 ID、HTML 實體
PLACEHOLDER = re.compile(
    r'(@[A-Za-z][\w]*\[[^\]]*\]'
    r'|</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>'
    r'|&[a-zA-Z]+;|&#\d+;)'
)
# 裸網址（不在標籤裡的），內部不轉：#TOC-黑暗视觉 是 d20pfsrd 錨點
URL = re.compile(r'https?://[^\s"<>]+')

# OpenCC 一對多映射：這些字在正體中文裡本來就通用，不是殘簡
AMBIGUOUS = set('了干伙面岩制注占並并复余系历钟表'
                '斗厘采征凶仆回辟只游划念')


def convert_segment(seg):
    """逐字轉換，只動真正的簡體字。"""
    conv = cc.convert(seg)
    if conv == seg or len(conv) != len(seg):
        return seg
    return ''.join(
        b if a != b and a not in AMBIGUOUS else a
        for a, b in zip(seg, conv)
    )


def fix(text):
    """先切標籤再切網址，兩者內部都不動。

    順序很重要：標籤要先切開，否則 <a href="...中文..."> 的屬性值
    會被當成一般文字轉換掉（來源的 Demand 法術就有這種破損網址），
    驗證會判定 HTML 標籤遭竄改。
    """
    if not isinstance(text, str) or not text:
        return text, 0

    result = []
    for seg in PLACEHOLDER.split(text):
        if not seg:
            continue
        if PLACEHOLDER.fullmatch(seg):
            result.append(seg)          # 標籤／連結 ID，整段保留
            continue
        # 標籤外的文字：裸網址仍要保護
        pos = 0
        for m in URL.finditer(seg):
            result.append(convert_segment(seg[pos:m.start()]))
            result.append(m.group(0))
            pos = m.end()
        result.append(convert_segment(seg[pos:]))

    new = ''.join(result)
    return new, (1 if new != text else 0)


def walk(node):
    n = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'mapping':
                continue
            node[k], c = walk(v)
            n += c
        return node, n
    if isinstance(node, list):
        for i, v in enumerate(node):
            node[i], c = walk(v)
            n += c
        return node, n
    if isinstance(node, str):
        return fix(node)
    return node, 0


if __name__ == '__main__':
    total = 0
    touched = []
    for fn in sorted(os.listdir(TR_DIR)):
        if not fn.lower().endswith('.json'):
            continue
        p = os.path.join(TR_DIR, fn)
        raw = io.open(p, encoding='utf-8-sig').read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = json.loads(re.sub(r',(\s*[}\]])', r'\1', raw))

        data, n = walk(data)
        if n:
            io.open(p, 'w', encoding='utf-8').write(
                json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            touched.append((fn, n))
            total += n

    for fn, n in touched:
        print(f'  {fn:<40}{n}')
    print()
    print(f'修正字串數: {total}')
