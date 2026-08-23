# -*- coding: utf-8 -*-
"""建置 PF1 合集包（Babele）正體中文對照表。

與 pf1-zhtw（介面層）的差異：
  介面層是扁平的 鍵->字串；合集層是 Babele 對照表，結構有三種東西混在同一份
  JSON 裡，其中兩種**不可轉換**：

    entries 的「鍵」  = 英文原名，Babele 靠它比對合集包項目，動了就查不到
    mapping 的「值」  = Foundry 欄位路徑（system.actions / token.name）與
                        converter 名稱，動了 Babele 直接壞掉
    其餘字串          = 真正的譯文，要轉

因此走遞迴，並在遞迴時帶著「這個節點該不該轉」的旗標，不採欄位白名單
（actions/results/pages 之類的巢狀結構會漏掉）。

術語處理沿用 pf1-zhtw/_build/build_zhtw.py 的 TERM_MAP 與 PROTECTED，
兩層譯名必須一致，不各自維護一份。

來源：pf1e_compendium_chn (FVTT-CN)。**該專案無授權聲明**，
產出物僅供本機使用，取得作者授權前不得散布。見 README「授權現況」。
"""
import json, os, re, sys
from collections import OrderedDict

sys.stdout.reconfigure(encoding='utf-8')
import opencc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), 'translations')
DATA = r'C:\Users\User\AppData\Local\FoundryVTT\Data'
SRC_DIR = os.path.join(DATA, 'modules', 'pf1e_compendium_chn', 'translations')

# 介面層的術語表就是正本，從那邊 import，不複製一份。
# 正本在 D 槽的工作資料夾，不是 Foundry 的 modules 底下——
# modules/pf1-zhtw 只有建置產物（lang/zh-tw.json），沒有 _build/。
IFACE_BUILD = r'D:\TRPG\4_工具與筆記\pf1-zhtw\_build'
sys.path.insert(0, IFACE_BUILD)
try:
    from build_zhtw import TERM_MAP, PROTECTED
except ImportError:
    print(f'找不到介面層術語表，預期路徑：{IFACE_BUILD}\\build_zhtw.py')
    raise

# ---------------------------------------------------------------
# 不可轉換的片段（合集層專用，**不沿用介面層的 PLACEHOLDER**）
#
# 介面層那份把 `{...}` 整組保護起來，因為介面字串的大括號是 Foundry 插值
# 變數（`{value} gp`）。合集層相反：這裡的大括號幾乎都是中文內容——
#   3,119 個 @Compendium[...]{中文名} 的顯示標籤
#   180 個 {2+智力修正} 這類規則算式
# 沿用介面層那份會把這 3,299 處全部留在簡體。
#
# 真正不能動的是文件 ID：@Compendium[pf1.spells.8jqq8kxdzx01ogl9] 的方括號
# 內容。因此只保護「@方案名[ID]」與 HTML 標籤，把後面的 {顯示標籤} 留給轉換。
# ---------------------------------------------------------------
# HTML 標籤要「真的是標籤」才保護。來源裡有 21 處長得像標籤但不是：
#   <水晶球 (crystal ball)>  這類用角括號當引號的物品名（18 處）
#   <p被壓制的生物…         漏打 > 的破損標籤（3 處）
# 用 `<[^>]+>` 會把這些連同後面的中文一起當標籤保護起來，那段就留在簡體。
# 因此限定「</?標籤名 …>」的形狀。
PLACEHOLDER = re.compile(
    r'(@[A-Za-z][\w]*\[[^\]]*\]'          # @Compendium[...] / @UUID[...] 的 ID
    r'|</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>'   # 真正的 HTML 標籤
    r'|&[a-zA-Z]+;|&#\d+;)'               # HTML 實體（&emsp; 等）
)


cc = opencc.OpenCC('s2tw')  # 只轉字形，用語替換交給 TERM_MAP

# ---------------------------------------------------------------
# 合集層額外的術語：規則書內文才會出現的詞，介面層用不到
# 一樣是長詞在前
# ---------------------------------------------------------------
EXTRA_TERMS = OrderedDict([
    ('豁免检定', '豁免檢定'),
    ('攻击检定', '攻擊檢定'),
    ('技能检定', '技能檢定'),
])

# 合集層額外的保護詞：PF1 規則術語，替換表不得動到
# 一律寫繁體（下面不再做 cc.convert），與 PROTECTED 的體例一致
EXTRA_PROTECTED = [
    '法術',
    '專長',
    '同伴',
    '構裝',
    '衝鋒',
    '借機攻擊',
    '威能',
]

ALL_TERMS = OrderedDict(list(TERM_MAP.items()) + list(EXTRA_TERMS.items()))
ALL_PROTECTED = list(PROTECTED) + EXTRA_PROTECTED


def load_lenient(path):
    """來源有一份檔案帶尾逗號（Foundry 的載入器容忍，strict json 不容忍）。"""
    text = open(path, encoding='utf-8-sig').read()
    try:
        return json.loads(text), False
    except json.JSONDecodeError:
        repaired = re.sub(r',(\s*[}\]])', r'\1', text)
        return json.loads(repaired), True


def convert(text):
    """字形轉換 + 用語替換，保護插值變數、HTML 標籤與 @ 參照。"""
    if not isinstance(text, str) or not text:
        return text
    parts = PLACEHOLDER.split(text)
    out = []
    for seg in parts:
        if PLACEHOLDER.fullmatch(seg or ''):
            out.append(seg)          # 原樣保留
            continue
        s = cc.convert(seg)
        for a, b in ALL_TERMS.items():
            s = s.replace(a, b)
        out.append(s)
    return ''.join(out)


# 統計
stats = {'converted': 0, 'skipped_key': 0, 'skipped_mapping': 0}
protected_hits = []


def check_protected(before, after):
    """只抓「保護詞在純字形轉換後存在、卻被替換表弄不見」的情形。

    比對的是出現次數而非有無：同一段文字裡「法術」可能出現多次，
    只要有一次被替換表吃掉就算誤傷。逐段比較才不會被其他位置的同詞掩蓋。
    """
    plain = cc.convert(before)
    for p in ALL_PROTECTED:
        if plain.count(p) > after.count(p):
            protected_hits.append((p, plain, after))
            break


def walk(node, translate=True):
    """遞迴轉換。translate=False 的子樹原樣保留（mapping 的值）。

    dict 的「鍵」一律不轉——最外層是 Babele 的英文查找鍵，
    巢狀處（folders / results / pages）的鍵同樣是英文識別字。
    """
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if not translate:
                out[k] = walk(v, translate=False)
                continue
            # mapping 的值是欄位路徑與 converter 名稱，整棵子樹不轉
            if k == 'mapping':
                stats['skipped_mapping'] += 1
                out[k] = walk(v, translate=False)
            else:
                out[k] = walk(v, translate=True)
        return out
    if isinstance(node, list):
        return [walk(v, translate) for v in node]
    if isinstance(node, str):
        if not translate:
            return node
        after = convert(node)
        if after != node:
            stats['converted'] += 1
            check_protected(node, after)
        return after
    return node


def count_keys(node):
    """統計 dict 鍵數（這些鍵刻意不轉，用來對帳）。"""
    n = 0
    if isinstance(node, dict):
        n += len(node)
        for v in node.values():
            n += count_keys(v)
    elif isinstance(node, list):
        for v in node:
            n += count_keys(v)
    return n


if __name__ == '__main__':
    if not os.path.isdir(SRC_DIR):
        print(f'來源不存在：{SRC_DIR}')
        sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)

    files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith('.json'))
    print(f'來源檔案數 : {len(files)}')
    print()

    total_entries = 0
    repaired_files = []
    for fn in files:
        src, repaired = load_lenient(os.path.join(SRC_DIR, fn))
        if repaired:
            repaired_files.append(fn)
        result = walk(src)
        n = len(result.get('entries') or {})
        total_entries += n
        stats['skipped_key'] += count_keys(src.get('entries') or {})
        with open(os.path.join(OUT_DIR, fn), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'entries 總數      : {total_entries}')
    print(f'已轉換字串        : {stats["converted"]}')
    print(f'保留的 mapping 區 : {stats["skipped_mapping"]}')
    print(f'保護清單誤傷      : {len(protected_hits)}')
    if repaired_files:
        print(f'尾逗號已修復      : {", ".join(repaired_files)}')
    if protected_hits:
        print()
        print('!! 保護詞被替換表誤傷，需修正 TERM_MAP / EXTRA_TERMS:')
        for p, a, b in protected_hits[:10]:
            print(f'   [{p}]')
            print(f'      {a[:70]}')
            print(f'   -> {b[:70]}')

    print()
    print(f'輸出 : {OUT_DIR}')
