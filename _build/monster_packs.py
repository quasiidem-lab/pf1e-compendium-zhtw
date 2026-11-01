# -*- coding: utf-8 -*-
r"""產 PF1 系統三個怪物相關合集包的名稱對照檔：怪物模板、模板能力、怪物能力。

    python _build/monster_packs.py                 # 照譯名表寫 translations/（繁）＋ _build/審核/zhcn/（簡）
    python _build/monster_packs.py --pack <路徑>    # 另外比對 pf1 原始碼的 packs/ 目錄，確認每個鍵都存在

譯名表是 `_build/怪物合集包譯名.tsv`（Excel 可開），一列一條：
  「譯名」欄有值才寫進對照檔，空白的留英文。要補、要改，直接改這一欄再重跑本支。
  「來源」「說明」「上游寫法」「CHM寫法」「既有對照檔寫法」是 2026-11-01 比對時留下的依據，改譯名時順手更新來源。

**譯名不自己翻**，來源只收 CHM、本模組既有對照檔、上游 fvtt-cn 簡體稿（簡轉繁），CHM 優先。
上游只有一個來源的，要 CHM 裡找得到同一個詞才收（上游把巫妖模板譯成「活屍化」、
Entothrope 譯成「蟲化人緒論」這類錯，靠這條擋）。

只翻名稱與資料夾名，不翻內文：上游怪物模板的內文多半只有一行標題，蓋上去會把英文內文變空白。
mapping 不寫，用 Babele 內建的 Item 對應；上游 mapping 裡的 tags 轉換器本模組沒有，不沿用。
名稱重複的條目（例如模板能力裡三個 Change Shape）用文件 ID 當鍵，Babele 會先比對 ID。
"""
import argparse, csv, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
TABLE = HERE / '怪物合集包譯名.tsv'
OUT_TW = HERE.parent / 'translations'
OUT_CN = HERE / '審核' / 'zhcn'

PACKS = {   # 代號 → 合集包名稱（繁, 簡）
    'monster-templates': ('怪物模板', '怪物模板'),
    'template-abilities': ('模板能力', '模板能力'),
    'monster-abilities': ('怪物能力', '怪物能力'),
}
NAME_FMT = '{zh}（{en}）'   # 跟職業特性等其他 Item 合集包一樣


def load_table():
    with open(TABLE, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def build(rows, pack, lang, conv):
    entries, folders = {}, {}
    for r in rows:
        if r['代號'] != pack or not r['譯名'].strip():
            continue
        zh = conv(r['譯名'].strip())
        if r['合集包'].endswith('（資料夾）'):
            folders[r['英文']] = zh
        else:
            entries[r['鍵']] = {'name': NAME_FMT.format(zh=zh, en=r['英文'])}
    d = {'label': PACKS[pack][0 if lang == 'zh-tw' else 1]}
    if folders:
        d['folders'] = dict(sorted(folders.items()))
    d['entries'] = dict(sorted(entries.items()))
    return d


def pack_keys(pack_dir, pack):
    """pf1 原始碼 packs/<pack>/*.yaml → 可用的鍵（文件 ID 與名稱）與資料夾名稱。"""
    keys, folders = set(), set()
    for p in Path(pack_dir, pack).glob('*.yaml'):
        t = p.read_text(encoding='utf-8')
        key = re.search(r"^_key:\s*'?!(\w+)!", t, re.M).group(1)
        name = re.search(r'^name:\s*(.+)$', t, re.M).group(1).strip().strip('\'"')
        if key == 'folders':
            folders.add(name)
        else:
            keys.add(name)
            keys.add(re.search(r'^_id:\s*(\S+)', t, re.M).group(1))
    return keys, folders


def save(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('寫入', path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', help='pf1 原始碼的 packs 目錄，給了就檢查每個鍵都對得上')
    a = ap.parse_args()
    rows = load_table()

    if a.pack:
        bad = []
        for pack in PACKS:
            keys, folders = pack_keys(a.pack, pack)
            for r in rows:
                if r['代號'] != pack:
                    continue
                ok = r['英文'] in folders if r['合集包'].endswith('（資料夾）') else r['鍵'] in keys
                if not ok:
                    bad.append(f"{pack}: {r['鍵']}")
        if bad:
            print('譯名表裡有對不上 pf1 原始碼的鍵：')
            for b in bad:
                print('  ', b)
            sys.exit(1)
        print('譯名表的鍵全部對得上 pf1 原始碼')

    import opencc
    tw2s = opencc.OpenCC('tw2s').convert
    for pack in PACKS:
        tw = build(rows, pack, 'zh-tw', lambda s: s)
        save(OUT_TW / f'pf1.{pack}.json', tw)
        save(OUT_CN / f'pf1.{pack}.json', build(rows, pack, 'zh-cn', tw2s))
        total = sum(1 for r in rows if r['代號'] == pack)
        done = len(tw['entries']) + len(tw.get('folders', {}))
        print(f'  {PACKS[pack][0]}：{done}／{total} 條有譯名')


if __name__ == '__main__':
    main()
