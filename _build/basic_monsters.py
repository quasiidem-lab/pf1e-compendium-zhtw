# -*- coding: utf-8 -*-
r"""產 pf1.basic-monsters（PF1 系統內建「基本怪物」合集包）的名稱對照檔。

    python _build/basic_monsters.py                 # 寫 translations/pf1.basic-monsters.json（繁）＋簡體稿
    python _build/basic_monsters.py --pack <路徑>    # 另外比對 pf1 原始碼 packs/basic-monsters 的條目清單

這包在 PF1 11.11 只有 15 條（系統開場導覽用的示範怪），跟八個 pf1-bestiary.* 是兩回事：
那八檔對的合集包在 11.11 不存在，Foundry 裡的怪物在這包與 statblock-library。

**譯名不自己翻**。NAMES 每一列都寫了來源，只收三種：
  CHM   果園 CHM 裡提到這隻怪的寫法（CHM 沒有逐隻怪物頁，取召喚表、魔寵表、專長、物品裡的提及）
  上游  fvtt-cn/pf1e_compendium_chn 的 pf1.basic-monsters.json（2026-10-18 起才有），簡轉繁
  舊檔  本模組 pf1-bestiary.* 裡英文名完全相同的條目
CHM 優先（2026-10-10 定）。三處都沒有的留英文，列在 MISSING，等用語集補。

只翻名稱（name、token 名稱），不翻內文與怪物身上的物品：
上游有物品名，但有錯（怪物的 Poison 能力譯成法術「毒擊術」、Enchanting Smile 譯成「惑控學派」），不收。

mapping 不寫，用 Babele 內建的 Actor 對應（name → name、tokenName → prototypeToken.name），
不會指到 converters.js 裡沒定義的轉換器。

簡體稿寫到 _build/審核/zhcn/，要放進 pf1e-compendium-zhcn 時手動複製到它的 translations/。
"""
import argparse, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
OUT_TW = HERE.parent / 'translations' / 'pf1.basic-monsters.json'
OUT_CN = HERE / '審核' / 'zhcn' / 'pf1.basic-monsters.json'

LABEL = {'zh-tw': '基礎怪物', 'zh-cn': '基础怪物'}   # 上游的合集包名稱
NAME_FMT = '{zh}（{en}）'   # 跟 pf1-bestiary.* 一樣

# 英文鍵：(繁, 簡, 來源)
# 繁體是簡體走 CHM 線同一套轉換（s2tw＋tc_例外.tsv）得到的，這裡直接寫死，不在建置時再轉
NAMES = {
    'Fire Beetle':     ('火甲蟲', '火甲虫', 'CHM'),
    'Goblin':          ('地精', '地精', 'CHM'),
    'Homunculus':      ('人造人', '人造人', 'CHM'),
    'Human Skeleton':  ('人類骷髏', '人类骷髅', 'CHM'),
    'Human Zombie':    ('人類喪屍', '人类丧尸', 'CHM'),
    'Orc':             ('獸人', '兽人', 'CHM'),
    'Stirge':          ('蚊蝠', '蚊蝠', 'CHM'),
    'Wasp Swarm':      ('黃蜂群', '黄蜂群', 'CHM'),
    'Wolf':            ('狼', '狼', 'CHM'),
    'Acolyte':         ('侍祭', '侍祭', '上游'),
    'Battle Mage':     ('戰鬥法師', '战斗法师', '上游'),
    'Poacher':         ('偷獵者', '偷猎者', '上游'),
    'Street Magician': ('街頭魔術師', '街头魔术师', '上游'),
}
# 三處都找不到譯名的：留英文，不寫進對照檔
MISSING = ['Goblin Alchemist', 'Human Bandit']


def build(lang):
    i = 0 if lang == 'zh-tw' else 1
    entries = {}
    for en in sorted(NAMES):
        zh = NAMES[en][i]
        entries[en] = {'name': NAME_FMT.format(zh=zh, en=en), 'tokenName': zh}
    return {'label': LABEL[lang], 'entries': entries}


def pack_names(pack):
    """pf1 原始碼的 packs/basic-monsters/*.yaml → 頂層 name（不讀物品的 name）。"""
    out = set()
    for p in Path(pack).glob('*.yaml'):
        m = re.search(r'^name:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            out.add(m.group(1).strip().strip('\'"'))
    return out


def save(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('寫入', path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', help='pf1 原始碼的 packs/basic-monsters 目錄，給了就比對條目清單')
    a = ap.parse_args()

    if a.pack:
        src = pack_names(a.pack)
        ours = set(NAMES) | set(MISSING)
        if src != ours:
            print('條目清單對不上 pf1 原始碼：')
            for n in sorted(src - ours):
                print('  原始碼有、這裡沒有：', n)
            for n in sorted(ours - src):
                print('  這裡有、原始碼沒有：', n)
            sys.exit(1)
        print(f'條目清單與 pf1 原始碼一致（{len(src)} 條）')

    save(OUT_TW, build('zh-tw'))
    save(OUT_CN, build('zh-cn'))
    by = {}
    for _, _, s in NAMES.values():
        by[s] = by.get(s, 0) + 1
    print(f'已補 {len(NAMES)} 條（' + '、'.join(f'{k} {v}' for k, v in by.items()) + f'），沒補 {len(MISSING)} 條')


if __name__ == '__main__':
    main()
