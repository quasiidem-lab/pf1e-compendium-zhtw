# -*- coding: utf-8 -*-
r"""拿果園用語集補名稱、比對譯名差異。

    python _build/glossary_names.py report   # 產審核表 _build/審核/名稱審核.xlsx
    python _build/glossary_names.py apply    # 照審核表的「裁定」欄改 translations/

審核表兩張工作表：

- 補名稱：translations/ 裡名稱還是英文、用語集有譯名的條目
- 譯名差異：已經有中文名、但跟用語集譯名不同的條目

「裁定」欄寫「套」＝用「用語集譯名」欄的值；寫「改」＝用「改為」欄的值；
其他（空白、「不套」、「留上游」）都不動。apply 只動 name（和怪物的 token_name），
不碰內文，名稱格式照各合集包原本的寫法（見 FORMAT）。

用語集的「規範譯名(繁)」有一半是機器從論壇抽的候選（來源「果園用例」），
所以分三級預填裁定：
  A  定案、人工整理、慣用譯名這類核過的來源 → 預填「套」
  B  果園用例、形狀乾淨、分類對得上           → 預填「套」，抽查
  C  果園用例但形狀可疑或分類對不上           → 留空，要逐條看
"""
import csv, json, re, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
TR = HERE.parent / 'translations'
OUT = HERE / '審核' / '名稱審核.xlsx'
GL = Path(r'D:\TRPG\4_工具與筆記\pf1-glossary')

sys.path.insert(0, str(GL))
from check_dirty import why  # noqa: E402  形狀檢查沿用用語集那支，不另寫一套

CJK = re.compile(r'[\u3400-\u9fff]')
TIER_A = {'定案', '人工整理', '慣用譯名', '使用者裁定', '定案（弱證據）', '我翻譯'}

# 各合集包對得上的用語集分類；對不上的降成 C 級
CATS = {
    'pf-content.pf-feats': {'feat', 'mythic', 'trait'},
    'pf1.feats': {'feat', 'mythic', 'trait'},
    'pf1-bestiary': {'monster', 'npc'},
    'pf1.class-abilities': {'class-option', 'archetype', 'archetype-ability', 'discovery',
                            'race-trait', 'mythic', 'feat'},
    'pf1.items': {'magic-item', 'equipment'},
    'pf1.weapons-and-ammo': {'equipment', 'magic-item'},
    'pf1.armors-and-shields': {'equipment', 'magic-item'},
    'pf1.spells': {'spell'},
    'pf1.races': {'race'},
}

# 名稱格式：{zh} 中文、{en} 原文鍵。照各檔已譯條目的多數寫法
FORMAT = {
    'pf-content.pf-feats': '{zh} {en}',
    'pf1.feats': '{zh} {en}',
    'pf1.spells': '{zh} ({en})',
}
DEFAULT_FORMAT = '{zh}（{en}）'


def pack_of(fname):
    stem = fname[:-5]
    return 'pf1-bestiary' if stem.startswith('pf1-bestiary') else stem


def fmt_of(fname):
    return FORMAT.get(pack_of(fname), DEFAULT_FORMAT)


def norm(s):
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'[\s·・\-–—()（）]', '', s).replace('裏', '裡').replace('着', '著')


def load_json(p):
    return json.loads(p.read_text(encoding='utf-8'))


def save_json(p, d):
    m = re.match(r'\{\r?\n( +)', p.read_text(encoding='utf-8'))
    s = json.dumps(d, indent=len(m.group(1)), ensure_ascii=False) + '\n'
    p.write_text(s, encoding='utf-8', newline='\r\n')


def load_glossary():
    ok = set()
    with open(GL / '_已核可.tsv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            ok.add((r['en'], r['category']))
    gl = defaultdict(list)
    with open(GL / '用語集.tsv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            man, std = (r['人工譯名'] or '').strip(), (r['規範譯名(繁)'] or '').strip()
            zh = man or std
            if man.endswith('語') and std and not std.endswith('語'):
                zh = std  # 人工譯名欄填成語言名的，規範欄多半是對的（Goblin：地精語／地精）
            if not zh:
                continue
            src = r['譯名來源'] or ''
            if src == '待定':
                continue
            dirty = '' if (r['en'], r['category']) in ok else why(zh, r['category'])
            # 用語集已知的錯：種族、怪物列的人工譯名被填成語言名（地精語、天狗語）
            if not dirty and zh.endswith('語') and r['category'] != '語言' \
                    and not r['en'].lower().endswith(('language', 'tongue', 'speech')):
                dirty = '人工譯名像語言名'
            # 果園用例會截掉開頭：Beast Shape II → 級獸形術
            if not dirty and re.search(r'\b(I{1,3}|IV|VI{0,3}|IX|\d+)\b', r['en']) \
                    and not re.search(r'[0-9０-９一二三四五六七八九十]|[IVX]', zh):
                dirty = '英文有數字、中文沒有'
            gl[r['en'].strip().lower()].append(
                dict(zh=zh, cat=r['category'], src=src, dirty=dirty))
    return gl


def pick(rows, want):
    """同一英文有多列時，優先分類對得上、來源可靠的那列。"""
    def score(r):
        return (r['cat'] in want, not r['dirty'], r['src'] in TIER_A)
    rows = sorted(rows, key=score, reverse=True)
    best = rows[0]
    others = sorted({r['zh'] for r in rows if r['zh'] != best['zh']})
    return best, others


def tier(best, want):
    fits = best['cat'] in want or best['cat'] == '慣用'  # 慣用譯名跨分類通用
    if best['dirty'] or not fits:
        return 'C'
    return 'A' if best['src'] in TIER_A else 'B'


SUFFIX = re.compile(r'^(.+?) \(([A-Z]{2,4})\)$')
CLS_NAME = re.compile(r'^(.+?)\((.+?)\)（(.+?) \(([A-Z]{2,4})\)）$')


def class_abbr(entries):
    """從已譯的職業能力學 PSY→靈能者 這類縮寫對照。"""
    c = defaultdict(Counter)
    for v in entries.values():
        m = CLS_NAME.match(v.get('name', ''))
        if m:
            c[m.group(4)][m.group(2)] += 1
    return {a: n.most_common(1)[0][0] for a, n in c.items()}


def zh_part(name, en):
    """從現有名稱拿掉英文，剩中文部分。"""
    s = name.replace(en, '')
    s = re.sub(r'[（(]\s*[)）]', '', s)
    return s.strip(' 　')


def collect():
    gl = load_glossary()
    fill, diff = [], []
    for p in sorted(TR.glob('*.json')):
        if '_packs-folders' in p.name:
            continue
        pack = pack_of(p.name)
        want = CATS.get(pack, set())
        ent = load_json(p).get('entries', {})
        abbr = class_abbr(ent) if pack == 'pf1.class-abilities' else {}
        for en, v in ent.items():
            name = v.get('name', '')
            base, cls = en, ''
            m = SUFFIX.match(en)
            if m and pack == 'pf1.class-abilities':
                base, cls = m.group(1), abbr.get(m.group(2), '')
            rows = gl.get(base.lower())
            if not rows:
                continue
            best, others = pick(rows, want)
            gz = best['zh'] + (f'({cls})' if cls else '')
            if m and pack == 'pf1.class-abilities' and not cls:
                continue  # 縮寫對不上，不猜
            row = dict(檔案=p.name, 英文=en, 用語集譯名=gz, 用語集分類=best['cat'],
                       來源=best['src'] or '（空）', 形狀疑點=best['dirty'],
                       其他譯名='、'.join(others))
            if not CJK.search(name):
                t = tier(best, want)
                fill.append(dict(級=t, **row, 現在名稱=name,
                                 裁定='套' if t in 'AB' else '', 改為=''))
            else:
                cur = zh_part(name, en)
                if norm(cur) not in (norm(gz), norm(best['zh'])):
                    t = tier(best, want)
                    diff.append(dict(級=t, **row, 現在中文=cur, 裁定='', 改為=''))
    return fill, diff


HELP = [
    ['名稱審核表', ''],
    ['裁定欄', '「套」＝用「用語集譯名」；「改」＝用「改為」欄；空白或其他字＝不動'],
    ['級 A', '用語集來源是定案、人工整理、慣用譯名，分類也對得上'],
    ['級 B', '來源是果園用例（機器從論壇抽的候選），形狀乾淨、分類對得上。補名稱表預填「套」，請抽查'],
    ['級 C', '果園用例但形狀可疑（黏字、混英數）或分類對不上，要逐條看'],
    ['補名稱', '現在名稱還是英文的條目。A、B 級預填「套」'],
    ['譯名差異', '已經有中文名、但跟用語集不同。全部留空，你決定要不要統一成用語集'],
    ['套回去', 'python _build/glossary_names.py apply（只動名稱，不動內文）'],
    ['譯名本身錯了', '改用語集（sync.py），不要只改這張表；重跑 report 會拿到新值'],
]


def report():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    fill, diff = collect()
    fill.sort(key=lambda r: (r['級'], r['檔案'], r['英文']))
    diff.sort(key=lambda r: (r['級'], r['檔案'], r['英文']))
    wb = Workbook()
    ws = wb.active
    ws.title = '說明'
    for r in HELP:
        ws.append(r)
    ws['A1'].font = Font(bold=True, size=14)
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 90
    shade = {'A': 'E8F5E9', 'B': 'FFFDE7', 'C': 'FFEBEE'}
    for title, rows in (('補名稱', fill), ('譯名差異', diff)):
        ws = wb.create_sheet(title)
        if not rows:
            continue
        cols = list(rows[0].keys())
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r[c] for c in cols])
            ws.cell(ws.max_row, 1).fill = PatternFill('solid', fgColor=shade[r['級']])
        ws.freeze_panes = 'C2'
        ws.auto_filter.ref = ws.dimensions
        wide = {'英文': 34, '用語集譯名': 22, '現在名稱': 34, '現在中文': 22,
                '其他譯名': 24, '檔案': 30, '形狀疑點': 16, '改為': 20}
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = wide.get(c, 9)
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    for title, rows in (('補名稱', fill), ('譯名差異', diff)):
        c = Counter(r['級'] for r in rows)
        print(f'{title}: {len(rows)} 條（A {c["A"]}、B {c["B"]}、C {c["C"]}）')
        byf = Counter(pack_of(r['檔案']) for r in rows)
        print('   ', '、'.join(f'{k} {n}' for k, n in byf.most_common()))
    print(OUT)


def apply():
    from openpyxl import load_workbook
    wb = load_workbook(OUT, read_only=True)
    todo = defaultdict(dict)
    for title in ('補名稱', '譯名差異'):
        rows = list(wb[title].iter_rows(values_only=True))
        if not rows:
            continue
        h = {c: i for i, c in enumerate(rows[0])}
        for r in rows[1:]:
            act = (r[h['裁定']] or '').strip()
            if act == '套':
                zh = r[h['用語集譯名']]
            elif act == '改':
                zh = (r[h['改為']] or '').strip()
                if not zh:
                    print('裁定「改」但「改為」空白，跳過：', r[h['英文']])
                    continue
            else:
                continue
            todo[r[h['檔案']]][r[h['英文']]] = zh
    n = 0
    for fname, items in sorted(todo.items()):
        p = TR / fname
        d = load_json(p)
        fmt = fmt_of(fname)
        for en, zh in items.items():
            e = d['entries'].get(en)
            if e is None:
                print('找不到鍵，跳過：', fname, en)
                continue
            e['name'] = fmt.format(zh=zh, en=en)
            if pack_of(fname) == 'pf1-bestiary':
                e['token_name'] = zh
            n += 1
        save_json(p, d)
        print(f'{fname}: {len(items)}')
    print(f'共改 {n} 條名稱。改完跑 git diff 看一眼')


if __name__ == '__main__':
    {'report': report, 'apply': apply}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: print(__doc__))()
