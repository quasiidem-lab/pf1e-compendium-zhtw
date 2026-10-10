# -*- coding: utf-8 -*-
r"""從繁中模組產生簡體模組（pf1e-compendium-zhcn）的程式碼與樣式。

    python _build/make_zhcn.py

程式碼只有繁中版一份正本（scripts/、styles/），這支轉成簡體字、換掉模組代號與語言代碼，
寫進旁邊的 pf1e-compendium-zhcn/。改了繁中版的程式碼就重跑這支，不要直接改簡體那份。
譯文由 build_chm.py 寫（上游簡體稿＋CHM 簡體版），這支不碰 translations/。

module.json、README.md、NOTICE.md 是簡體模組自己手寫的，這支也不碰。

壞掉時：簡體模組在 Foundry 不翻譯 → 看 REPLACE 的語言代碼是否還對得上 Babele 的語言（簡體核心翻譯用 cn）。
"""
import shutil, sys
from pathlib import Path
import opencc

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
SRC = HERE.parent
DST = SRC.parent / 'pf1e-compendium-zhcn'

# 字串替換（在轉簡體之後做）；每條都要命中，沒命中代表繁中版改了寫法，要回來看
REPLACE = {
    'scripts/babele.js': [
        ('const MODULE_ID = "pf1e-compendium-zhtw";', 'const MODULE_ID = "pf1e-compendium-zhcn";'),
        ('lang: "zh-tw",', 'lang: "cn",'),
        ('game.settings.get("core", "language") !== "zh-tw"', 'game.settings.get("core", "language") !== "cn"'),
        ('pf1e-compendium-zhtw — 向 Babele 注册繁体中文合集包对照表。',
         'pf1e-compendium-zhcn — 向 Babele 注册简体中文合集包对照表（由繁中版 make_zhcn.py 产生，勿直接修改）。'),
    ],
}
FILES = ['scripts/babele.js', 'scripts/converters.js', 'scripts/filters.mjs',
         'styles/compendium-browser-filter.css']
COPY = ['LICENSE', 'OGL.txt']


def main():
    if not DST.exists():
        sys.exit(f'找不到 {DST}')
    cc = opencc.OpenCC('tw2s')
    miss = []
    for rel in FILES:
        t = cc.convert((SRC / rel).read_text(encoding='utf-8'))
        for old, new in REPLACE.get(rel, []):
            if old not in t:
                miss.append(f'{rel}: {old}')
            t = t.replace(old, new)
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(t, encoding='utf-8', newline='\n')
        print('寫入', out)
    for rel in COPY:
        shutil.copy2(SRC / rel, DST / rel)
    hits = sum(len(v) for v in REPLACE.values()) - len(miss)
    print(f'替換 {hits} 條命中，{len(miss)} 條沒命中')
    for m in miss:
        print('  沒命中：', m)
    sys.exit(1 if miss else 0)


if __name__ == '__main__':
    main()
