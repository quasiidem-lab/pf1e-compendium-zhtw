# -*- coding: utf-8 -*-
r"""職業能力（pf1.class-abilities）的 Foundry 名稱 → AoN 名稱對應表。

    python _build/class_ability_names.py fetch    # 補抓 AoN 職業頁與選項詳情頁（有快取就不抓，1 秒一頁）
    python _build/class_ability_names.py          # 產對應表與統計（零請求）

產物：
  _build/審核/職業能力名稱對應-<日期>.tsv   一列一條 Foundry 條目：轉換後名、AoN 頁、CHM 有沒有、信心

**只做名稱對應，不填譯文。** 對應表裡的「CHM 夾註」欄是 CHM 原文裡「中文（English）」的寫法，
給人核對用；要接進合集包得等 CHM 線替職業能力插條目錨點，再在 build_chm.py 的 KINDS 加一類。

為什麼要另外對：Foundry 的職業能力名稱跟 AoN 不同寫法，pf1.py 的 `_pack_match()` 只吃得下
其中三種（同名、職業縮寫後綴、倒裝），其餘 idmap 一律報「AoN 對不到」。這支補上其他寫法，
規則寫在 RULES（一條一個函式，報表的「規則」欄就是函式的說明第一行）。

輸入（都只讀；路徑環境變數優先，沒設用他電腦上的預設）：
  PF1_TOOLS       Tools\pf1（pf1.py：AoN 抓頁、職業選項頁清單）
  PF1_INDEX       Tools\pf1\pf1-index：aon-class-options.json、aon-discoveries.json
                  （`python pf1.py build --classopts-only`、`--discoveries-only` 產的）
                  加上這支 fetch 存的 class-pages\、classopt-pages\（AoN 原始 HTML）
  PF1_DATA_PACKS  pf1-data\packs（Foundry 原始名稱、所屬職業 associations）
  PF1_CHM_DIR     CHM勘誤（chmbuild\ 簡體原始檔，看 CHM 職業章節有沒有這條）

信心怎麼給（寧可少對，不要對錯）：
  高    名稱對上、AoN 只剩一條，而且所屬職業（縮寫後綴或 Foundry 的 associations）對得上
  中    名稱對上、AoN 只有一條，但 Foundry 這邊沒有職業可核（條目不在現行 pf1-data、也沒有縮寫）
  共用  一條 Foundry 能力，AoN 在好幾頁各列一次（多職業共有、子領域、好幾個秘示域共有的天啟），全列
  多筆  對到不只一條（不同職業或不同家族的同名能力）分不出來，不挑，全列
  —     對不到。「備註」寫卡在哪
"""
import csv, html, json, os, re, sys, time, unicodedata, urllib.parse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
TR = HERE.parent / 'translations' / 'pf1.class-abilities.json'
BASE = HERE / 'base' / 'pf1.class-abilities.json'
TOOLS = Path(os.environ.get('PF1_TOOLS', r'C:\Users\User\Tools\pf1'))
INDEX = Path(os.environ.get('PF1_INDEX', str(TOOLS / 'pf1-index')))
PACKS = Path(os.environ.get('PF1_DATA_PACKS', str(TOOLS / 'pf1-data' / 'packs')))
CHM = Path(os.environ.get('PF1_CHM_DIR', r'D:\TRPG\4_工具與筆記\CHM勘誤'))
CLASS_DIR = INDEX / 'class-pages'
DETAIL_DIR = INDEX / 'classopt-pages'
OUT = HERE / '審核' / f'職業能力名稱對應-{date.today():%Y%m%d}.tsv'
AON = 'https://www.aonprd.com/'

# Foundry 名稱結尾的職業縮寫。照 Foundry 的用法列（UMK＝掉鏈武僧），不從字首猜：
# 字首猜法會把 SAM 猜成 Samurai 以外的東西、把 SU（Spiritualist 錯拼）猜錯
ABBR = {
    'ALC': ['Alchemist'], 'APA': ['Antipaladin'], 'ARC': ['Arcanist'],
    'BAR': ['Barbarian', 'Barbarian (Unchained)'], 'BLO': ['Bloodrager'], 'BRA': ['Brawler'],
    'CAV': ['Cavalier'], 'CLE': ['Cleric'], 'DRU': ['Druid'], 'FGT': ['Fighter'],
    'GUN': ['Gunslinger'], 'HUN': ['Hunter'], 'INQ': ['Inquisitor'], 'INV': ['Investigator'],
    'KIN': ['Kineticist'], 'MAG': ['Magus'], 'MNK': ['Monk'], 'UMK': ['Monk (Unchained)'],
    'NIN': ['Ninja'], 'OCC': ['Occultist'], 'ORA': ['Oracle'], 'PSY': ['Psychic'],
    'RNG': ['Ranger'], 'ROG': ['Rogue', 'Rogue (Unchained)'], 'SAM': ['Samurai'],
    'SHA': ['Shaman'], 'SHI': ['Shifter'], 'SKA': ['Skald'], 'SLA': ['Slayer'],
    'SOR': ['Sorcerer'], 'SPI': ['Spiritualist', 'Phantom'], 'SWA': ['Swashbuckler'],
    'VIG': ['Vigilante'], 'WAR': ['Warpriest'], 'WIZ': ['Wizard'],
    'UC': ['Barbarian (Unchained)', 'Monk (Unchained)', 'Rogue (Unchained)',
           'Summoner (Unchained)', 'Eidolon (Unchained)'],
}
UNCHAINED_BASE = {'Barbarian (Unchained)': 'Barbarian', 'Monk (Unchained)': 'Monk',
                  'Rogue (Unchained)': 'Rogue', 'Summoner (Unchained)': 'Summoner',
                  'Eidolon (Unchained)': 'Eidolon'}


# ---------------------------------------------------------------- 名稱正規化

# 結尾的 (Ex)／(Su)／(Sp)；通靈者靈體能力還會帶階級：(Lesser, Su)、(Supreme, Su)
TYPE_SUF = re.compile(r'\s*\((?:(?:lesser|intermediate|greater|supreme),\s*)?'
                      r'(?:ex|su|sp|ex or su|su or ex|ex or sp|sp or ex|su or sp|sp or su|ex, su|su, sp|ex/su|su/sp)\)\s*$',
                      re.I)


def key(s):
    """比對用的鍵：全半形、彎撇號、連字號、大小寫、多餘空白、結尾 (Ex)/(Su)/(Sp) 與 AoN 的 * 標記都不算差別。

    連字號當空白：Foundry `Jack of All Trades`／AoN `Jack-of-All-Trades`；撇號前的空白拿掉：AoN `Thief ’s Soul`。
    """
    s = unicodedata.normalize('NFKC', html.unescape(str(s)))
    s = s.replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    s = TYPE_SUF.sub('', s.replace('*', '')).replace('-', ' ')   # AoN 有 `Tanglefoot Bomb (Su)*`，星號先拿掉
    return re.sub(r" +'", "'", ' '.join(s.split())).lower().strip(' :')


# ---------------------------------------------------------------- AoN 端

def _strip(s):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ').split())


SKIP_HEAD = {'source', 'prerequisites', 'prerequisite', 'benefit', 'benefits', 'level', 'special',
             'granted powers', 'domain spells', 'bonus spells', 'class skills', 'spells',
             'weapon and armor proficiency', 'associated school', 'replacement power',
             'bonus feats', 'bloodline arcana', 'bloodline powers', 'bloodline spells',
             'arcana', 'powers', 'spells per day', 'revelations',
             'mystery spells', 'associated domains', 'associated blessings', 'description',
             'requirements', 'note', 'notes', 'deities', 'minor', 'major', 'spirit magic spells',
             'hexes', 'spirit animal', 'spirit ability', 'greater spirit ability',
             'true spirit ability', 'subdomains', 'focus powers',
             'base power', 'resonant power', 'implements', 'phrenic pool ability',
             'discipline powers', 'discipline spells', 'skills', 'patron spells', 'curse'}
# 標題裡常夾 PFS 圖示 <img> 或連結 <a>，所以中間允許標籤，取出來再脫
# 職業頁只濾表頭類的字；「Bonus Feats」「Focus Powers」「Hexes」在職業頁上是真的職業能力
SKIP_CLASS = {'source', 'prerequisites', 'prerequisite', 'benefit', 'benefits', 'level', 'special',
              'class skills', 'weapon and armor proficiency', 'spells per day', 'description',
              'requirements', 'note', 'notes'}
HEAD_RE = re.compile(r'<b>((?:(?!</?b>).){2,200}?)</b>|<i>([^<]{2,80})</i>\s*:|<h[2-4][^>]*>(.{2,300}?)</h[2-4]>',
                     re.I | re.S)


INNER_TABLE = re.compile(r'<table\b(?:(?!<table\b).)*?</table>', re.S | re.I)


def heads(seg, detail=False):
    """一段 AoN HTML 裡的能力名：粗體標題、`<i>名稱</i>:`、h2～h4。表格裡的不算（是進度表）。

    詳情頁整頁內容包在一張排版用的表格裡，只拿掉有表頭格的內層表格（進度表）。
    """
    if detail:
        seg = INNER_TABLE.sub(lambda m: '' if re.search(r'<th\b', m.group(0), re.I) else m.group(0), seg)
    else:
        seg = re.sub(r'<table\b.*?</table>', '', seg, flags=re.S | re.I)
    out = []
    for m in HEAD_RE.finditer(seg):
        n = _strip(next(g for g in m.groups() if g)).strip(' :')
        n = re.sub(r'\s*\((?:minor|major)\)$', '', n, flags=re.I)   # 祝福的大小能力
        if n and len(n) <= 80 and key(n) not in (SKIP_HEAD if detail else SKIP_CLASS) \
                and not re.search(r'\bpg\.\s*\d|Class Details', n):
            out.append(n)
    return out


FAMILY_WORDS = {'bloodline', 'bloodrager', 'blessing', 'domain', 'subdomain', 'mystery', 'spirit',
                'school', 'patron', 'oath', 'discipline', 'focus', 'arcane'}


def list_page(body, v, url, add):
    """一頁寫完整個家族的清單頁：h2 是上層（去掉家族字），其下的粗體／斜體是它的能力。"""
    body = INNER_TABLE.sub(lambda m: '' if re.search(r'<th\b', m.group(0), re.I) else m.group(0), body)
    parent = ''
    for m in HEAD_RE.finditer(body):
        n = re.sub(r'\s*\((?:minor|major)\)$', '', _strip(next(g for g in m.groups() if g)).strip(' :'), flags=re.I)
        if m.group(3) is not None:
            words = n.split()
            while words and words[-1].lower() in FAMILY_WORDS | {'inquisition'}:
                words.pop()
            parent = ' '.join(words)
            continue
        if parent and n and len(n) <= 80 and key(n) not in SKIP_HEAD | {'spirit bonus', 'seance boon',
                                                                        'favored locations', 'influence penalty',
                                                                        'taboos', 'granted powers'}:
            add(n, v['family'] + ' 能力', v['classes'], url, parent=parent)


def load_aon():
    """AoN 端的名冊：一列一條 (名稱, 家族, 職業, 上層名, AoN 頁)。"""
    recs = []

    def add(name, fam, classes, url, parent=''):
        recs.append(dict(name=name, key=key(name), family=fam, classes=list(classes),
                         parent=parent, url=url))
    # 一、職業選項索引（pf1.py build --classopts-only）：狂暴之力、盜賊天賦、血統名……
    for x in json.loads((INDEX / 'aon-class-options.json').read_text(encoding='utf-8')):
        page = x['page']
        url = page + (f"{'&' if '?' in page else '?'}{x['param']}={x['url_name']}"
                      if x.get('param') and x.get('url_name') else '')
        classes = list(x['classes'])
        if x['family'] == 'Evolution':   # 掉鏈子召喚師沒有自己的進化頁，跟原版共用這一頁
            classes += ['Summoner (Unchained)', 'Eidolon (Unchained)']
        add(x['name'], x['family'], classes, url)
    # 二、職業頁（ClassDisplay）：核心職業能力，含吟遊表演的子項、替代終極能力
    for p in sorted(CLASS_DIR.glob('*.html')):
        t = p.read_text(encoding='utf-8')
        i = t.find('>Class Features<')
        j = t.find('>Favored Class Options<')
        if i < 0:
            continue
        for n in heads(t[i:j if j > i else len(t)]):
            add(n, 'Class Feature', [p.stem], 'ClassDisplay.aspx?ItemName=' + p.stem)
    # 三、選項詳情頁：秘示域的天啟、領域能力、血統能力、祝福的大小能力……
    idx = DETAIL_DIR / '_index.json'
    if idx.exists():
        for url, v in json.loads(idx.read_text(encoding='utf-8')).items():
            p = DETAIL_DIR / v['file']
            if not p.exists():
                continue
            t = p.read_text(encoding='utf-8')
            m = re.search(r'id="MainContent_DataListTypes"|id="main"', t)
            body = t[m.start():] if m else t
            body = body[:body.find('Site Owner')] if 'Site Owner' in body else body
            classes = v.get('classes', [])
            if v.get('extra'):   # 職業選項索引沒收的上層（奧術學派），本身也算一條
                add(v['url_name'], v['family'], classes, url)
            if v.get('list'):
                list_page(body, v, url, add)
                continue
            own = key(v['url_name'])
            for n in heads(body, detail=True):
                k = key(n)
                if k == own or (k.startswith(own + ' ') and set(k[len(own):].split()) <= FAMILY_WORDS):
                    continue   # 頁面自己的標題（Black Blood、Fire Blessing），不是底下的能力
                add(n, v['family'] + ' 能力', classes, url, parent=v['url_name'])
    return recs


# ---------------------------------------------------------------- Foundry 端

def load_fvtt():
    """Foundry 原始名稱 → (所屬職業, 標籤)。名稱以 pf1-data 的 YAML 為準。"""
    import yaml
    info = {}
    for p in (PACKS / 'class-abilities').rglob('*.yaml'):
        try:
            d = yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(d, dict) or d.get('type') != 'feat' or not d.get('name'):
            continue
        s = d.get('system') or {}
        info[d['name']] = dict(classes=(s.get('associations') or {}).get('classes') or [],
                               tags=s.get('tags') or [])
    return info


# ---------------------------------------------------------------- 轉換規則
# 每條規則吃 Foundry 名稱，吐 0～多個候選 (AoN 名稱, 職業提示, 家族提示, 上層名提示)。
# 職業提示 None＝名稱本身沒帶職業（之後用 associations 核）；家族提示是 AoN 家族名的關鍵字。
# 說明第一行就是報表「規則」欄的文字。

def r_same(n):
    """原樣（只差大小寫、撇號、(Ex)/(Su) 這類標記）"""
    yield n, None, None, None


# 人工逐條確認過的拼法例外（2026-10-31，報表「對不到／拼法差一點」那批）：
# Foundry 名 → (AoN 名, 上層, 家族)。確認方式：Foundry 英文內文（現行 pf1-data 沒有的舊鍵看合集包現有內文）
# 跟 AoN 內文逐條對讀，是同一條能力才收。上層／家族留空＝不限。
# 名字很像但確認是**不同能力**、刻意不收的列在 NOT_SAME，報表備註會寫出來，免得下次又被當成拼錯
NOT_SAME = {
    'Aura (OMD)': '導魂者的靈光，AoN 只有牧師、戰鬥祭司的',
    'Deliver Touch Spells (SPI)': '幻影的能力，AoN 同名的是薩滿靈獸、女巫魔寵的',
    'Devotion (SPI)': '幻影的能力，AoN 同名的是女巫庇護主',
    'Disease (UC) (4 pts)': '掉鏈子幻靈進化，AoN 同名的是牧師變體引導',
    'Elemental Gap': '念力天賦（utility），AoN 最像的 Elemental Trap 是另一條注能',
    'Improved Quarry (VAM)': '吸血鬼獵人的，AoN 只有遊俠、殺手的',
    'Quarry (VAM)': '吸血鬼獵人的，AoN 只有遊俠、殺手的',
    'Magic Attacks (SPI)': '幻影的能力，AoN 同名的是幻靈進化',
    'Order of the Beast': 'AoN 沒有這個騎士團，最像的 Order of the Asp 是另一個',
    'Wavedancer': '血脈狂怒者血脈能力，AoN 最像的 Waterdancer 是念力天賦',
    'Wisdom of the Ancients': '內文是出神與祖靈交談，AoN 的 Wisdom of the Ages 是用感知代智力，不同能力',
}
EXCEPTIONS = {
    # Foundry 打錯
    "Ahrimon's Favor": ("Ahriman's Favor", 'Div', None),
    'Arcane Hypothesis': ('Arcane Apotheosis', 'Arcane', 'Bloodline 能力'),
    'Aura of Repitition': ('Aura of Repetition', 'Artifice', None),
    'Caging Strke': ('Caging Strike', 'Imprisonment', None),
    'Danger Word': ('Danger Ward', 'Order of the Paw', None),
    'Energy Absorbtion': ('Energy Absorption', 'Abjuration', 'Arcane School 能力'),
    'Entrepeneur': ('Entrepreneur', None, 'Vigilante Talent'),
    'Fiendish Probiscus': ('Fiendish Proboscis', None, 'Arcanist Exploit'),
    'Final Asepct': ('Final Aspect', None, 'Class Feature'),
    'Keep the Corners': ('Keep to the Corners', 'Streets', None),
    'Marshall\'s Order': ("Marshal's Order", 'Marshal', None),
    'Master Tacitician': ('Master Tactician', None, 'Class Feature'),
    'Metmorphosis': ('Metamorphosis', 'Rivethun', None),
    'Nightmate Subdomain': ('Nightmare Subdomain', 'Madness', None),
    'Pack Range': ('Pack Rage', None, 'Rage Power'),
    'Pheremones': ('Pheromones', None, 'Discovery'),
    'Rustling Grasp': ('Rusting Grasp', 'Metal', None),
    'Soiling Touch': ('Spoiling Touch', 'Div', None),
    'Soverignty Subdomain': ('Sovereignty Subdomain', 'Law', None),
    'Stone Stabilitiy': ('Stone Stability', 'Stone', 'Mystery 能力'),   # 內文是先知秘示域的寫法（You receive…）
    'Thorns Subdomainf': ('Thorns Subdomain', 'Plant', None),
    'UItimate Magic (4 pts)': ('Ultimate Magic', None, 'Evolution'),   # 開頭是大寫 I 不是 l
    'Vortex fo Flesh': ('Vortex of Flesh', 'Shapechanger', None),
    # AoN 打錯
    'Iconoclastic Strike': ('Iconclastic Strike', None, 'Investigator Talent'),
    'Remedy Extract': ('Remady Extract', None, 'Discovery'),
    'Venomous Stare': ('Venemous Stare', 'Scalykind', None),
    # 兩邊寫法不同（單複數、所有格、少一個字、改過名）
    'Black Blood Resistances': ('Black Blood Resistance', 'Black Blood', None),
    'Draconic Resistances': ('Draconic Resistance', 'Draconic', 'Bloodrager Bloodline 能力'),
    'Earth Glide (Kobold)': ('Earth Glide', 'Kobold Sorcerer', None),
    'Eldritch Blast': ('Eldritch Bolt', 'Spellscar', None),
    'Fortification Subdomain': ('Fortifications Subdomain', 'Protection', None),   # 替代能力都是 Sheltering Walls
    'In Accordance with Prophecy': ('In Accordance with the Prophecy', 'Divination', None),
    'Mammoth Hide': ("Mammoth's Hide", 'Mammoth', None),
    'Martial Discipline': ('Martial Disciple', 'Ascetic', None),
    'Mists Shroud': ("Mist's Shroud", 'Waves', None),
    'Moonlight Script': ('Moonlit Script', 'Lunar', None),
    'Power of the Giants': ('Power of Giants', 'Orc', None),
    'Rage (Cleric)': ('Rage', 'Destruction', 'Domain 能力'),   # 狂怒子領域的替代能力
    'Ravenous Fury': ('Ravenous Frenzy', 'Ghoul', None),
    'Salamander\'s Scales': ('Salamander Scales', 'Salamander', None),
    'Soulstrider': ('Soulrider', None, 'Arcanist Exploit'),
    'Spell Binding': ('Spell Blending', None, 'Magus Arcana'),
    'Style Strikes (UC)': ('Style Strike', None, 'Class Feature'),
    'Summon Monster': ('Summon Monster I', None, 'Class Feature'),
    'Summon Monster (UC)': ('Summon Monster I', None, 'Class Feature'),
    'Untwisting Infusion': ('Untwisting Iron Infusion', None, 'Wild Talent'),
    'Vision of Iron': ('Vision in Iron', 'Metal', None),
    'Wards of the City': ('Ward of the City', 'Slums', None),
    'World Serpent Unity': ('World Serpent Totem Unity', None, 'Rage Power'),
}


def r_exception(n):
    """人工確認過的拼法例外（EXCEPTIONS 表）：`Metmorphosis` → `Metamorphosis`"""
    if n in EXCEPTIONS:
        aon, parent, fam = EXCEPTIONS[n]
        yield aon, None, (fam,) if fam else None, parent


ELEMENTS = {'air', 'earth', 'fire', 'water', 'acid', 'cold', 'electricity', 'sonic'}
# 薩滿的元素形態：Foundry 依元素拆，AoN 分屬四個魂域（逐條對過內文：Air 那條是閃電元素，就是 Wind 魂域那條）
SHAMAN_SPIRIT_OF = {'air': 'Wind', 'earth': 'Stone', 'fire': 'Flame', 'water': 'Waves'}


def r_element(n):
    """元素子選項：`Elemental Movement (Earth)` → `Elemental Movement`（Foundry 依元素拆成好幾條，AoN 寫成一條）"""
    m = re.fullmatch(r'(.+?)(?: \(([A-Z]{2,3})\))? \(([A-Za-z]+)\)', n)
    if m and m.group(3).lower() in ELEMENTS and (not m.group(2) or m.group(2) in ABBR):
        parent = SHAMAN_SPIRIT_OF.get(m.group(3).lower()) if m.group(2) == 'SHA' else None
        yield m.group(1), ABBR.get(m.group(2)) if m.group(2) else None, None, parent


def r_abbr(n):
    """去掉結尾的職業縮寫：`Evasion (NIN)` → `Evasion`，只認忍者頁上的那條"""
    m = re.fullmatch(r'(.+?) \(([A-Za-z]{2,3})\)', n)
    if m and m.group(2).upper() in ABBR:
        yield m.group(1), ABBR[m.group(2).upper()], None, None


def r_uc(n):
    """去掉 `(UC)`（掉鏈子版）：`Ki Pool (UC)` → `Ki Pool`，只認掉鏈子職業的那條"""
    m = re.fullmatch(r'(.+?) \(UC\)(?: \((\d) pts?\))?', n)
    if m:
        yield m.group(1), ABBR['UC'], ('Evolution',) if m.group(2) else None, None


def r_points(n):
    """去掉幻靈進化的點數：`Bleed (1 pt)` → `Bleed`，只認進化"""
    m = re.fullmatch(r'(.+?) \((\d) pts?\)', n)
    if m:
        yield m.group(1), None, ('Evolution',), None


def r_paren_family(n):
    """去掉結尾括號裡的家族名：`Restriction (Stare)` → `Restriction`，只認凝視"""
    m = re.fullmatch(r'(.+?) \(([A-Za-z ]+)\)', n)
    if m and m.group(2).upper() not in ABBR and not re.fullmatch(r'\d pts?', m.group(2)):
        yield m.group(1), None, (m.group(2),), None


def r_inverted(n):
    """倒裝：`Animal Fury, Greater` ↔ `Greater Animal Fury`"""
    m = re.fullmatch(r'(.+?), (Greater|Lesser|Improved|Advanced|Master|Superior|True|Major|Minor)', n, re.I)
    if m:
        yield f'{m.group(2)} {m.group(1)}', None, None, None
    m = re.fullmatch(r'(Greater|Lesser|Improved|Advanced|Master|Superior|True|Major|Minor) (.+)', n, re.I)
    if m:
        yield f'{m.group(2)}, {m.group(1)}', None, None, None


# 名稱結尾的家族字 → AoN 家族名（`Efreeti Bloodline` 在 AoN 就叫 `Efreeti`，家族 Bloodline）
FAMILY_SUFFIX = [
    ('Bloodrager Bloodline', ('Bloodrager Bloodline',)), ('Bloodline', ('Bloodline', 'Bloodrager Bloodline')),
    ('Resonant School', ('Implement School',)), ('Subdomain', ('Domain', 'Druid Domain')), ('Domain', ('Domain', 'Druid Domain')),
    ('Inquisition', ('Inquisition',)), ('Mystery', ('Mystery',)), ('Patron', ('Patron Spells', 'Unique Patron')),
    ('Spirit', ('Shaman Spirit', 'Medium Spirit')), ('Order', ('Order',)), ('Blessing', ('Blessing',)),
    ('Discipline', ('Psychic Discipline',)), ('Oath', ('Oath',)), ('Curse', ('Oracle Curse',)),
    ('Focus', ('Emotional Focus', 'Animal Focus')),
    ('School', ('Arcane School', 'Implement School', 'Variant School')),
    ('Element', ('Kineticist Element',)), ('Aspect', ('Shifter Aspect', 'Ward Aspect')),
    ('Infusion', ('Wild Talent',)), ('Hex', ('Hex', 'Shaman Hex')),   # Foundry 的注能都加了 Infusion：`Force Hook Infusion` → `Force Hook`
]


def r_family_suffix(n):
    """去掉結尾的家族字：`Efreeti Bloodline` → `Efreeti`、`Force Hook Infusion` → `Force Hook`、`Flight Hex` → `Flight`"""
    for suf, fams in FAMILY_SUFFIX:
        if n.endswith(' ' + suf) and len(n) > len(suf) + 1:
            yield n[:-len(suf) - 1], None, fams, None
            return


def r_bomb(n):
    """炸彈發現：Foundry `Anarchic Bomb`，AoN `Anarchic Bombs`"""
    if n.endswith(' Bomb'):
        yield n + 's', None, ('Discovery',), None


def r_subschool(n):
    """子學派：Foundry 寫 `Foresight Subschool`，AoN 寫 `Foresight School`"""
    if n.endswith(' Subschool'):
        yield n[:-len('Subschool')] + 'School', None, ('Arcane School 能力',), None


def r_paren_parent(n):
    """結尾括號是上層名：`Elemental Movement (Earth)` → 上層 Earth 底下的 `Elemental Movement`"""
    m = re.fullmatch(r'(.+?) \(([A-Za-z ]+)\)', n)
    if m and m.group(2).upper() not in ABBR and not re.fullmatch(r'\d pts?', m.group(2)):
        yield m.group(1), None, None, m.group(2)


def r_parent_generic(n):
    """拆開「上層＋通用能力名」：`Battle Final Revelation` → 秘示域 Battle 的 `Final Revelation`"""
    for gen, fams in (('Final Revelation', ('Mystery 能力',)), ('Spirit Manifestation', ('Shaman Spirit 能力',)),
                      ('Manifestation', None)):
        if n.endswith(' ' + gen) and len(n) > len(gen) + 1:
            yield gen.replace('Spirit ', ''), None, fams, n[:-len(gen) - 1]
            return


def r_abbr_parent(n):
    """職業縮寫後面再接上層名：`Resiliency (ORA) (Battle)` → 先知、秘示域 Battle 的 `Resiliency`"""
    m = re.fullmatch(r'(.+?) \(([A-Z]{2,3})\) \(([A-Za-z ]+)\)', n)
    if m and m.group(2) in ABBR:
        yield m.group(1), ABBR[m.group(2)], None, m.group(3)


def r_prefix(n):
    """拆開「上層：能力」：`Wildfire Blessing: Fiery Wake` → 祝福 Wildfire 底下的 `Fiery Wake`"""
    m = re.fullmatch(r'(.+?): (.+)', n)
    if m:
        parent = m.group(1)
        fams = None
        for suf, fs in FAMILY_SUFFIX:
            if parent.endswith(' ' + suf):
                parent, fams = parent[:-len(suf) - 1], tuple(f + ' 能力' for f in fs)
                break
        yield m.group(2), None, fams, parent


RULES = [r_same, r_exception, r_abbr, r_uc, r_points, r_paren_family, r_paren_parent, r_inverted, r_family_suffix,
         r_subschool, r_bomb, r_parent_generic, r_abbr_parent, r_prefix, r_element]


def rule_doc(f):
    return f.__doc__.strip().splitlines()[0]


def match(name, fv, by_key):
    """回傳 (候選列表, 規則, 有沒有職業可核, 備註)。第一條有結果的規則就停。"""
    fv_cls = set(fv.get(name, {}).get('classes') or [])
    notes = []
    for rule in RULES:
        for aon_name, cls_hint, fam_hint, parent_hint in rule(name):
            cands = by_key.get(key(aon_name), [])
            if fam_hint:
                cands = [c for c in cands if any(f.lower() in c['family'].lower() for f in fam_hint)]
            if parent_hint:
                cands = [c for c in cands if key(c['parent']) == key(parent_hint)]
            if not cands:
                continue
            want0 = set(cls_hint or fv_cls)
            want = set(want0)
            if want:
                # 掉鏈子職業的能力，AoN 有時只掛在原版職業頁上（反之亦然），兩邊都認
                want |= {UNCHAINED_BASE[c] for c in want if c in UNCHAINED_BASE}
                ok = [c for c in cands if set(c['classes']) & want]
                if not ok:
                    notes.append(f'「{aon_name}」AoN 有，但職業不同（AoN：'
                                 + '、'.join(sorted({x for c in cands for x in c['classes']})) + '）')
                    continue
                cands = ok
            uniq = list({(c['url'], c['key']): c for c in cands}.values())
            if len(uniq) > 1:
                uniq = narrow(name, uniq, want0, fv.get(name, {}).get('tags'), notes)
            return uniq, rule, want0, notes
    return [], None, set(), notes


def _is_uc(c):
    return bool(c['classes']) and all('Unchained' in x for x in c['classes'])


def tag_parents(tags):
    """Foundry 標籤裡的上層名（`Battle Mystery` → battle）。"""
    return {key(re.sub(r' (?:Mystery|Domain|Subdomain|Bloodline|Blessing|Spirit|School|Order|Inquisition|'
                       r'Patron|Discipline)$', '', tg)) for tg in tags or ()}


def narrow(name, cands, want, tags, notes):
    """同名不只一條時，用 Foundry 這邊看得到的線索收窄；收不窄就原樣回去（報「多筆」）。

    一、掉鏈子：名稱帶 (UC) 留掉鏈子版；沒帶、而且所屬職業有原版職業的，留原版
    二、標籤寫了上層（`Battle Mystery`）的，留那個上層底下的
    三、標籤：Foundry 標了「Rogue Talent」「Alchemist Discovery」的，留家族名有同一個字的
        （`Mutagen` 標了鍊金發現就是發現那條，不是職業頁的突變劑）；沒有標籤的留職業頁那條
    """
    uc = '(UC)' in name or (want and all('Unchained' in w for w in want))
    if uc:
        keep = [c for c in cands if _is_uc(c) or '(UC)' in c['family']]
    elif want:
        keep = [c for c in cands if not _is_uc(c) and '(UC)' not in c['family']]
    else:
        keep = cands
    if keep and len(keep) < len(cands):
        notes.append('AoN 另有' + ('原版' if uc else '掉鏈子版') + '同名條目，已排除')
        cands = keep
    if len(cands) > 1 and tags:
        # 天啟、領域能力：Foundry 標籤寫了上層（`Battle Mystery`），留上層同名的那條
        ups = tag_parents(tags)
        keep = [c for c in cands if c['parent'] and key(c['parent']) in ups]
        if keep and len(keep) < len(cands):
            notes.append('照 Foundry 標籤的上層挑（' + '、'.join(tags) + '）')
            cands = keep
    if len(cands) > 1 and tags is not None:   # 不在現行 pf1-data 的舊鍵看不到標籤，不挑
        words = {w.lower() for tg in tags for w in re.findall(r'[A-Za-z]+', tg)} - {'of', 'the'}
        if words:
            keep = [c for c in cands if words & {w.lower() for w in re.findall(r'[A-Za-z]+', c['family'])}]
        else:
            keep = [c for c in cands if c['family'] == 'Class Feature']
        if keep and len(keep) < len(cands):
            notes.append('照 Foundry 標籤挑家族（' + ('、'.join(tags) or '沒有標籤＝職業本身的能力') + '）')
            cands = keep
    return cands


def shared(cands, want, tags=()):
    """同一個名稱掛在好幾個職業頁、每個職業 Foundry 都有列：Foundry 一條共用，AoN 各頁各一份。
    子領域（與其能力）也算：AoN 在它所屬的兩個領域頁各列一次。
    好幾個上層共有的能力也算（`Combat Healer` 屬於 Battle、Life、Succor 三個秘示域，Foundry 標籤三個都列）。"""
    if len(cands) < 2 or len({c['key'] for c in cands}) > 1:
        return False
    if all(c['family'] == 'Domain 能力' for c in cands):
        return True   # 子領域在每個所屬領域的頁面都列一次，內文相同
    ups = tag_parents(tags)
    if all(c['parent'] and key(c['parent']) in ups for c in cands):
        return True   # 好幾個秘示域共有的天啟：Foundry 標籤正好列了這幾個上層
    if not want:
        return False
    seen = set()
    for c in cands:
        cl = set(c['classes'])
        if not cl or cl & seen or not cl & want:
            return False
        seen |= cl
    return True


# ---------------------------------------------------------------- CHM 端

# CHM 目錄「按類別／職業」底下的職業節點（簡體）→ AoN 職業名。只拿來判斷 CHM 的段落在哪個職業頁
CHM_CLASS = {
    '野蛮人': 'Barbarian', '吟游诗人': 'Bard', '牧师': 'Cleric', '德鲁伊': 'Druid', '战士': 'Fighter',
    '武僧': 'Monk', '圣骑士': 'Paladin', '游侠': 'Ranger', '盗贼': 'Rogue', '术士': 'Sorcerer',
    '法师': 'Wizard', '炼金术师': 'Alchemist', '反圣武士': 'Antipaladin', '骑将': 'Cavalier',
    '铳手': 'Gunslinger', '审判者': 'Inquisitor', '魔战士': 'Magus', '忍者': 'Ninja', '先知': 'Oracle',
    '武士': 'Samurai', '召唤师': 'Summoner', '女巫': 'Witch', '奥能师': 'Arcanist',
    '血脉狂怒者': 'Bloodrager', '拳师': 'Brawler', '猎人': 'Hunter', '调查员': 'Investigator',
    '萨满': 'Shaman', '歌者': 'Skald', '杀手': 'Slayer', '游荡剑客': 'Swashbuckler',
    '战斗祭司': 'Warpriest', '操念使': 'Kineticist', '通灵者': 'Medium', '催眠师': 'Mesmerist',
    '秘学士': 'Occultist', '异能者': 'Psychic', '唤魂师': 'Spiritualist', '侠客': 'Vigilante',
    '变形者': 'Shifter',
}
# CHM 的寫法：清心（Distraction, Su）、破咒曲（Countersong）
CHM_PAIR = re.compile(r'([一-鿿][一-鿿·・]{0,15})\s*[（(]\s*'
                      r"([A-Za-z][A-Za-z0-9'’ \-:/&]{1,70}?)\s*(?:[,，]\s*(?:Ex|Su|Sp)[^)）]{0,12})?[)）]")


def chm_pages():
    """CHM 目錄「按類別／職業」底下每一頁 → 它在哪個職業節點（掉鏈子的節點算成 (Unchained)）。"""
    t = (CHM / 'chmbuild' / 'toc.hhc').read_bytes().decode('gb18030', 'replace')
    path, last, out = [], None, {}
    for m in re.finditer(r'<UL>|</UL>|<OBJECT[^>]*>(.*?)</OBJECT>', t, re.S | re.I):
        tok = m.group(0).upper()
        if tok == '<UL>':
            path.append(last)
        elif tok == '</UL>':
            if path:
                path.pop()
        else:
            nm = re.search(r'name="Name"\s+value="([^"]*)"', m.group(1), re.I)
            lc = re.search(r'name="Local"\s+value="([^"]*)"', m.group(1), re.I)
            last = html.unescape(nm.group(1)) if nm else ''
            p = [x for x in path if x]
            if not lc or p[:2] != ['按类别', '职业']:
                continue
            node = (p + [last])[3] if len(p) >= 3 else last
            cls = CHM_CLASS.get(node, '')
            if cls and len(p) >= 3 and 'Unchained' in p[2] and cls in ('Barbarian', 'Monk', 'Rogue', 'Summoner'):
                cls += ' (Unchained)'
            out.setdefault(lc.group(1).split('#')[0], set()).add(cls)
    return out


def load_chm():
    """英文鍵 → [(中文, 頁, 職業), …]；CHM 不在回 None。"""
    if not (CHM / 'chmbuild' / 'toc.hhc').exists():
        return None
    pairs = defaultdict(list)
    for page, classes in chm_pages().items():
        p = CHM / 'chmbuild' / page
        if not p.is_file():
            continue
        t = p.read_bytes().decode('gb18030', 'replace')
        i = t.lower().find('<body')
        text = html.unescape(re.sub(r'<[^>]+>', '', t[i:] if i >= 0 else t)).replace('\xa0', ' ')
        for zh, en in CHM_PAIR.findall(text):
            for c in classes:
                pairs[key(en)].append((zh, page, c))
    return pairs


def chm_status(aon_name, classes, chm):
    """(有沒有, 頁, 夾註中文)。只在 CHM 職業章節找「中文（English）」夾註，不從標題猜。"""
    if chm is None:
        return '（沒讀 CHM）', '', ''
    hits = chm.get(key(aon_name), [])
    if not hits:
        return '沒有', '', ''
    want = set(classes) | {UNCHAINED_BASE.get(c, c) for c in classes}
    own = [h for h in hits if h[2] in want] if want else []
    use = own or hits
    zhs = Counter(h[0] for h in use)
    pages = Counter(h[1] for h in use)
    st = '有（該職業頁）' if own else ('有（別的職業頁）' if want else '有（職業不明）')
    return st, '|'.join(p for p, _ in pages.most_common(3)), '／'.join(z for z, _ in zhs.most_common(3))


# ---------------------------------------------------------------- 抓頁（只補缺的）

def _pf1():
    sys.path.insert(0, str(TOOLS))
    import pf1
    pf1.PACKS = PACKS
    return pf1


# 最後一欄：清單頁本身的條目職業選項索引沒收（奧術學派），要連上層名一起算一條
EXTRA_LISTS = [
    ('WizardSchools.aspx', r'SchoolDisplay\.aspx\?ItemName=', 'Arcane School', ['Wizard'], True),
    ('CavalierOrders.aspx', r'CavalierOrders\.aspx\?ItemName=', 'Order', ['Cavalier', 'Samurai'], False),
]
# 沒有個別詳情頁、整個家族寫在一頁的：能力的上層是它前面最近的 h2 標題（`Anger Inquisition`、`Archmage`）
LIST_PAGES = [
    ('Inquisitions.aspx', 'Inquisition', ['Inquisitor', 'Cleric']),
    ('MediumSpirits.aspx', 'Medium Spirit', ['Medium']),
]


def fetch():
    """AoN 職業頁與「有詳情頁」的職業選項（血統、秘示域、領域、祝福……）存原始 HTML。

    pf1.py 的職業選項索引只到選項名（`Battle` 秘示域），底下的天啟、領域能力要看詳情頁。
    """
    pf1 = _pf1()
    CLASS_DIR.mkdir(parents=True, exist_ok=True)
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)
    t, _ = pf1.fetch(AON + 'Classes.aspx')
    classes = sorted({pf1.link_name(x) for x in re.findall(r'ClassDisplay\.aspx\?ItemName=([^"]*)', t)})
    for c in classes:
        p = CLASS_DIR / f'{c}.html'
        if not p.exists():
            p.write_text(pf1.fetch(AON + 'ClassDisplay.aspx?ItemName=' + urllib.parse.quote(c))[0],
                         encoding='utf-8')
            print('職業頁', c, flush=True)
    disp = {pg: d for pg, _f, _c, _l, d in pf1.CLASSOPT_PAGES}
    idx = {}
    for x in json.loads((INDEX / 'aon-class-options.json').read_text(encoding='utf-8')):
        if not (x.get('param') and x.get('url_name')):
            continue
        dp = disp.get(x['page']) or x['page'].split('?')[0]
        url = f"{dp}?{x['param']}={urllib.parse.quote(x['url_name'])}"
        fn = re.sub(r'[^\w\-]+', '_', x['family'] + '__' + x['url_name']) + '.html'
        idx[url] = dict(family=x['family'], url_name=x['url_name'], classes=x['classes'], file=fn)
        p = DETAIL_DIR / fn
        if p.exists():
            continue
        try:
            p.write_text(pf1.fetch(AON + url)[0], encoding='utf-8')
            print('詳情頁', url, flush=True)
        except Exception as e:
            print('失敗', url, e, flush=True)
    # 職業選項索引沒收、但底下有能力的清單頁：(清單頁, 詳情頁連結樣式, 家族, 職業)
    for lst, pat, fam, cls, own in EXTRA_LISTS:
        t, _ = pf1.fetch(AON + lst)
        for un in sorted({pf1.link_name(x) for x in re.findall(pat + r'([^"]*)', t)}):
            url = pat.replace('\\', '') + urllib.parse.quote(un)
            fn = re.sub(r'[^\w\-]+', '_', fam + '__' + un) + '.html'
            idx[url] = dict(family=fam, url_name=un, classes=cls, file=fn, extra=own)
            p = DETAIL_DIR / fn
            if not p.exists():
                p.write_text(pf1.fetch(AON + url)[0], encoding='utf-8')
                print('詳情頁', url, flush=True)
    for lst, fam, cls in LIST_PAGES:
        fn = '_list__' + lst.replace('.aspx', '.html')
        idx[lst] = dict(family=fam, url_name='', classes=cls, file=fn, list=True)
        p = DETAIL_DIR / fn
        if not p.exists():
            p.write_text(pf1.fetch(AON + lst)[0], encoding='utf-8')
            print('清單頁', lst, flush=True)
    (DETAIL_DIR / '_index.json').write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding='utf-8')


# ---------------------------------------------------------------- 主程式

def baseline(recs_opt, fv_names):
    """idmap 現行規則（pf1.py `_pack_match()`）從職業選項索引對得到的 Foundry 條目（小寫）。"""
    try:
        pf1 = _pf1()
    except Exception:
        return None
    names = {k: {'class-abilities'} for k in (pf1._pack_key(n) for n in fv_names)}
    got = set()
    for r in recs_opt:
        m = pf1._pack_match(r['name'], r['family'], names, ('class-abilities',), r['classes'])
        if m:
            got.add(m)
    return got


COLS = ['Foundry 名', '轉換後名', 'AoN 頁', 'AoN 家族', '規則', '信心', '現行規則',
        'CHM', 'CHM 頁', 'CHM 夾註（參考，未接）', '現有名稱', '備註']


def main():
    ent = json.loads(TR.read_text(encoding='utf-8-sig'))['entries']
    fv = load_fvtt()
    recs = load_aon()
    by_key = defaultdict(list)
    for r in recs:
        by_key[r['key']].append(r)
    chm = load_chm()
    opt = [r for r in recs if r['family'] != 'Class Feature' and not r['family'].endswith(' 能力')]
    base = baseline(opt, list(fv) + list(ent))
    cjk = re.compile(r'[一-鿿]')
    rows = []
    for name in sorted(ent, key=str.lower):
        cands, rule, has_cls, notes = match(name, fv, by_key)
        row = dict.fromkeys(COLS, '')
        row['Foundry 名'] = name
        cur = ent[name].get('name', '')
        row['現有名稱'] = cur if cjk.search(cur) else ''
        if base is not None:
            row['現行規則'] = '對得到' if ' '.join(name.replace('’', "'").split()).lower() in base else '對不到'
        if not cands:
            row['信心'] = '—'
            row['備註'] = '；'.join([x for x in notes if name not in NOT_SAME] + [why_not(name, fv, by_key)])
        else:
            c0 = cands[0]
            row['轉換後名'] = '｜'.join(dict.fromkeys(TYPE_SUF.sub('', c['name'].replace('*', '')) for c in cands))
            row['AoN 頁'] = '｜'.join(dict.fromkeys(c['url'] for c in cands))
            row['AoN 家族'] = '｜'.join(dict.fromkeys(
                c['family'] + (f"（{c['parent']}）" if c['parent'] else '') for c in cands))
            row['規則'] = rule_doc(rule)
            if len(cands) == 1:
                direct = bool(has_cls & set(c0['classes']))
                if has_cls and not direct:
                    notes.append('AoN 只在原版職業頁找到（Foundry 標的是掉鏈子版），要人看')
                row['信心'] = '高' if direct else '中'
            else:
                row['信心'] = '共用' if shared(cands, has_cls, fv.get(name, {}).get('tags')) else '多筆'
            if len(cands) == 1:
                st, pg, zh = chm_status(c0['name'], c0['classes'], chm)
                row['CHM'], row['CHM 頁'], row['CHM 夾註（參考，未接）'] = st, pg, zh
            if name not in fv:
                notes.append('現行 pf1-data 沒有這個名稱（合集包譯文鍵比較舊）')
            row['備註'] = '；'.join(notes)
        rows.append(row)
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter='\t', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    summary(rows)
    print(OUT)


def why_not(name, fv, by_key):
    """對不到的原因，附 AoN 最像的名稱給人看（只當線索，不自動採用：拼字差一兩個字母也可能是兩條不同能力）。"""
    import difflib
    if name in NOT_SAME:
        return '人工確認：跟 AoN 同名／近名的不是同一條能力，不收（' + NOT_SAME[name] + '）'
    msg = 'AoN 名冊裡找不到' if name in fv else '現行 pf1-data 沒有這個名稱，AoN 也找不到'
    base = re.sub(r'(?: \([^)]*\))+$', '', name)
    near = difflib.get_close_matches(key(base), list(by_key), n=1, cutoff=0.85)
    if near:
        msg += f'；最像的 AoN 名稱：{TYPE_SUF.sub("", by_key[near[0]][0]["name"])}'
    return msg


def summary(rows):
    print(f'合集包職業能力 {len(rows)} 條')
    for scope, rs in (('全部', rows), ('現行規則對不到', [r for r in rows if r['現行規則'] == '對不到'])):
        c = Counter(r['信心'] for r in rs)
        print(f'  {scope} {len(rs)}：' + '、'.join(f'{k} {c[k]}' for k in ('高', '中', '共用', '多筆', '—')))
        rc = Counter(r['規則'] for r in rs if r['信心'] in ('高', '中'))
        for k, v in rc.most_common():
            print(f'      {v:>5}  {k}')
        cc = Counter(r['CHM'] for r in rs if r['信心'] in ('高', '中'))
        print('    CHM：' + '、'.join(f'{k} {v}' for k, v in cc.most_common()))


if __name__ == '__main__':
    {'fetch': fetch}.get(sys.argv[1] if len(sys.argv) > 1 else '', main)()
