# -*- coding: utf-8 -*-
"""驗證合集包繁中對照表的完整性。只輸出統計與異常位置，不列出譯文內容。

檢查七項（前四項對應介面層 verify_zhtw.py，後三項是合集層特有）：
  1. 檔案集合一致        來源 30 檔都要有對應輸出
  2. entries 鍵集合一致  Babele 靠英文鍵比對，少一個就查不到那筆
  3. mapping 完全未變    欄位路徑被轉換的話 Babele 直接壞掉
  4. HTML 標籤完好
  5. @ 連結的文件 ID 完好  @Compendium[pf1.spells.xxx] 的 ID 不可變
  6. 無殘留簡體          以 OpenCC 反向轉換偵測，非手寫字元表
  7. 結構一致            巢狀 actions/results/pages 的形狀不可變

驗證沒過回傳非零。
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
import opencc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), 'translations')
DATA = r'C:\Users\User\AppData\Local\FoundryVTT\Data'
SRC_DIR = os.path.join(DATA, 'modules', 'pf1e_compendium_chn', 'translations')

_cc = opencc.OpenCC('s2tw')

# 與 build_compendium.py 的 PLACEHOLDER 同義：只認真正的 HTML 標籤。
# 若這裡用寬鬆的 `<[^>]+>`，<水晶球 (crystal ball)> 這種偽標籤在轉換前後
# 內容不同，會被誤報成「標籤不符」。
TAG = re.compile(r'</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>')
LINK_ID = re.compile(r'@[A-Za-z][\w]*\[([^\]]*)\]')

# OpenCC s2tw 的一對多映射：這些字在正體中文裡本來就通用，
# 反向偵測會把已經正確的譯文誤判成「殘留簡體」。實例：
#   斗轉星移  OpenCC 想改成「鬥轉星移」，但這個成語就是「斗」（星斗）
#   無厘頭    想改成「無釐頭」；風采 想改成「風採」；來回 想改成「來迴」
#   趨吉避凶  想改成「避兇」；顛仆 想改成「顛僕」
#   了解/瞭解、干擾、平面 同理
# 只有「該字在原文確實是簡體字」才算殘簡，因此逐字比對並跳過這一組。
AMBIGUOUS = set('了干伙面岩制注占並并复余系历钟表'
                '斗厘采征凶仆回辟只游划念')

# 轉換前後長度不同時無法逐字對齊——實務上不會發生（s2tw 是一對一字元映射），
# 真的出現代表有別的東西壞掉，保守起見回報出來。

# URL 與 HTML 屬性內的文字刻意不轉：
#   #TOC-黑暗视觉  是 d20pfsrd 的錨點，轉了連結就失效
#   來源有一處把中文誤貼進 href 的網址裡（Demand），那是上游既有的破損
# 這些都在標籤／網址內部，不影響畫面上看到的字。
URL_IN = re.compile(r'https?://[^\s"<>]+')


def load_lenient(path):
    text = open(path, encoding='utf-8-sig').read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(re.sub(r',(\s*[}\]])', r'\1', text))


def has_simplified(text):
    """已是繁體的字串再轉一次 s2tw 應為不動點，有變化即代表殘留簡體。

    例外是 AMBIGUOUS 那組一對多映射的字——它們在正體中文裡本來就通用，
    OpenCC 想改不代表原文是簡體。逐字比對並跳過那組，避免整批誤報。
    """
    if not isinstance(text, str) or not text:
        return False
    conv = _cc.convert(text)
    if conv == text:
        return False
    # 長度不同時無法逐字對齊，保守起見直接視為有殘簡
    if len(conv) != len(text):
        return True
    diff = [i for i, (a, b) in enumerate(zip(text, conv))
            if a != b and a not in AMBIGUOUS]
    if not diff:
        return False
    # 全部落在標籤／網址內部就不算——那些字不會顯示在畫面上
    spans = [(m.start(), m.end()) for m in URL_IN.finditer(text)]
    spans += [(m.start(), m.end()) for m in TAG.finditer(text)]
    return not all(any(s <= i < e for s, e in spans) for i in diff)


def shape(node):
    """結構指紋：只看容器形狀與鍵名，不看字串內容。"""
    if isinstance(node, dict):
        return {k: shape(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        return [shape(v) for v in node]
    return type(node).__name__


def strings_with_path(node, path='', skip_mapping=True):
    """走訪所有字串，回傳 (路徑, 字串)。mapping 子樹預設略過。"""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if skip_mapping and k == 'mapping':
                continue
            out += strings_with_path(v, f'{path}.{k}' if path else k, skip_mapping)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += strings_with_path(v, f'{path}[{i}]', skip_mapping)
    elif isinstance(node, str):
        out.append((path, node))
    return out


bad_keys, bad_mapping, bad_tag, bad_link, bad_cjk, bad_shape = [], [], [], [], [], []

_chm = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chm_entries.json')
CHM_ENTRIES = json.load(open(_chm, encoding='utf-8')) if os.path.exists(_chm) else {}

src_files = sorted(f for f in os.listdir(SRC_DIR) if f.lower().endswith('.json'))
out_files = sorted(f for f in os.listdir(OUT_DIR) if f.lower().endswith('.json')) \
    if os.path.isdir(OUT_DIR) else []

missing_files = [f for f in src_files if f not in out_files]
extra_files = [f for f in out_files if f not in src_files]

n_entries = n_strings = 0

for fn in src_files:
    if fn in missing_files:
        continue
    src = load_lenient(os.path.join(SRC_DIR, fn))
    dst = load_lenient(os.path.join(OUT_DIR, fn))

    se, de = src.get('entries') or {}, dst.get('entries') or {}
    n_entries += len(de)
    # build_chm.py 補進的條目（上游對照表沒收、CHM 有）算合法新增，比對鍵集合與結構前先拿掉
    chm_added = (set(de) - set(se)) & set(CHM_ENTRIES.get(fn, {}))
    if chm_added:
        dst = dict(dst, entries={k: v for k, v in de.items() if k not in chm_added})
        de = dst['entries']
    if set(se) != set(de):
        bad_keys.append(f'{fn}: 缺 {len(set(se)-set(de))} / 多 {len(set(de)-set(se))}')

    if src.get('mapping') != dst.get('mapping'):
        bad_mapping.append(fn)

    if shape(src) != shape(dst):
        bad_shape.append(fn)

    s_strs = dict(strings_with_path(src))
    d_strs = dict(strings_with_path(dst))
    n_strings += len(d_strs)

    # 換成 CHM 譯文的條目（build_chm.py 記在 chm_entries.json）跟上游本來就不同：
    # HTML 標籤不比，殘簡也不查——CHM 繁體版的字形由 CHM 線的例外表裁定（污、拆台、回合這類會被誤報）
    chm_prefix = tuple(f'entries.{k}.' for k in CHM_ENTRIES.get(fn, {}))
    for p, s in s_strs.items():
        d = d_strs.get(p)
        if d is None:
            continue
        from_chm = bool(chm_prefix) and p.startswith(chm_prefix)
        if not from_chm and sorted(TAG.findall(s)) != sorted(TAG.findall(d)):
            bad_tag.append(f'{fn}:{p}')
        if sorted(LINK_ID.findall(s)) != sorted(LINK_ID.findall(d)):
            bad_link.append(f'{fn}:{p}')
        if not from_chm and has_simplified(d):
            bad_cjk.append(f'{fn}:{p}')

print(f'來源檔案數         : {len(src_files)}')
print(f'輸出檔案數         : {len(out_files)}')
print(f'entries 總數       : {n_entries}')
print(f'字串總數           : {n_strings}')
print()
print(f'缺少的輸出檔       : {len(missing_files)}')
print(f'多餘的輸出檔       : {len(extra_files)}')
print(f'entries 鍵集合不符 : {len(bad_keys)}')
print(f'mapping 被更動     : {len(bad_mapping)}')
print(f'結構不一致         : {len(bad_shape)}')
print(f'HTML 標籤不符      : {len(bad_tag)}')
print(f'連結 ID 不符       : {len(bad_link)}')
print(f'殘留簡體字         : {len(bad_cjk)}')

for label, lst in (('缺檔', missing_files), ('多檔', extra_files),
                   ('鍵集合', bad_keys), ('mapping', bad_mapping),
                   ('結構', bad_shape), ('HTML', bad_tag),
                   ('連結ID', bad_link), ('殘簡', bad_cjk)):
    if lst:
        print()
        print(f'--- {label} 異常（最多 15 筆）---')
        for k in lst[:15]:
            print(f'   {k}')

ok = not (missing_files or extra_files or bad_keys or bad_mapping
          or bad_shape or bad_tag or bad_link or bad_cjk)
print()
print('驗證結果:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
