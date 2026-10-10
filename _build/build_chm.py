# -*- coding: utf-8 -*-
r"""從果園 PF1 CHM 產合集包譯文（名稱＋內文），繁體寫進 translations/，簡體另存。

    python _build/build_chm.py            # 建置：改 translations/，簡體寫旁邊 pf1e-compendium-zhcn/translations/
    python _build/build_chm.py --dry      # 只算、印統計，不寫

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

壞掉時的症狀與要改的地方：
  - 對上 0 條 → 錨點報表檔名或欄位改了，看 KINDS 與 load_report()
  - 內文吃進下一條或整頁 → 停止條件 is_boundary() 不夠，CHM 換了標題樣式
  - 出處欄空白 → 頁首格式變了，看 page_meta()
"""
import argparse, csv, glob, html, json, re, sys
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
CHM = Path(r'D:\TRPG\4_工具與筆記\CHM勘誤')
TREES = {'zh-tw': CHM / 'chmbuild_tc', 'zh-cn': CHM / 'chmbuild'}
UPSTREAM_CN = MOD.parent / 'pf1e_compendium_chn' / 'translations'

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
KINDS = {
    'feat': dict(report='條目索引-專長-*.tsv',
                 files=['pf-content.pf-feats.json', 'pf1.feats.json'],
                 aon='https://aonprd.com/FeatDisplay.aspx?ItemName={}'),
}
NAME_FMT = {'pf-content.pf-feats.json': '{zh} {en}', 'pf1.feats.json': '{zh} {en}'}

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


def clean(raw):
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
    s = LINE_BREAK.sub('\n', s)
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
        line = _balance(line)
        while True:   # Word 留下的空粗體／斜體（<b><i></i></b>）
            new = re.sub(r'<(b|i|em|strong|sup|sub|u)>\s*</\1>', '', line)
            if new == line:
                break
            line = new
        if not re.sub(r'<[^>]+>', '', line).strip(' 　•'):
            continue
        out.append(f'<p>{line}</p>')
    return ''.join(out)


PREREQ = re.compile(r'先決條件|先决条件|前置條件|前置条件')


def trim_next_entry(body):
    """「先決條件」出現第二次＝吃進了下一條（那條沒有錨點），切在下一條的標題之前。"""
    ps = re.findall(r'<p>.*?</p>|<table>.*?</table>', body)
    hits = [i for i, p in enumerate(ps) if PREREQ.search(p)]
    if len(hits) < 2:
        return body
    cut = hits[1] - 1                       # 下一條的標題行
    if cut > hits[0] and re.match(r'<p>\s*<(em|i)>', ps[cut]):
        cut -= 1                            # 標題後面那行斜體導言也是下一條的
    return ''.join(ps[:max(cut, hits[0] + 1)])


TAGS = r'(?:\s*(?:〔[^〕]*〕|【[^】]*】|\[[^\]]*\]|[（(][^）)]{0,12}[）)]|\*|[A-Z]{2,4}\b|pfs\s*\w?))*'


def heading_is(head, en, zh):
    """標題是不是「就是」這條：中文名（可省）＋英文名＋〔戰鬥〕之類的標籤，後面沒有別的。

    擋掉的例子（10-10 抽查抓到的）：
      猛力攻擊（Power Attack），街霸流*……   ← 先決條件清單，不是標題
      奧多里決鬥劍（Weapon Focus：Aldori…）  ← 變體
      跳躍攻擊（神話） Spring Attack (Mythic) ← 神話版
    """
    t = text(head).replace('　', ' ').strip()
    if re.search(r'神話|神话|mythic', t, re.I) and not re.search(r'mythic', en, re.I):
        return False
    zhs = [re.escape(z.strip()) for z in re.split(r'[／/]', zh or '') if z.strip()]
    zp = '(?:%s)?' % '|'.join(zhs) if zhs else ''
    pat = r'^\s*%s\s*[（(]?\s*%s\s*[)）]?%s\s*$' % (zp, re.escape(en), TAGS)
    if re.match(pat, t, re.I):
        return True
    # 英文寫在標題外（標題只有中文）的版面
    return bool(zhs) and re.match(r'^\s*(?:%s)%s\s*$' % ('|'.join(zhs), TAGS), t, re.I) is not None


def extract(tree, links, names):
    """同一條在好幾頁有錨點（總表＋正文＋合集頁＋變體）時挑一處。

    只收標題「就是」這條的（heading_is）。不取最長的：最長的往往是吃進了下一節的那處。
    先切掉吃進來的下一條，再取有內文的裡面最短的那處。
    """
    en, zh = names
    cands = []
    for link in links.split():
        x = extract_one(tree, link)
        if x and x[1] and heading_is(x[0], en, zh):
            body = trim_next_entry(x[1])
            # 排序：有「先決條件／效果」的優先（沒有的多半是總表的一行摘要），再取短的
            full = bool(PREREQ.search(body) or re.search(r'效果|Benefit', body))
            # 同名標題也出現在規則變體頁（健壯在「負傷與活力」也有一條），優先挑目錄在專長章節的
            in_feats = '專長' in x[2]['book'] or '专长' in x[2]['book']
            cands.append((not full, not in_feats, book_rank(x[2]['book']), len(text(body)) < 20,
                          len(body), (x[0], body, x[2])))
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
MAX_TEXT = 2000   # 純文字超過這個長度多半是吃進了整節（頁尾最後一條沒有下一個錨點），丟掉不用；專長九成在 600 字內


def extract_one(tree, link):
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
    body_end = up.find('</BODY>', m.end())
    end = min(nxt.start() if nxt else len(s), body_end if body_end >= 0 else len(s))
    seg = s[m.end():end]
    h = HEAD_END.search(seg)
    head, body = (seg[:h.start()], seg[h.end():]) if h else (seg, '')
    body = clean(body)
    if len(text(body)) > MAX_TEXT:
        return None
    return head, body, page_meta(s, m.start(), name)



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
    for kind, cfg in KINDS.items():
        rname, rows = load_report(cfg['report'])
        print(f'[{kind}] 錨點報表 {rname}：{len(rows)} 條')
        got = {}
        for lang in TREES:
            for r in rows:
                en = r['英文']
                zh = r['中文'] if lang == 'zh-cn' else to_tw(r['中文'])   # 名稱用 CHM 線定好的，不從標題猜
                x = extract(lang, r['連結'], [en, zh])
                if not x:
                    stats[f'{kind} {lang} 沒有可用的定義處'] += 1
                    continue
                head, body, meta = x
                if '／' in zh:   # 報表的中文名有時是幾個候選串起來的，取標題裡實際出現的那個
                    ht = text(head)
                    zh = next((z for z in zh.split('／') if z and z in ht), zh.split('／')[0])
                if not body:
                    stats[f'{kind} {lang} 內文空白'] += 1
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
                        # 對照表沒收的：要先知道合集包裡真的有這條才補（pack 名單另外接），這裡先只計數
                        stats[f'{fname} {lang} CHM 有但對照表沒收'] += 1
                        continue
                    stats[f'{fname} {lang} 取代'] += 1
                    ent[key]['name'] = fmt.format(zh=it['zh'], en=key)
                    ent[key]['description'] = it['desc']
                    if lang == 'zh-tw':
                        record.setdefault(fname, {})[key] = it['link']
                if not a.dry:
                    save_tr(dst, d, ref=TR / fname)
    # 簡體模組其餘沒有 CHM 條目的檔：照抄上游（修掉 JSON 語法錯誤）
    if not a.dry and OUT_CN.parent.exists():
        done = {f for cfg in KINDS.values() for f in cfg['files']}
        for src in sorted(UPSTREAM_CN.glob('*.json')):
            if src.name not in done:
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
