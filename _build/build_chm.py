# -*- coding: utf-8 -*-
r"""從果園 PF1 CHM 產合集包譯文（名稱＋內文），繁體寫進 translations/，簡體另存。

    python _build/build_chm.py            # 建置：改 translations/，簡體寫旁邊 pf1e-compendium-zhcn/translations/
    python _build/build_chm.py --dry      # 只算、印統計，不寫

路徑寫死成他本機的位置；別台機器（雲端）用環境變數指過去，沒設就用本機路徑：
    PF1_CHM_DIR     CHM勘誤（pf1-chm-src）  PF1_IDMAP  idmap.tsv  PF1_DATA_PACKS  pf1-data\packs

**CHM 優先**（他 2026-10-10 定）：CHM 有的條目，名稱與內文都換成 CHM；
CHM 沒有的維持原本的譯文（上游簡體稿繁化，或用語集補的名稱）。

來源（都只讀）：
  CHM勘誤\chmbuild_tc\   繁體 CHM（CHM 線用 TcFixer 轉的，簡轉繁修正已在裡面，這裡不再轉）
  CHM勘誤\chmbuild\      簡體 CHM
  CHM勘誤\_資料\條目索引-<類>-*.tsv   CHM 線的條目錨點報表（英文 → 頁#錨點）

定位靠 CHM 線插的條目錨點 `<A NAME="feat-xxx">`，**不在這裡另寫一套找定義處的規則**。
CHM 線每加一類錨點（計畫一週一類），在 KINDS 加一列就多吃一類，這就是兩邊的連動：
CHM 週五發版 → 重跑這支 → 合集包發新版。

每條內文最後附一行出處（他定的四項）：譯者 ID、書目、CHM 出處（果園帖）、AoN 出處。
譯者、書目、果園帖取該錨點之前最近的一次頁內宣告，頁內沒有就取頁首。

專長的比對分兩輪（2026-10-31 放寬）：先用嚴格比對挑，一處都挑不到才用放寬比對，
已經吃進的條目不會因為放寬而換頁。放寬認得哪些版面寫在 heading_is()。

壞掉時的症狀與要改的地方：
  - 對上 0 條 → 錨點報表檔名或欄位改了，看 KINDS 與 load_report()
  - 內文吃進下一條或整頁 → trim_next_entry()（第二個「先決條件」）、drop_tail_heading()（結尾的下一條標題）
    、extend_cut()（跳過行中錨點後多切的那段）不夠，CHM 換了標題樣式
  - 內文斷在半句（「先決條件：」後面沒了）→ CHM 錨點插在句子中間，看 inline_anchor()
  - 出處欄空白 → 頁首格式變了，看 page_meta()
"""
import argparse, csv, glob, html, json, os, re, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
MOD = HERE.parent
TR = MOD / 'translations'
# 簡體版是另一個模組（pf1e-compendium-zhcn），譯文直接寫進它的 translations/：
# 上游 pf1e_compendium_chn 的簡體稿當底，CHM 有的條目換成 CHM 簡體版
OUT_CN = MOD.parent / 'pf1e-compendium-zhcn' / 'translations'
BASE = HERE / 'base'   # 套 CHM 之前的繁體譯文。改上游繁化或用語集補名稱時改這裡，再重跑本支
# 路徑：環境變數優先，沒設就用他本機的位置（雲端或別台機器跑時用環境變數指過去）
#   PF1_CHM_DIR    CHM勘誤（pf1-chm-src）資料夾，裡面要有 chm.py、chmbuild\、chmbuild_tc\、_資料\
#   PF1_IDMAP      Tools\pf1\pf1-index\idmap.tsv
#   PF1_DATA_PACKS Tools\pf1\pf1-data\packs
CHM = Path(os.environ.get('PF1_CHM_DIR') or r'D:\TRPG\4_工具與筆記\CHM勘誤')
TREES = {'zh-tw': CHM / 'chmbuild_tc', 'zh-cn': CHM / 'chmbuild'}
UPSTREAM_CN = MOD.parent / 'pf1e_compendium_chn' / 'translations'
# 繁中版刪掉的對照檔（對的合集包在 PF1 11 已不存在，2026-10-31）：簡體版照抄上游時跳過，免得又被寫回去。
# 簡體模組裡已經有的要手動刪一次，這支不刪檔。
# 怪物相關四檔的簡體版是 basic_monsters.py／monster_packs.py 自己產的（上游那份有錯譯，也用了本模組沒有的 tags 轉換器），也不照抄上游
DROPPED = {f'pf1-bestiary.bestiary-{n}.json' for n in ('00', '02', '04', '06', '08', '11', '15', '20')} | {
    'pf1.commonbuffs.json', 'pf1.mythicpaths.json', 'pf1.pf1e-rules.json', 'pf1.racialhd.json',
    'pf1.basic-monsters.json', 'pf1.monster-templates.json', 'pf1.template-abilities.json', 'pf1.monster-abilities.json'}

# 名稱的簡轉繁跟 CHM 繁體版同一套（s2tw＋CHM 線的例外表），不另寫
sys.path.insert(0, str(CHM))
import chm  # noqa: E402
import opencc  # noqa: E402
_S2TW = opencc.OpenCC('s2tw')
_TW2S = opencc.OpenCC('tw2s')
_FIX = chm.TcFixer()
CHM_VER = re.search(r'v[\d.]+', chm.CHM_NAME).group(0)


def to_tw(s):
    return _FIX(_S2TW.convert(s))

# 類別：錨點報表的檔名樣式、要寫進哪些翻譯檔、AoN 網址樣式、名稱格式
# max：內文純文字長度上限（超過多半是吃進了整節）；chapter：同名多處時優先挑 CHM 目錄在這個章節的；
# loose：嚴格比對挑不到時改用放寬比對（見 extract()、heading_is()）；tidy_tail：拿掉結尾黏到的下一條標題（drop_tail_heading()）
# skip_inline_anchor：切條時跳過插在句子中間的錨點（inline_anchor()）
# drop_table：拿掉標題後第一張表（法術的屬性表，Foundry 法術卡已經用欄位顯示學派、環位等，留著會重複）
KINDS = {
    'feat': dict(report='條目索引-專長-*.tsv',
                 files=['pf-content.pf-feats.json', 'pf1.feats.json'],
                 aon='https://aonprd.com/FeatDisplay.aspx?ItemName={}',
                 max=2000, chapter=('專長', '专长'), loose=True, tidy_tail=True,
                 skip_inline_anchor=True),
    'spell': dict(report='條目索引-法術-*.tsv',
                  files=['pf1.spells.json'],
                  aon='https://aonprd.com/SpellDisplay.aspx?ItemName={}',
                  max=6000, chapter=('法術', '法术'), drop_table=True),
}
NAME_FMT = {'pf-content.pf-feats.json': '{zh} {en}', 'pf1.feats.json': '{zh} {en}',
            'pf1.spells.json': '{zh} ({en})'}
CFG = KINDS['feat']   # main() 逐類切換

BLOCK = re.compile(r'<P\b.*?</P>|<TABLE\b.*?</TABLE>', re.S | re.I)
TAG = re.compile(r'<[^>]+>')
URL = re.compile(r'https?://www\.goddessfantasy\.net/bbs/index\.php\?topic=[^\s"<>]+')
# 「譯者：傻豆」中間常夾 </SPAN><SPAN> 之類的標籤
TRANS = re.compile(r'(?:譯者|译者)\s*(?:<[^>]+>\s*)*[:：]\s*(?:<[^>]+>\s*)*([^<\n\r]+)')


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(TAG.sub('', s)).replace('\xa0', ' ')).strip()


_cache = {}


def page(tree, name):
    k = (tree, name)
    if k not in _cache:
        _cache[k] = (TREES[tree] / name).read_bytes().decode('gb18030', 'replace')
    return _cache[k]


def _toc():
    """CHM 目錄：頁檔名 → 目錄路徑（例：專長／進階職業手冊）。書目找不到「來源」行時用它。"""
    t = (TREES['zh-tw'] / 'toc.hhc').read_bytes().decode('gb18030', 'replace')
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
            if lc:
                out.setdefault(lc.group(1).split('#')[0], [p for p in path if p] + [last])
    return out


TOC = None


def clean_translator(t):
    t = text(t).strip(' ，,、;；')
    if not t or len(t) > 40 or re.search(r'[…）)！!？?。]', t):
        return ''   # 抓到的是聊天句子不是 ID
    return t


def page_meta(s, pos, name):
    """錨點之前最近的果園帖、譯者；書目取目錄路徑（條目裡有「來源」行時 credit() 改用那行）。"""
    global TOC
    if TOC is None:
        TOC = _toc()
    head = s[:pos]
    urls = URL.findall(head) or URL.findall(s)
    tr = ''
    for cand in list(reversed(TRANS.findall(head))) + TRANS.findall(s):
        tr = clean_translator(cand)
        if tr:
            break
    toc = TOC.get(name, [])
    return dict(url=html.unescape(urls[-1]) if urls else '', translator=tr,
                book='／'.join(toc[-2:]) if toc else '')


INLINE = {'b', 'strong', 'i', 'em', 'sup', 'sub', 'u'}
TABLE_TAGS = {'table', 'tr', 'td', 'th', 'tbody', 'thead'}
LINE_BREAK = re.compile(r'<BR\s*/?>|</P>|</DIV>|<HR\b[^>]*>|</H\d>|</LI>', re.I)
# 放寬比對用：<BR> 常帶屬性（<BR style='…'>），上面那條不認，整條會擠成一段。
# 嚴格比對已經挑到的條目維持舊切法（不讓已發布的條目跟著變），只有放寬才吃進來的用這條
LINE_BREAK_LOOSE = re.compile(r'<BR\b[^>]*>|</P>|</DIV>|<HR\b[^>]*>|</H\d>|</LI>', re.I)


def _strip_tags(s, keep):
    def tag(m):
        close, name = m.group(1), m.group(2).lower()
        return f'<{close}{name}>' if name in keep else ''
    return re.sub(r'<(/?)([A-Za-z][\w:]*)\b[^>]*>', tag, s)


def _balance(frag):
    """一行裡沒關的粗體／斜體補關、沒開的關閉標籤丟掉（CHM 的 <B> 常跨行）。"""
    import warnings
    from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
    warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
    return ''.join(str(x) for x in BeautifulSoup(frag, 'html.parser').contents)


def clean(raw, loose=False):
    """Word 轉出的 HTML → Foundry 用的乾淨段落：只留粗斜體、上下標、表格，每行一個 <p>。"""
    s = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
    s = re.sub(r'<o:p>.*?</o:p>', '', s, flags=re.S | re.I)
    s = re.sub(r'<(script|style)\b.*?</\1>', '', s, flags=re.S | re.I)
    tables = []

    def stash(m):
        t = _strip_tags(m.group(0), TABLE_TAGS | INLINE)
        t = re.sub(r'\s+', ' ', t.replace('&nbsp;', ' '))
        tables.append(_balance(t))
        return f'\n\x00{len(tables) - 1}\x00\n'
    s = re.sub(r'\s+', ' ', s)   # 原始檔裡的換行只是 Word 斷行，不是段落（不收掉會把句子切斷）
    s = re.sub(r'<TABLE\b.*?</TABLE>', stash, s, flags=re.S | re.I)
    s = (LINE_BREAK_LOOSE if loose else LINE_BREAK).sub('\n', s)
    s = _strip_tags(s, INLINE)
    s = s.replace('&nbsp;', ' ').replace('\xa0', ' ')
    out = []
    for line in s.split('\n'):
        line = re.sub(r'[ \t\r]+', ' ', line).strip(' 　')
        mt = re.fullmatch(r'\x00(\d+)\x00', line)
        if mt:
            out.append(tables[int(mt.group(1))])
            continue
        line = re.sub(r'^\?\s*', '• ', line)   # Symbol 字型的項目符號轉出來是「?」
        line = re.sub(r'^l\s+(?=[一-鿿])', '• ', line)   # Wingdings 的圓點轉出來是「l」
        line = re.sub(r'[_＿—-]{8,}', '', line)  # Word 用一長串底線或破折號當分隔線
        line = _balance(line)
        while True:   # Word 留下的空粗體／斜體（<b><i></i></b>）
            new = re.sub(r'<(b|i|em|strong|sup|sub|u)>\s*</\1>', '', line)
            if new == line:
                break
            line = new
        if not re.sub(r'<[^>]+>', '', line).strip(' 　•'):
            continue
        out.append(f'<p>{line}</p>')
    # 結尾黏到的下一條純英文標題、字母索引（「E」「Eagle Eye」）：沒有中文的尾段拿掉
    while out and not re.search(r'[㐀-鿿]', re.sub(r'<[^>]+>', '', out[-1])):
        out.pop()
    return ''.join(out)


STAT = re.compile(r'^(?:<[^>]+>)*\s*(?:學派|学派|環位|环位|環級|环级|施法時間|施法时间|施放時間|施放时间|成分|範圍|范围|'
                  r'目標|目标|效果|區域|区域|持續時間|持续时间|豁免|法術抗力|法术抗力)')


def drop_stat_lines(body):
    """法術：開頭一行一行的屬性欄（沒做成表格的頁）拿掉，到第一段不是屬性欄的為止。"""
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    k = 0
    while k < len(ps) and STAT.match(ps[k][3:]):
        k += 1
    return ''.join(ps[k:]) if k else body


PREREQ = re.compile(r'先決條件|先决条件|前置條件|前置条件')
PREREQ_LABEL = re.compile(r'<p>(?:<[^>]+>|\s)*(?:先決條件|先决条件|前置條件|前置条件)')


def trim_next_entry(body):
    """「先決條件」出現第二次＝吃進了下一條（那條沒有錨點），切在下一條的標題之前。

    只認段首的「先決條件」標籤。內文順口提到的（「他不需要滿足這些專長的先決條件」）
    以前也算，結果把本條的「專長效果」整段切掉（10-31 查到震懾拳等六十來條）；
    現在遇到順口提到的，改成從那之後第一個像標題的行切（武器技法後面的職業變體這類）。
    """
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    hits = [i for i, p in enumerate(ps) if PREREQ_LABEL.match(p)]
    if len(hits) < 2:
        first = hits[0] + 1 if hits else 0
        if any(PREREQ.search(p) for p in ps[first:]):
            plain = lambda p: re.sub(r'<[^>]+>', '', p).strip(' 　*')
            for j in range(first + 1, len(ps)):
                h = plain(ps[j])
                if LOOKS_LIKE_HEADING.match(h) or re.fullmatch(SHORT_TITLE, h):
                    return ''.join(ps[:j])
        return body
    cut = hits[1] - 1                       # 下一條的標題行
    # 標題後面那行斜體導言也是下一條的。導言常是粗斜體（<b><i>…），只認 <i> 開頭的話會退不到，
    # 下一條的標題行就黏在本條結尾（武器專攻尾巴的「武器專精（Weapons Specialization）〔戰鬥〕」）
    if cut > hits[0] and re.match(r'<p>\s*(?:<(?:b|strong)>\s*)?<(em|i)>', ps[cut]):
        cut -= 1
    return ''.join(ps[:max(cut, hits[0] + 1)])


# 一行只有「中文 English〔標籤〕」、沒有句讀＝某一條的標題
LOOKS_LIKE_HEADING = re.compile(r'^[^。：:，,；;\d]{1,30}?\s*[（(]?\s*[A-Z][A-Za-z\'’`!\- ,:]{2,}[)）]?\s*'
                                r'(?:〔[^〕]*〕|【[^】]*】|[（(][^）)]{0,12}[)）]|PFS\s*(?:不?可用?|X)?|\s)*$')


# 一行短短的中文、沒有句讀（「巨人粉碎」「章魚專注（戰鬥）」「故事專長」）＝下一條或下一節的標題
SHORT_TITLE = r'[㐀-鿿·]{1,12}(?:[（(][^）)]{0,8}[)）]?)?(?:\s*PFS\s*(?:不?可用?|X)?)?'
OTHER_ZH = {}   # 報表裡各條的中文名 → 英文名（main() 逐語言填）：結尾一行剛好是別條的中文名＝下一條的標題


def drop_tail_heading(body, en, zh=''):
    """結尾黏著的下一條標題（或沒內容的小標）拿掉，最多兩段。

    下一條的英文名在 CHM 拼錯（Weapons Specialization、Hellkngiht）時錨點報表收不到它，
    本條就一路切到再下一個錨點；下一條有「先決條件」時 trim_next_entry() 會切掉，
    沒有的（只剩標題、或標題加導言）靠這裡。認得的形狀：
      地獄騎士狂熱（Hellkngiht Obsession）   ← 一行「中文 English〔標籤〕」、沒有句讀
      巨人粉碎／章魚專注（戰鬥）／故事專長   ← 一行短短的中文、沒有句讀（下一條或下一節的標題）
      譯註                                   ← 頁尾註腳的小標（註腳本身有 <A name> 錨點，切不進來）
      （點擊查看遊俠陷阱）                   ← 指向別頁的連結字
    標題裡有本條英文名或中文名的不動。
    """
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    plain = lambda p: re.sub(r'<[^>]+>', '', p).strip(' 　*')
    own = [z for z in re.split(r'[／/]', zh or '') if z]
    for _ in range(2):
        if len(ps) < 2:
            break
        h = plain(ps[-1])
        if OTHER_ZH.get(h, en) != en or re.fullmatch(r'譯註|译注|譯者註|译者注|[（(](?:點擊|点击|點此|点此)[^）)]*[)）]', h):
            ps.pop()
        elif (re.fullmatch(SHORT_TITLE, h)
              and not any(z in h for z in own)):
            ps.pop()
        elif LOOKS_LIKE_HEADING.match(h) and en.lower() not in h.lower():
            ps.pop()
        elif (len(ps) > 2 and re.match(r'<p>\s*(?:<(?:b|strong)>\s*)?<(em|i)>', ps[-1])
              and LOOKS_LIKE_HEADING.match(plain(ps[-2])) and en.lower() not in plain(ps[-2]).lower()):
            del ps[-2:]   # 標題＋它的斜體導言
        else:
            break
    return ''.join(ps)


TAGS = r'(?:\s*(?:〔[^〕]*〕|【[^】]*】|\[[^\]]*\]|[（(][^）)]{0,12}[）)]|\*|[A-Z]{2,4}\b|pfs\s*\w?))*'


def heading_is(head, en, zh, loose=False):
    """標題是不是「就是」這條：中文名（可省）＋英文名＋〔戰鬥〕之類的標籤，後面沒有別的。

    擋掉的例子（10-10 抽查抓到的）：
      猛力攻擊（Power Attack），街霸流*……   ← 先決條件清單，不是標題
      奧多里決鬥劍（Weapon Focus：Aldori…）  ← 變體
      跳躍攻擊（神話） Spring Attack (Mythic) ← 神話版

    loose=True（只在嚴格比對一處都挑不到時才用，見 extract()）多認這幾種版面：
      破碎衝擊（戰鬥）Crushing Impact                   ← 標籤寫在中英文中間
      密集阻擊 (Barrage of Styles，戰鬥，團隊 ) 出自《…》 ← 標籤寫在英文括號裡、後面接書目
      浪徒之幸(汲引) (Wanderer's Fortune (Conduit)) PFS可 ← 括號套括號、PFS 標記
      美德假面（Mask of Virtue）［詛咒］                  ← 全形方括號
      自發召喚自然盟友 Spontaneous Nature’s Ally          ← 彎引號
    代價是要求更嚴的另一頭：報表有中文名時，標題裡一定要出現那個中文名
    （變體與地區書改寫的中文名不同，靠這條擋；嚴格比對的中文名可省）。
    """
    t = text(head).replace('　', ' ').strip()
    if re.search(r'神話|神话|mythic', t, re.I) and not re.search(r'mythic', en, re.I):
        return False
    if loose:
        return _heading_is_loose(t, en, zh)
    zhs = [re.escape(z.strip()) for z in re.split(r'[／/]', zh or '') if z.strip()]
    zp = '(?:%s)?' % '|'.join(zhs) if zhs else ''
    pat = r'^\s*%s\s*[（(]?\s*%s\s*[)）]?%s\s*$' % (zp, re.escape(en), TAGS)
    if re.match(pat, t, re.I):
        return True
    # 英文寫在標題外（標題只有中文）的版面
    return bool(zhs) and re.match(r'^\s*(?:%s)%s\s*$' % ('|'.join(zhs), TAGS), t, re.I) is not None


_TAG_WORDS = (r'(?:Combat|Teamwork|Meditation|Conduit|Critical|Style|Stare|Coven|Item Creation|Metamagic|Grit|'
              r'Panache|Story|Blood Hex|Achievement|Faith|Performance|Betrayal|Hero Point|Monster|Racial|Weapon Mastery)')
TAGS_LOOSE = (r'(?:\s*(?:〔[^〕]*〕|【[^】]*】|［[^］]*］|\[[^\]]*\]|[（(][^（）()]{0,12}[）)]|\*|'
              r'[（(]\s*%s(?:\s*[,，、]\s*%s)*\s*[）)]|(?:戰鬥|战斗|團隊|团队)?(?:專長|专长)|'
              r'[A-Z]{2,4}\b|pfs\s*(?:不?可用?|X\b|\w)?))*' % (_TAG_WORDS, _TAG_WORDS))


def _heading_is_loose(t, en, zh):
    q = lambda s: re.sub(r'[’‘`´]', "'", s)
    t, en = q(t), q(en)
    t = re.sub(r'(?<=\S)\s*(?:出自|[｜|]|[（(]\s*(?:來源|来源)).*$', '', t)   # 標題後面接的書目、致謝
    t = re.sub(r'(?<=\S)\s+[A-Z][\w\'’ :&-]*\bpg\.\s*\d+\s*$', '', t)      # Goblins of Golarion pg. 25
    t = re.sub(r'(?<=[A-Za-z])\.\s*$', '', t)                               # 大步向前 Longshanks.
    zhs = [z.strip() for z in re.split(r'[／/]', zh or '') if z.strip()]
    if zhs and not any(z in t for z in zhs):
        return False
    zp = '(?:%s)?' % '|'.join(map(re.escape, zhs)) if zhs else ''
    pat = (r'^\s*%s%s\s*[（(]?\s*%s\s*(?:[，,、][^（）()]{0,20})?%s\s*[)）]?%s\s*$'
           % (zp, TAGS_LOOSE, re.escape(en), TAGS_LOOSE, TAGS_LOOSE))
    if re.match(pat, t, re.I):
        return True
    return bool(zhs) and re.match(r'^\s*(?:%s)%s\s*$' % ('|'.join(map(re.escape, zhs)), TAGS_LOOSE),
                                  t, re.I) is not None


def extract(tree, links, names):
    """同一條在好幾頁有錨點（總表＋正文＋合集頁＋變體）時挑一處。

    只收標題「就是」這條的（heading_is）。不取最長的：最長的往往是吃進了下一節的那處。
    先切掉吃進來的下一條，再取有內文的裡面最短的那處。

    兩輪：先用嚴格比對（2026-10-10 那套）挑，一處都挑不到才用放寬比對（KINDS 的 loose）。
    已經吃進的條目因此不會換到別頁的版本——放寬只多吃，不改已發布的條目。
    """
    for loose in (False, True) if CFG.get('loose') else (False,):
        x = _extract(tree, links, names, loose)
        if x:
            return x
    return None


FLAVOR = re.compile(r'^[㐀-鿿][^：:；;，,]*?[。！!]?$|^[㐀-鿿][^：:；;]*[。！!]$')
NOT_FLAVOR = re.compile(r'專長|专长|技能|等級|等级|\d+\s*級|\d+\s*级|加值\s*\+|先決|先决')


def split_flavor(x, en, zh):
    """標題與導言擠在同一行、中間沒有換行（血巫術那批：「鈍刃 blunt blade（血巫術）你用一次詛咒……」）。

    只在這些條件都成立時拆：前半是本條標題（heading_is 放寬版）、後半是一句完整的話、
    不含先決條件會出現的字（專長、技能、等級、加值+），而且內文第一行就是「先決條件」。
    拆出來的導言放回內文開頭（不是丟掉）。對不上就回 None。
    """
    head, body, meta = x
    t = text(head).replace('　', ' ').strip()
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    if not ps or not PREREQ.search(ps[0]):
        return None
    for i in range(1, len(t)):
        rest = t[i:].strip()
        if not re.match(r'[㐀-鿿]', rest) or not FLAVOR.match(rest) or NOT_FLAVOR.search(rest):
            continue
        if heading_is(t[:i], en, zh, True):
            return t[:i], f'<p>{html.escape(rest, quote=False)}</p>' + body, meta
    return None


def _extract(tree, links, names, loose):
    en, zh = names
    cands = []
    # 報表用空格分隔多個連結，但法術頁檔名本身有空格（Spell CRB.html），照「…html#錨點」的形狀切
    for link in re.findall(r'[^\s#][^#]*?\.html?#[\w-]+', links):
        x = extract_one(tree, link, loose)
        if loose and x and x[1] and not heading_is(x[0], en, zh, True):
            x = split_flavor(x, en, zh) or x
        if x and x[1] and heading_is(x[0], en, zh, loose):
            raw = trim_next_entry(x[1])
            # 排序看切尾巴之前的內文：drop_tail_heading() 只修內容，不該改變挑哪一頁
            body = drop_tail_heading(raw, en, zh) if CFG.get('tidy_tail') else raw
            # 排序：有「先決條件／效果」的優先（沒有的多半是總表的一行摘要），再取短的
            full = bool(PREREQ.search(raw) or re.search(r'效果|Benefit', raw))
            if loose and not full:
                continue   # 放寬比對只收有正文的：只有標題或一串標題的（目錄、清單）不收
            # 同名標題也出現在規則變體頁（健壯在「負傷與活力」也有一條），優先挑目錄在該類章節的
            in_feats = any(k in x[2]['book'] for k in CFG.get('chapter', ()))
            x[2]['loose'] = loose
            cands.append((not full, not in_feats, book_rank(x[2]['book']), len(text(raw)) < 20,
                          min(len(raw), x[2].get('cut_at', len(raw))), (x[0], body, x[2])))
    if not cands:
        return None
    return min(cands, key=lambda c: c[:5])[5]


# 同名條目在好幾本書都有（地區書常改寫核心專長）時，照這個順序挑：核心書在前
BOOK_ORDER = ['CRB', 'APG', 'UM', 'UC', 'ARG', 'ACG', 'UI', 'UW', 'OA', 'MA', 'UE', 'B1']


def book_rank(book):
    for i, b in enumerate(BOOK_ORDER):
        if re.search(r'\b%s\b' % b, book):
            return i
    return len(BOOK_ORDER)


ANCHOR = re.compile(r'<A NAME="[^"]+">', re.I)
HEAD_END = re.compile(r'<BR\s*/?>|</P>', re.I)
# 放寬比對用：帶屬性的 <BR style='…'> 也算換行。上面那條不認，下一行的斜體導言會黏進標題，
# heading_is() 就判成「不是本條」——10-31 查到放寬前抽不到的專長有六成卡在這裡
HEAD_END_LOOSE = re.compile(r'<BR\b[^>]*>|</P>', re.I)
MAX_TEXT = 2000   # 純文字超過這個長度多半是吃進了整節（頁尾最後一條沒有下一個錨點），丟掉不用；專長九成在 600 字內


LINE_START = re.compile(r'<BR\b[^>]*>|</?P\b[^>]*>|</?DIV\b[^>]*>|<HR\b[^>]*>|</H\d>|</?LI\b[^>]*>|</?T[RD]\b[^>]*>', re.I)


def inline_anchor(s, lo, a):
    """位置 a 的錨點是不是插在一行的中間（不是一條的開頭）。

    CHM 的錨點報表有時把先決條件、內文裡提到的別條專長也當成定義處插了錨點：
      先決條件：<A NAME="feat-critical-focus">重擊專攻（Critical Focus），BAB+15
    照「錨點到錨點」切的話本條就斷在「先決條件：」（10-31 查到已發布的專長有 106 條這樣斷掉）。
    判準：錨點前面、同一行裡已經有字（【CRB】這類書目標記不算字）＝行中間。
    """
    starts = [x.end() for x in LINE_START.finditer(s, lo, a)]
    pre = text(s[starts[-1] if starts else lo:a])
    return bool(re.sub(r'【[^】]*】|［[^］]*］|[\s*•·]', '', pre))


MARK = '\ue000'   # 私用區字元，CHM 原文不會有


def extend_cut(body):
    """跳過行中錨點多切進來的那段（記號之後）裡，遇到像下一條標題的行就停。

    回傳 (內文, 原切點在內文裡的位置)。原切點拿去排序（_extract），
    已經挑好頁的條目才不會因為內文變長就換到別頁。
    """
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    plain = lambda p: re.sub(r'<[^>]+>', '', p).replace(MARK, '').strip(' 　*')
    i = next(i for i, p in enumerate(ps) if MARK in p)
    for j in range(i + 1, len(ps)):
        h = plain(ps[j])
        if (LOOKS_LIKE_HEADING.match(h) or re.fullmatch(SHORT_TITLE, h)
                or OTHER_ZH.get(h)):
            ps = ps[:j]
            break
    out = ''.join(ps)
    return out.replace(MARK, ''), out.index(MARK)


def extract_one(tree, link, loose=False):
    """從錨點切到下一個錨點（或頁尾）。回傳 (標題 HTML, 內文 HTML, meta)。

    CHM 的版面很雜：一條一段、好幾條擠一段用 <BR> 隔、標題後先接一條橫線……
    所以不照段落切，照「錨點到錨點」切，再把換行重排成段落。
    錨點在表格裡＝總表那一列，回 None（同一條通常另有正文處）。
    """
    name, anchor = link.split('#')
    s = page(tree, name)
    m = re.search(r'<A NAME="%s">' % re.escape(anchor), s, re.I)
    if not m:
        return None
    up = s.upper()
    if up.rfind('<TABLE', 0, m.start()) > up.rfind('</TABLE>', 0, m.start()):
        return None
    nxt = ANCHOR.search(s, m.end())
    first = nxt
    while CFG.get('skip_inline_anchor') and nxt and inline_anchor(s, m.end(), nxt.start()):
        nxt = ANCHOR.search(s, nxt.end())
    body_end = up.find('</BODY>', m.end())
    end = min(nxt.start() if nxt else len(s), body_end if body_end >= 0 else len(s))
    seg = s[m.end():end]
    h = (HEAD_END_LOOSE if loose else HEAD_END).search(seg)
    head, body = (seg[:h.start()], seg[h.end():]) if h else (seg, '')
    if first is not nxt and first.start() < end:
        k = first.start() - m.end() - (h.end() if h else len(seg))
        if k < 0:   # 標題行裡就有別的錨點（「甲／乙」兩名並列）：照舊切在那裡
            seg = s[m.end():first.start()]
            h = (HEAD_END_LOOSE if loose else HEAD_END).search(seg)
            head, body = (seg[:h.start()], seg[h.end():]) if h else (seg, '')
        else:
            # 原本的切點做記號：記號之後是跳過行中錨點才多切進來的，extend_cut() 只在這段找下一條的標題
            body = body[:k] + MARK + body[k:]
    if CFG.get('drop_table'):
        t0 = re.search(r'<TABLE\b.*?</TABLE>', body, re.S | re.I)
        if t0 and len(text(body[:t0.start()])) < 10:   # 標題後緊接的那張才是屬性表
            body = body[:t0.start()] + body[t0.end():]
    body = clean(body, loose)
    if CFG.get('drop_table'):
        body = drop_stat_lines(body)
    meta = page_meta(s, m.start(), name)
    if MARK in body:
        body, meta['cut_at'] = extend_cut(body)
    if len(text(body)) > CFG.get('max', MAX_TEXT):
        return None
    return head, body, meta



SOURCE_LINE = re.compile(r'<p>(?:<strong>|<b>)?\s*(?:來源|来源)\s*(?:</strong>|</b>)?\s*[:：]?\s*(.+?)</p>')


def credit(meta, aon, body=''):
    parts = []
    if meta['translator']:
        parts.append('譯者：' + meta['translator'])
    src = SOURCE_LINE.search(body)
    book = text(src.group(1)) if src else meta['book']
    if book:
        parts.append('書目：' + book)
    if meta['url']:
        parts.append(f'CHM 出處：<a href="{html.escape(meta["url"])}">果園原帖</a>（CHM {CHM_VER}）')
    parts.append(f'AoN 出處：<a href="{html.escape(aon)}">Archives of Nethys</a>')
    return '<p class="zhtw-credit"><em>' + '｜'.join(parts) + '</em></p>'


IDMAP = Path(os.environ.get('PF1_IDMAP') or r'C:\Users\User\Tools\pf1\pf1-index\idmap.tsv')
PF1_DATA = Path(os.environ.get('PF1_DATA_PACKS') or r'C:\Users\User\Tools\pf1\pf1-data\packs')
_packs = None


def pack_names(fname):
    """pf1 系統合集包裡實際有哪些條目：小寫英文 → FVTT 原始名稱。

    名單取自 Tools\\pf1 的對照表（idmap.tsv 的 FVTT pack 欄），原始大小寫從 pf1-data 的 YAML 讀
    （idmap 存的是小寫）。只認得 pf1.<pack>.json；pf-content 這類別的模組不在 pf1-data 裡，回空。
    pf1-data 落後於安裝的系統版本時，新條目會補不到（不會補錯）。
    """
    global _packs
    if _packs is None:
        _packs = {}
        if not IDMAP.exists():
            # idmap.tsv 是機器產的、沒進版控（雲端拿不到）。退而直接掃 pf1-data 的 pack 資料夾：
            # 名單比 idmap 寬（idmap 只收對得上 AoN 的），但一樣只認合集包裡真的有的條目
            print('！找不到', IDMAP, '——改直接讀', PF1_DATA)
            for d in PF1_DATA.iterdir() if PF1_DATA.exists() else ():
                for y in d.rglob('*.yaml'):
                    m = re.search(r'^name:\s*(.+?)\s*$', y.read_text(encoding='utf-8'), re.M)
                    if m:
                        nm = m.group(1).strip('\'"')
                        _packs.setdefault(f'pf1.{d.name}.json', {})[nm.lower()] = nm
            return _packs.get(fname, {})
        with open(IDMAP, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                if not r['FVTT pack'] or not r['FVTT路徑']:
                    continue
                for pk, path in zip(r['FVTT pack'].split('|'), r['FVTT路徑'].split('|')):
                    y = PF1_DATA / path
                    if not y.exists():
                        continue
                    m = re.search(r'^name:\s*(.+?)\s*$', y.read_text(encoding='utf-8'), re.M)
                    if m:
                        nm = m.group(1).strip('\'"')
                        _packs.setdefault(f'pf1.{pk}.json', {})[nm.lower()] = nm
    return _packs.get(fname, {})


# 維護者逐條裁定要拿掉的段落：英文名 → 從哪個字串起（含）到內文結尾全部拿掉，繁簡各寫一份。
# CHM 原文有、但不屬於這條專長的東西（同一節的清單、FAQ、譯者旁白）放這裡，不改切條規則。
CUT_FROM = {
    # 2026-10-31：「可選野獸夥伴」是野獸語者那一節的夥伴清單，AoN 本條到「通常」為止
    'Beast Speaker Mastery': ('可選野獸夥伴', '可选野兽伙伴'),
    # 2026-10-31：FAQ 與譯者旁白不收
    "Shifter's Edge": ('FAQ',),
}


def cut_from(en, body):
    """照 CUT_FROM 拿掉指定段落。記號在段首就整段起拿掉；在段落中間就從記號切、補關標籤。"""
    marks = CUT_FROM.get(en)
    if not marks:
        return body
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    for i, p in enumerate(ps):
        k = min((p.find(m) for m in marks if m in p), default=-1)
        if k < 0:
            continue
        head = p[:k]
        if not re.sub(r'<[^>]+>', '', head).strip():
            return ''.join(ps[:i])
        return ''.join(ps[:i]) + _balance(head.rstrip() + '</p>')
    return body


def load_report(pattern):
    files = sorted(glob.glob(str(CHM / '_資料' / pattern)))
    if not files:
        sys.exit('找不到錨點報表 ' + pattern)
    with open(files[-1], encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    return Path(files[-1]).name, [r for r in rows if r.get('連結')]


def load_tr(path, lenient=False):
    t = path.read_text(encoding='utf-8-sig')
    if lenient:   # 上游 pf-content.pf-tables.json 有物件結尾多餘逗號，strict JSON 讀不了
        t = re.sub(r',(\s*[}\]])', r'\1', t)
    return json.loads(t)


def save_tr(path, d, ref=None):
    ref = ref if ref and ref.exists() else path
    m = re.match(r'\{\r?\n( +)', ref.read_text(encoding='utf-8')) if ref.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    s = json.dumps(d, indent=len(m.group(1)) if m else 2, ensure_ascii=False) + '\n'
    path.write_text(s, encoding='utf-8', newline='\r\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    stats = Counter()
    record = {}
    global CFG
    for kind, cfg in KINDS.items():
        CFG = cfg
        rname, rows = load_report(cfg['report'])
        print(f'[{kind}] 錨點報表 {rname}：{len(rows)} 條')
        got = {}
        for lang in TREES:
            OTHER_ZH.clear()
            for r in rows:
                for z in re.split(r'[／/]', r['中文'] if lang == 'zh-cn' else to_tw(r['中文'])):
                    if z:
                        OTHER_ZH.setdefault(z, r['英文'])
            for r in rows:
                en = r['英文']
                zh = r['中文'] if lang == 'zh-cn' else to_tw(r['中文'])   # 名稱用 CHM 線定好的，不從標題猜
                x = extract(lang, r['連結'], [en, zh])
                if not x:
                    stats[f'{kind} {lang} 沒有可用的定義處'] += 1
                    continue
                head, body, meta = x
                body = cut_from(en, body)
                if '／' in zh:   # 報表的中文名有時是幾個候選串起來的，取標題裡實際出現的那個
                    ht = text(head)
                    zh = next((z for z in zh.split('／') if z and z in ht), zh.split('／')[0])
                if not body:
                    stats[f'{kind} {lang} 內文空白'] += 1
                    continue
                if not zh.strip() and meta.get('loose'):
                    # 報表沒給中文名：名稱不從標題猜，放寬才對上的就不收（不然底稿原有的中文名會被蓋成純英文）
                    stats[f'{kind} {lang} 放寬對上但報表沒中文名，不收'] += 1
                    continue
                aon = cfg['aon'].format(en.replace(' ', '%20'))
                cr = credit(meta, aon, body)
                if lang == 'zh-cn':
                    cr = _TW2S.convert(cr)   # 出處行的「譯者／書目／果園原帖」轉簡體（網址是 ASCII，不受影響）
                got.setdefault(en.lower(), {})[lang] = dict(
                    en=en, zh=zh, desc=body + cr, meta=meta, link=r['連結'])
        print(f'  抽到 {len(got)} 條')
        for fname in cfg['files']:
            fmt = NAME_FMT.get(fname, '{zh}（{en}）')
            for lang in TREES:
                # 底稿：繁體讀 _build/base/（套 CHM 之前的譯文快照），不讀 translations/——
                # 讀 translations/ 會疊在上一次的結果上，上次挑錯、這次不再挑的條目就永遠留著錯的
                src = BASE / fname if lang == 'zh-tw' else (UPSTREAM_CN / fname)
                dst = TR / fname if lang == 'zh-tw' else OUT_CN / fname
                if not src.exists():
                    stats[f'{fname} {lang} 沒有底稿'] += 1
                    continue
                d = load_tr(src, lenient=True)
                ent = d['entries']
                lower = {k.lower(): k for k in ent}
                for enl, item in got.items():
                    it = item.get(lang)
                    if not it:
                        continue
                    key = lower.get(enl)
                    if key is None:
                        # 對照表沒收的：合集包裡確定有這條（pack_names）才補，鍵用 FVTT 原始寫法（Babele 照原名比對）
                        key = pack_names(fname).get(enl)
                        if key is None:
                            stats[f'{fname} {lang} CHM 有但合集包沒有'] += 1
                            continue
                        ent[key] = {}
                        stats[f'{fname} {lang} 新增'] += 1
                    else:
                        stats[f'{fname} {lang} 取代'] += 1
                    ent[key]['name'] = fmt.format(zh=it['zh'], en=key).strip()
                    ent[key]['description'] = it['desc']
                    if lang == 'zh-tw':
                        record.setdefault(fname, {})[key] = it['link']
                if not a.dry:
                    save_tr(dst, d, ref=TR / fname)
    # 簡體模組其餘沒有 CHM 條目的檔：照抄上游（修掉 JSON 語法錯誤）
    if not a.dry and OUT_CN.parent.exists():
        done = {f for cfg in KINDS.values() for f in cfg['files']}
        for src in sorted(UPSTREAM_CN.glob('*.json')):
            if src.name not in done and src.name not in DROPPED:
                save_tr(OUT_CN / src.name, load_tr(src, lenient=True), ref=TR / src.name)
                stats['簡體模組 照抄上游'] += 1
    elif not OUT_CN.parent.exists():
        print('！找不到簡體模組資料夾', OUT_CN.parent, '——簡體版沒寫')
    for k, v in sorted(stats.items()):
        print(f'  {k}: {v}')
    if not a.dry:
        (HERE / 'chm_entries.json').write_text(
            json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        print('來源紀錄 →', HERE / 'chm_entries.json')


if __name__ == '__main__':
    main()
