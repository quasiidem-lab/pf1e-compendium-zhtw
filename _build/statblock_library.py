# -*- coding: utf-8 -*-
r"""產 Statblock Library（SBL）模組的怪物名稱對照檔。

    python _build/statblock_library.py              # 照譯名表寫 translations/statblock-library.*.json（繁）＋簡體稿
    python _build/statblock_library.py --scan       # 重新比對 CHM、舊檔、用語集，重產譯名表（會蓋掉「譯名」欄，先備份）

**這不是 PF1 系統內建的合集包。** SBL 是 PF1 社群另外發的模組（模組代號 `statblock-library`，
gitlab.com/foundryvtt_pathfinder1e/pf1-statblock-library，對照 0.8.0），48 個合集包、10,387 條，
每條是一則日誌（JournalEntry），裡面一頁數據方塊文字（給 SBC 匯入用）＋一頁封面圖。
Babele 每個合集包一個檔，所以會產生多個 `statblock-library.<合集包>.json`，沒有任何一條有譯名的合集包不產檔。

譯名表：`_build/statblock-library譯名.tsv`（Excel 可開），一列一個英文名（同名怪物在不同合集包共用一列）：
  「譯名」欄有值才寫進對照檔，空白的留英文。要補、要改，直接改這一欄再重跑本支（不加 --scan）。
  其他欄是 --scan 比對時留下的依據。
條目清單：`_build/statblock-library條目.tsv`，--scan 時從 SBL 原始碼產生，建置時用來展開成每一條。

**譯名不自己翻**。來源優先序：
  用語集   pf1-chm-src/_資料/用語集對照-CHM不一致.tsv 裡「定案」且分類含 npc／monster 的列（用語集本身在他本機，這是雲端拿得到的片段）
  既有對照檔  本模組 pf1.basic-monsters.json 已定的譯名（同一隻怪兩處寫法一致）
  CHM      果園 CHM 裡「中文（English）」寫在一起的地方。CHM 沒有逐隻怪物頁，取召喚表、魔寵表、動物夥伴、專長、冒險等處的提及
  上游     本模組刪掉的 pf1-bestiary.* 舊檔（上游 fvtt-cn 簡體稿繁化），**只有 CHM 裡找得到同一個詞才收**
CHM 抽出來的中文前面常黏著「或」「例如」「召喚」這類字，strip_prefix() 只在剩下的詞在 CHM 別處也單獨出現時才切；
同一個英文 CHM 有兩種以上寫法的，主寫法要佔三倍以上才收（auto_pick()），其餘列進「CHM寫法」等他裁定。

mapping 不寫，用 Babele 2.9 內建的 JournalEntry 對應：name → name，pages → 頁面（document 轉換器，先比對頁 ID 再比對頁名稱）。
只翻條目名稱與數據方塊那一頁的標題，不翻數據方塊內文、不翻封面頁、不翻合集包名稱。
名稱重複的條目用文件 ID 當鍵，Babele 會先比對 ID。

外部資料（只在 --scan 時讀，環境變數沒設就用他本機路徑）：
  PF1_CHM_DIR   CHM勘誤（pf1-chm-src），要有 chm.py、chmbuild\、_資料\
  PF1_SBL_SRC   pf1-statblock-library 原始碼的 src\ 目錄（裡面是 sb-*\*.yml）
"""
import argparse, collections, csv, glob, html, json, os, re, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
MOD = HERE.parent
TABLE = HERE / 'statblock-library譯名.tsv'
ENTRIES = HERE / 'statblock-library條目.tsv'
OUT_TW = MOD / 'translations'
OUT_CN = HERE / '審核' / 'zhcn'
MODULE_ID = 'statblock-library'
NAME_FMT = '{zh}（{en}）{tail}'   # 「凶暴鼠（Dire Rat）(CR 1/3)」：跟其他怪物對照檔一樣中文在前，英文原名與 CR 保留

CHM = Path(os.environ.get('PF1_CHM_DIR') or r'D:\TRPG\4_工具與筆記\CHM勘誤')
SBL_SRC = Path(os.environ.get('PF1_SBL_SRC') or r'D:\TRPG\4_工具與筆記\Tools\pf1\pf1-statblock-library\src')
OLD_BESTIARY_REV = 'aa5a4b3~1'   # 刪掉 pf1-bestiary.* 之前的那一版

# 人工看過上下文後不收的（2026-11-01）。英文小寫 → 理由。--scan 時這些不自動填譯名，理由寫進「說明」
REJECT = {
    # 上游舊檔的譯名，CHM 裡的「同詞」其實指別的東西
    'nightwalker': 'CHM 的「暗夜行者」是神恩 Come by Night，不是這隻不死生物',
    'dullahan': 'CHM 的「無頭騎士」是作祟 Headless Horseman，不是 Dullahan',
    'siren': 'CHM 的「塞壬」只出現在塞壬珍珠（Pearl of the Sirines），Sirine 是另一種生物',
    'giant bee': 'CHM 的「巨蜂」是巨蜂魔寵（Wasp Familiar），是黃蜂不是蜜蜂',
    'taotieh': 'CHM 的「饕餮」只出現在能力名（饕餮力量、饕餮盛宴），看不出是這隻怪',
    'jinushigami': 'CHM 的「地主神」是御靈衛的能力名，看不出是這隻怪',
    # CHM 的詞指的是同名的別種東西（SBL 這條是有名字的 NPC、動物夥伴，或 Tome of Horrors 的怪物）
    'jynx': 'CHM 的「厄運」看不出是這隻精類',
    'phantasm': 'CHM 的「魅影幻覺」是幻術子派，SBL 這條是虛體不死生物',
    'empyreal': 'CHM 的「蒼生」是血統名，SBL 這條是天使類外來者',
    'gatekeeper': 'CHM 的「守門人」是職業能力，SBL 這條是叫 Gatekeeper 的豺狼人戰士',
    'craven': 'CHM 的「膽小鬼」是半身人替代種族特性，SBL 這條是叫 Craven 的盜賊',
    'beetle': 'CHM 的「甲蟲」是動物之力，SBL 這條是叫 Beetle 的食屍鬼盜賊',
    'lacedon': 'CHM 抽到「妖鬼和水鬼」，切不出是哪一個',
    'sentinel': 'CHM 的「衛道者」是進階職業，SBL 這條是 NPC 圖鑑的武僧',
    'master': 'CHM 的「大師」是職業能力名，SBL 這條是 NPC 圖鑑的武僧',
    'protector': 'CHM 的「戍衛寵」是魔寵變體，SBL 這條是 Tome of Horrors 的外來者',
    'spike': 'CHM 的「釘刺」是攻擊名，SBL 這條是叫 Spike 的巨雪貂',
    'talon': 'CHM 的「爪擊」是攻擊名，SBL 這條是叫 Talon 的鷹動物夥伴',
    'glory': 'CHM 的「榮耀」是能力名，SBL 這條是叫 Glory 的動物夥伴',
    'the old man': '沒查到 CHM 那一處的上下文，不確定是同一個',
    'kyra': 'CHM 寫「凱拉斯」，跟常見的 Kyra 譯法差很多，沒查到上下文，等用語集',
    'recruit': 'CHM 的「見習從者」「新兵」都不是指 NPC 圖鑑這條',
    'thorny': 'CHM 的「刺球」在一張顏色表裡，不是這隻植物生物',
    'haunt': 'CHM 的「作祟」是作祟陷阱，SBL 這條是 Tome of Horrors 的虛體不死生物',
    'shadow': 'CHM 的「陰影」多半是描述符、幻術子派，不死生物 Shadow 在 CHM 寫「幽影」；兩種都有，等裁定',
    'skulk': 'CHM 的「潛伏」是動詞，看不出是這種類人生物',
    'raider': 'CHM 抽到「慘遭劫掠」，不是名詞',
    'fisherman': 'CHM 的「漁夫」是職業，SBL 這條是 Tome of Horrors 的外來者',
    'rake': 'CHM 的「耙抓」是怪物能力，SBL 這條是 NPC 圖鑑的浪蕩子；CHM 另有「浪蕩子」2 處',
    'seal': 'CHM 的「封印」不是海豹',
    'sloth': 'CHM 的「懶惰」是七罪，不是樹懶',
    'su': 'CHM 的 Su 是超自然能力標記',
    'gardener': 'CHM 的「園丁」是職業，SBL 這條是叫 Gardener 的木偶族德魯伊',
    'jackdaw': 'CHM 的「寒鴉」是魔寵，SBL 這條是叫 Jackdaw 的精靈劍客',
    'mole': 'CHM 的「鼴鼠」是魔寵，SBL 這條是 NPC 圖鑑的間諜（Mole 是臥底的意思）',
    'taicho': 'CHM 的「隊長」看不出是指這個叫 Taicho 的天狗戰士',
    'aberrant': 'CHM 的「異怪」是血統、生物類型，SBL 這條是 Tome of Horrors 的巨人',
    'living monolith': 'CHM 的「活體石像」是進階職業，SBL 這條是 Tome of Horrors 的軟泥怪',
}

# 人工定邊界的（CHM 的字串黏著前文，詞本身是 CHM 的寫法）。英文小寫 → (繁體, 說明)
BOUNDARY = {
    'choral the conqueror': ('征服者卓拉爾', 'CHM「遠在征服者卓拉爾（Choral the Conqueror）」'),
    'mammon': ('瑪門', 'CHM「魔鬼大公瑪門（Mammon）」，「魔鬼大公」是頭銜'),
    'plague zombie': ('染疫喪屍', 'CHM「會產生染疫喪屍（plague zombie）」'),
    'witchfire': ('巫火', 'CHM「摧毀巫火（witchfire）」；上游寫「巫焰」'),
}

# 繁體用字定案：CHM 繁體版跟本模組舊譯文寫法不同時，跟舊譯文（2026-11-01 定：凶暴 → 兇暴）
TW_FIX = {'凶暴': '兇暴'}

TABLE_COLS = ['英文', '譯名', '來源', '說明', 'CHM寫法', '上游寫法', '用語集', '既有對照檔', '同名其他條目', '條數', '合集包']


def split_name(n):
    """「Dire Rat (CR 1/3)」→（Dire Rat, (CR 1/3)）。結尾的括號（CR、職業等級）保留英文。"""
    m = re.match(r'^(.*?)\s*(\([^()]*\))?\s*$', n)
    return m.group(1), m.group(2) or ''


def norm(en):
    return re.sub(r'\s+', ' ', en.replace('’', "'")).strip(' ,.').lower()


# ───────────────────────── 掃描（--scan） ─────────────────────────

CJK = '\u4e00-\u9fff\u3400-\u4dbf'
CJK_RE = re.compile(f'[{CJK}]')
PAIR_RE = re.compile(f'([{CJK}]{{1,24}})\\*?\\s*[（(]\\s*([A-Za-z][A-Za-z\\s\'’\\-,.;]{{0,60}}?)\\s*[)）]')
# 括號裡英文後面接的書目、法術抗力、陣營等（「黯翼（Gloomwing, B2）」「巡守者 (Lhaksharut; SR 31)」）
TAIL_RE = re.compile(r'\s*[,;]\s*(?:B\d|SR|CR|[LNC][GNE]|N|pg|\d).*$', re.I)
INLINE_TAG = r'</?(?:b|i|u|em|strong|span|font|a|sup|sub|small|big|s|strike)\b[^>]*>'

# 抽出來的中文前面可能黏著的字。只在切掉後剩下的詞「在 CHM 別處也單獨出現」時才切，見 strip_prefix()
PREFIXES = sorted('''或者 或是 或 以及 和 与 及 跟 同 例如 比如 譬如 如同 如 像是 像 包括 包含 甚至 并且 并 而且 而
但是 但 然后由 然后 由 被 把 将 让 使 使用 用 对 向 从 在 为 成为 化为 变成 变为 变 成 是 有 的 之 你的 你 他 她 它
其 该 此 这些 这个 这种 这只 这 那 一些 一名 一只 一头 一个 一位 一条 一种 一群 一 两只 两 每只 每个 每 只 头 名 个
位 条 种 召唤出 召唤 呼唤 唤来 拥有 获得 化身为 化身 转化为 杀死 击败 对抗 面对 遭遇 类似 某些 某 所有 任何 其他
其它 许多 大量 多个 多只 几只 中的 里的 上的'''.split(), key=len, reverse=True)
# 結尾是這些字的是語言、血統、專長等，不是怪物本身（Tengu →「天狗語」）
NOT_CREATURE = ('语', '血统', '子域', '领域', '专长', '模板', '学派', '秘法', '法术', '之力', '战技', '语言')
DASHES = '—－-·‧・'
CLASSIFIERS = '只头名个位条种'
SENTENCE_RE = re.compile('[的是这那该此它你他她被就由将把让从为有或与及并但而如了得会]|使用|就像|尽管|指挥|天内')
# 兩種寫法一長一短、長的只是短的前面多了虛詞（「當德斯卡瑞」「見綠鬼婆」）：併成短的。
# 前面多的是頭銜、形容詞（「至高天神使安多萊塔」「雄鷹騎士」）就不併，算兩種寫法
FUNC_RE = re.compile('[当对仅会出见除了以获得个可用到直至在把将被给让从向是的为和或与及并而]')


def read_chm_pages():
    for f in sorted(os.listdir(CHM / 'chmbuild')):
        if not re.search(r'\.html?$', f):
            continue
        b = (CHM / 'chmbuild' / f).read_bytes()
        try:
            s = b.decode('utf-8')
        except UnicodeDecodeError:
            s = b.decode('gb18030', errors='replace')
        s = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', s)
        s = re.sub(INLINE_TAG, '', s, flags=re.I)   # 粗體、連結等行內標籤拿掉，詞才不會被切斷
        s = re.sub(r'<[^>]+>', '\n', s)              # 段落、表格格子當邊界
        yield f, html.unescape(s).replace('\u3000', ' ').replace('\xa0', ' ')


class ChmIndex:
    def __init__(self):
        self.pairs = collections.defaultdict(list)   # 英文（小寫）→ [(中文, 頁, 前一個字)]
        texts = []
        for f, s in read_chm_pages():
            texts.append(s)
            for m in PAIR_RE.finditer(s):
                prev = s[m.start() - 1] if m.start() else '\n'
                en = norm(TAIL_RE.sub('', m.group(2)))
                if ',' in en or ';' in en:
                    continue   # 「Elemental, Small Air」這種倒裝，或一個括號裡好幾隻
                self.pairs[en].append((m.group(1), f, prev))
                if re.search(r'[^s]s$', en):   # 複數（young umbral dragons）也記一份單數
                    self.pairs[en[:-1]].append((m.group(1), f, prev))
        self.text = '\n\x00\n'.join(texts)
        self._lb = {}

    def standalone(self, t):
        """t 在 CHM 裡前面不接中文字的出現次數（＝當成一個詞單獨出現）。"""
        if t not in self._lb:
            n, i = 0, self.text.find(t)
            while i != -1:
                if i == 0 or not CJK_RE.match(self.text[i - 1]):
                    n += 1
                i = self.text.find(t, i + 1)
            self._lb[t] = n
        return self._lb[t]

    def strip_prefix(self, r, prev=''):
        if prev.isdigit() and r[:1] in CLASSIFIERS and len(r) > 1:
            r = r[1:]   # 「1d4頭穴巨人」的量詞
        changed = True
        while changed:
            changed = False
            for p in PREFIXES:
                if r.startswith(p) and len(r) > len(p) and self.standalone(r[len(p):]):
                    r, changed = r[len(p):], True
                    break
        parts = re.split(r'或者|或|以及|和|与|及|、', r)
        if len(parts) > 1 and parts[-1] and self.standalone(parts[-1]):
            r = parts[-1]
        return r

    def unsure(self, t):
        """切完還像半句話：開頭還是虛詞，或中間有句子用字、CHM 裡又只出現這一次。"""
        if any(t.startswith(p) for p in PREFIXES):
            return True
        return bool(SENTENCE_RE.search(t)) and self.standalone(t) < 2

    def owners(self, t):
        """CHM 把中文 t 配給了哪些英文（切掉前綴後完全相同才算）。"""
        if not hasattr(self, '_rev'):
            self._rev = collections.defaultdict(set)
            for e, lst in self.pairs.items():
                for raw, _, _ in lst:
                    if len(raw) <= 10:
                        self._rev[self.strip_prefix(raw)].add(e)
        return self._rev.get(t, set())

    def variants(self, en, hint=''):
        """英文 → {中文寫法: 次數}（已切掉前綴）、出現的頁、不採用的寫法。
        hint：上游舊檔的寫法（簡體）。CHM 抽出的字串切不乾淨、但剛好以它結尾時，用它當邊界。"""
        terms, pages, odd = collections.Counter(), collections.defaultdict(set), set()
        for raw, f, prev in self.pairs.get(en, []):
            t = self.strip_prefix(raw, prev)
            if len(t) > 10 or self.unsure(t):
                if hint and len(hint) >= 2 and raw.endswith(hint):
                    t = hint   # 切不乾淨，但結尾剛好是上游的寫法：用它當邊界
                else:
                    odd.add(raw)
                    continue
            if prev in DASHES or t.endswith(NOT_CREATURE):
                odd.add(t)    # 名字被破折號切開（「奧厄—翁」只抓到「翁」），或是語言／血統
                continue
            terms[t] += 1
            pages[t].add(f)
        # 不同寫法分開算，不把「獵豹」併進「豹」；只有多出來的是虛詞才併
        for t in sorted(terms, key=len, reverse=True):
            short = [o for o in terms if o != t and t.endswith(o) and FUNC_RE.search(t[:-len(o)])]
            if short:
                o = max(short, key=len)
                terms[o] += terms.pop(t)
                pages[o] |= pages.pop(t)
        sup = dict(terms)
        return dict(sorted(sup.items(), key=lambda x: -x[1])), pages, odd


def auto_pick(sup):
    """CHM 寫法要不要直接收：只有一種，或主寫法 ≥3 次且是第二名的三倍以上。回傳（寫法, 是否要他看一眼）。"""
    if not sup:
        return None, False
    items = list(sup.items())
    top, n = items[0]
    if len(top) == 1 and n < 2:
        return None, False   # 單字又只出現一次，抓錯邊界的機率太高
    if len(items) == 1:
        return top, False
    if n >= 3 and n >= 3 * items[1][1]:
        return top, True
    return None, False


def read_sbl():
    """SBL 原始碼 → [(合集包, 條目ID, 條目名, 頁ID, 頁名)]，只取數據方塊那一頁（封面頁不翻）。"""
    try:
        import yaml
    except ImportError:
        sys.exit('需要 PyYAML：pip install pyyaml')
    rows = []
    for pack in sorted(p.name for p in SBL_SRC.iterdir() if p.is_dir() and p.name.startswith('sb-')):
        for f in sorted((SBL_SRC / pack).glob('*.yml')):
            d = yaml.safe_load(f.read_text(encoding='utf-8'))
            if str(d.get('_key', '')).startswith('!folders'):
                continue
            page = next((p for p in d.get('pages', []) if p.get('name') == d['name']), None)
            rows.append((pack, d['_id'], d['name'], page['_id'] if page else '', page['name'] if page else ''))
    return rows


def old_bestiary():
    """刪掉的 pf1-bestiary.* 舊檔（上游繁化）→ {英文小寫: 中文}。從本 repo 的 git 歷史讀。"""
    out = {}
    ls = subprocess.run(['git', '-C', str(MOD), 'ls-tree', '--name-only', OLD_BESTIARY_REV, 'translations/'],
                        capture_output=True, text=True, encoding='utf-8', check=True).stdout.split()
    for path in ls:
        if 'pf1-bestiary' not in path:
            continue
        d = json.loads(subprocess.run(['git', '-C', str(MOD), 'show', f'{OLD_BESTIARY_REV}:{path}'],
                                      capture_output=True, text=True, encoding='utf-8', check=True).stdout)
        for en, v in d['entries'].items():
            m = re.match(r'^(.+?)（', v.get('name', ''))
            if m and CJK_RE.search(m.group(1)) and not re.search('[A-Za-z]', m.group(1)):
                out[norm(en)] = m.group(1)
    return out


def glossary():
    """用語集片段：定案、分類含 npc／monster、只有一個譯名的列 → {英文小寫: 簡體}。"""
    out = {}
    p = CHM / '_資料' / '用語集對照-CHM不一致.tsv'
    with open(p, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['層級'] == '定案' and re.search(r'npc|monster', r['分類']) and '／' not in r['用語集譯名（簡）']:
                out[norm(r['英文'])] = r['用語集譯名（簡）']
    return out


def existing():
    """本模組已定的怪物譯名（basic-monsters）→ {英文小寫: 繁體}。"""
    d = json.loads((OUT_TW / 'pf1.basic-monsters.json').read_text(encoding='utf-8'))
    return {norm(en): v['tokenName'] for en, v in d['entries'].items()}


def homonyms():
    """其他合集包（法術、專長、物品…）裡同名的條目 → {英文小寫: [「法術 恐懼術」…]}。種族與怪物類不算。"""
    skip = {'pf1.races.json', 'pf1.racial-hd.json', 'pf1.basic-monsters.json', '_packs-folders'}
    out = collections.defaultdict(list)
    for p in sorted(OUT_TW.glob('*.json')):
        if p.name in skip or 'folders' in p.name or p.name.startswith(MODULE_ID):
            continue
        d = json.loads(re.sub(r',(\s*[}\]])', r'\1', p.read_text(encoding='utf-8')))
        label = d.get('label', p.stem)
        for en, v in d.get('entries', {}).items():
            if isinstance(v, dict) and isinstance(v.get('name'), str):
                out[norm(en)].append(f"{label}「{v['name']}」")
    return out


SAME_KIND = ('怪物模板', '職業', '職業特性')   # 跟這幾類同名、譯名又一致的，是同一個東西（Vampire 吸血鬼、Cleric 牧師）


def same_thing(homs, zh):
    """同名的其他條目都是怪物模板／職業／職業特性，而且沒翻或譯名以 zh 開頭（「術士模板」對「術士」）。"""
    for h in homs:
        m = re.match(r'^(.*?)「(.*)」$', h)
        if not m or m.group(1) not in SAME_KIND:
            return False
        other = re.split(r'[（ ]', m.group(2))[0]
        if CJK_RE.search(other) and not other.startswith(zh):
            return False
    return True


def scan():
    sys.path.insert(0, str(CHM))
    import chm, opencc
    s2tw, tw2s, fix = opencc.OpenCC('s2tw').convert, opencc.OpenCC('tw2s').convert, chm.TcFixer()
    def to_tw(s):   # 跟 CHM 繁體版同一套（s2tw＋CHM 線的例外表），再套本模組的用字定案
        s = fix(s2tw(s))
        for a, b in TW_FIX.items():
            s = s.replace(a, b)
        return s

    sbl = read_sbl()
    with open(ENTRIES, 'w', encoding='utf-8', newline='\n') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['合集包', '條目ID', '條目名稱', '頁ID', '頁名稱'])
        w.writerows(sbl)
    print(f'條目清單：{len(sbl)} 條 → {ENTRIES.name}')

    print('讀 CHM…')
    idx = ChmIndex()
    old, glo, exi, homo = old_bestiary(), glossary(), existing(), homonyms()

    names = collections.OrderedDict()   # 英文小寫 → [顯示用英文, 條數, 合集包集合]
    for pack, _, name, _, _ in sbl:
        en = split_name(name)[0]
        k = norm(en)
        names.setdefault(k, [en, 0, set()])
        names[k][1] += 1
        names[k][2].add(pack)

    rows = []
    for k, (en, n, packs) in sorted(names.items(), key=lambda x: x[1][0].lower()):
        sup, pages, odd = idx.variants(k, tw2s(old[k]) if k in old else '')
        chm_txt = '；'.join(f'{to_tw(t)}×{c}' for t, c in sup.items())
        if odd:
            chm_txt += ('；' if chm_txt else '') + '不採用（邊界不確定或非怪物用法）：' + '、'.join(to_tw(t) for t in sorted(odd))
        r = dict(英文=en, 譯名='', 來源='', 說明='', CHM寫法=chm_txt, 上游寫法=old.get(k, ''),
                 用語集=to_tw(glo[k]) if k in glo else '', 既有對照檔=exi.get(k, ''),
                 同名其他條目='、'.join(homo.get(k, [])[:3]), 條數=n, 合集包='、'.join(sorted(packs)))
        pick, unsure = auto_pick(sup)
        pick_tw = to_tw(pick) if pick else ''
        up = old.get(k, '')
        up_s = tw2s(up) if up else ''
        up_tw = to_tw(up_s) if up else ''   # 舊檔的繁化有錯字（古云龍），走同一套轉換校正

        if k in REJECT:
            r['說明'] = '不收：' + REJECT[k]
        elif k in BOUNDARY:
            r.update(譯名=BOUNDARY[k][0], 來源='CHM', 說明='人工定邊界：' + BOUNDARY[k][1])
        elif k in glo:
            r.update(譯名=r['用語集'], 來源='用語集', 說明='用語集定案' + (f'；CHM 寫「{pick_tw}」' if pick_tw and pick_tw != r['用語集'] else ''))
        elif k in exi:
            r.update(譯名=exi[k], 來源='既有對照檔', 說明='跟 pf1.basic-monsters 一致' + (f'；CHM 寫「{pick_tw}」' if pick_tw and pick_tw != exi[k] else ''))
        elif homo.get(k) and pick and not same_thing(homo[k], pick_tw):
            r['說明'] = '英文跟其他合集包的條目同名，CHM 的寫法可能指那一條，不自動收'
        elif pick:
            note = ['CHM ' + '、'.join(sorted(pages[pick]))[:80]]
            if homo.get(k):
                note.append('跟' + '、'.join(homo[k][:2]) + '同名同譯')
            if unsure:
                note.insert(0, '⚠ CHM 有其他寫法，取多數')
            if up and up_tw != pick_tw:
                note.append(f'上游寫「{up}」')
            elif up:
                note.append('上游相同')
            r.update(譯名=pick_tw, 來源='CHM', 說明='；'.join(note))
        elif sup:
            r['說明'] = 'CHM 寫法不一，等裁定' if len(sup) > 1 else 'CHM 只有一處單字，可能抓錯邊界'
        elif odd and not up:
            r['說明'] = 'CHM 有提到，但抽出來的字串黏著前後文，切不準，見「CHM寫法」'
        elif up:
            # 上游單一來源：CHM 裡要找得到同一個詞，而且 CHM 沒把這個詞配給別的英文
            other = sorted(idx.owners(up_s) - {k})
            hits = idx.standalone(up_s)
            if hits and not other and len(up_s) >= 2:
                r.update(譯名=up_tw, 來源='上游', 說明=f'CHM 有同詞 {hits} 處' + (f'；舊檔原寫「{up}」' if up_tw != up else ''))
            elif other:
                r['說明'] = f'只有上游有譯名；CHM 把這個詞配給 {"、".join(other[:3])}'
            else:
                r['說明'] = '只有上游有譯名，CHM 找不到這個詞'
        rows.append(r)

    with open(TABLE, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=TABLE_COLS, delimiter='\t', lineterminator='\r\n')
        w.writeheader()
        w.writerows(rows)
    by = collections.Counter(r['來源'] for r in rows if r['譯名'])
    print(f'譯名表：{len(rows)} 個英文名，有譯名 {sum(by.values())}（' + '、'.join(f'{k} {v}' for k, v in by.items()) + f'）→ {TABLE.name}')


# ───────────────────────── 建置（預設） ─────────────────────────

def load_tsv(path, sig=False):
    with open(path, encoding='utf-8-sig' if sig else 'utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def build(entries, names, conv):
    """→ {合集包: 對照檔內容}。"""
    dup = collections.Counter((e['合集包'], e['條目名稱']) for e in entries)
    out = collections.defaultdict(dict)
    for e in entries:
        en, tail = split_name(e['條目名稱'])
        zh = names.get(norm(en))
        if not zh:
            continue
        name = NAME_FMT.format(zh=conv(zh), en=en, tail=tail)
        item = {'name': name}
        if e['頁ID']:
            item['pages'] = {e['頁ID']: {'name': name}}
        key = e['條目ID'] if dup[(e['合集包'], e['條目名稱'])] > 1 else e['條目名稱']
        out[e['合集包']][key] = item
    return {p: {'entries': dict(sorted(v.items()))} for p, v in out.items()}


def save(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scan', action='store_true', help='重新比對來源、重產譯名表與條目清單')
    a = ap.parse_args()
    if a.scan:
        scan()

    import opencc
    tw2s = opencc.OpenCC('tw2s').convert
    entries = load_tsv(ENTRIES)
    names = {norm(r['英文']): r['譯名'].strip() for r in load_tsv(TABLE, sig=True) if r['譯名'].strip()}
    for f in list(OUT_TW.glob(f'{MODULE_ID}.*.json')) + list(OUT_CN.glob(f'{MODULE_ID}.*.json')):
        f.unlink()   # 譯名表刪光某個合集包的譯名時，舊檔不要留著
    tw, cn = build(entries, names, lambda s: s), build(entries, names, tw2s)
    for pack in sorted(tw):
        save(OUT_TW / f'{MODULE_ID}.{pack}.json', tw[pack])
        save(OUT_CN / f'{MODULE_ID}.{pack}.json', cn[pack])
    total = collections.Counter(e['合集包'] for e in entries)
    for pack in sorted(total):
        print(f'  {pack}：{len(tw.get(pack, {}).get("entries", {}))}／{total[pack]}')
    print(f'寫入 {len(tw)} 個合集包，{sum(len(v["entries"]) for v in tw.values())}／{len(entries)} 條有譯名')


if __name__ == '__main__':
    main()
