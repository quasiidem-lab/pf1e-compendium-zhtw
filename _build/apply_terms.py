# -*- coding: utf-8 -*-
r"""把譯名定案套到 translations/（繁）與旁邊的 pf1e-compendium-zhcn/translations/（簡）。

    python _build/apply_terms.py          # 套用並寫回
    python _build/apply_terms.py --dry    # 只算、印統計，不寫

**每次跑完 build_chm.py 之後都要再跑這支。** CHM 層會把名稱與內文整條換成 CHM 的寫法，
而有些譯名是維護者另外裁定、跟 CHM 不同的（例：Terrifying Howl 定為「驚駭狂嚎」，CHM 寫「怖懼狂嚎」），
不在建置的最後補一次就會被蓋回去。

定案來源：pf1-zhtw 的 audit/譯名一致性稽核（2026-10-17 維護者裁定＋依 CHM v2.33.0 的建議）。

三種改法：
  NAME   指定條目的名稱改成定案譯名（只動名稱的中文部分，英文與職業標記保留）
  TERM   內文裡的舊譯名換成定案譯名（繁簡都套，簡體版自動轉字形）
  WORDS  對岸用語換成台灣用語（只套繁體版）

全部是可重複執行的：已經是定案寫法的不會再動。
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
TR = HERE.parent / 'translations'
TR_CN = HERE.parent.parent / 'pf1e-compendium-zhcn' / 'translations'

# 內容完全相同的成對檔：改一份就要改兩份
TWINS = {'pf1.pf1e-rules.json': 'pf1.rules.json', 'pf1.racial-hd.json': 'pf1.racialhd.json'}

# ---------------------------------------------------------------
# NAME：檔案 → {條目鍵: 定案譯名}；規則頁（pages）的鍵寫成「條目/頁」
# ---------------------------------------------------------------
NAME = {
    'pf-content.pf-feats.json': {
        'Armor Focus': '護甲專攻',
        'Improved Armor Focus': '精通護甲專攻',
        'Martial Focus': '武術專精',
    },
    'pf1.pf1e-rules.json': {
        'Conditions/Prone': '俯臥',
        'Conditions/Energy Drained': '能量吸取',   # 2026-10-20 維護者改定（跟 CHM、怪物能力 Energy Drain 同詞）
    },
    'pf1.races.json': {'Ratfolk': '鼠族'},
    'pf1.racial-hd.json': {'Ooze': '泥怪'},
    'pf1.class-abilities.json': {
        'Bardic Knowledge (SKA)': '逸聞知識',
        'Dazing Touch (CLE)': '暈眩之觸',
        'Dazing Touch (WIZ)': '暈眩之觸',
        'Poison Resistance (INV)': '毒性抗力',
        'Knockback (UC)': '擊飛',
        'Eater of Magic (UC)': '吞噬魔法',
        'Increased Damage Reduction (UC)': '增強傷害減免',
        'Low-Light Vision (UC)': '昏暗視覺',
        'Elemental Body (BLO)': '元素形態',
        'Elemental Body': '元素形態',
        'Order of the Beast': '狂獸騎士團',
        'Animal Fury (UC)': '野性之怒',
        'Bleeding Blow (UC)': '流血猛擊',
        'Aberrant Form (BLO)': '異怪形態',
        'Terrifying Howl (UC)': '驚駭狂嚎',
        'Terrifying Howl': '驚駭狂嚎',
        'Auspicious Mark (UC)': '吉祥烙記',
        'Breath Weapon': '噴吐武器',
        'Resiliency': '韌性',
        'Abundant Step (UC)': '遁術',
        'Sprint (UC)': '奮力衝刺',
        'Witch Hunter (UC)': '獵巫人',
        'Intimidating Glare (UC)': '威嚇凝視',
        'Acid Dart (WIZ)': '酸蝕鏢',
        'Acid Dart (CLE)': '酸蝕鏢',
        'Unarmed Strike (BRA)': '徒手打擊',
        'Clear Mind (UC)': '心如堅鋼',
        'Feat (NIN)': '專長',
        'Evasion (NIN)': '反射閃避',
        'Rogue Talent': '盜賊天賦',
        'Rogue Talent (INV)': '盜賊天賦',
        'Smoke Bomb (NIN)': '煙霧彈',
        'Smoke Bomb': '煙霧彈',
        'Quick Reflexes (UC)': '超速反射',
        'Unexpected Strike (UC)': '詭擊',
        'Brain Drain (SHA)': '意識鑽刺',
        'Maneuver Mastery (MAG)': '戰技熟稔',
        'Skill Mastery (UC)': '技能專精',
        'Lasting Poison (UC)': '毒性持續',
        'Ground Breaker (UC)': '大地之擊',
        'Sharpened Accuracy (UC)': '敏銳精確',
        'Fearless Rage (UC)': '無懼狂暴',
        'Nimble Climber (UC)': '飛簷走壁',
        'Minor Magic (UC)': '次級魔法',
        'Major Magic (UC)': '高級魔法',
        'Deadly Accuracy (UC)': '致命精確',
        'Lethal Accuracy (UC)': '致死精確',
        'Ki Pool': '氣池',
        'Spontaneous Casting (CLE)': '自發施法',
        'Roused Anger (UC)': '無邊怒火',
        'Inspire Ferocity (UC)': '激發凶性',
        'Inspire Ferocity': '激發凶性',
        'Raging Swimmer (UC)': '狂暴遊者',
        'Raging Leaper (UC)': '狂暴跳躍',
        'Sudden Speed (UC)': '瞬時加速',
        'Flesh Wound (UC)': '不屈武勇',
        'Superstition (UC)': '迷信',
        'Aura of Despair': '絕望靈氳',
        'Aura of Despair (APA)': '絕望靈氳',
        'Channel': '引導能量',
        'Crippling Blow (UC)': '致殘猛擊',
        'High Jump (UC)': '輕功',
        'Swift Foot (UC)': '迅足',
        'Smasher (UC)': '破壞者',
        'Guarded Stance (UC)': '守衛姿態',
        'Bonus Feats (SWA)': '獎勵專長',
        'Improved Quarry (VAM)': '精通狩獵目標',
    },
}

# ---------------------------------------------------------------
# TERM：內文裡的舊譯名 → 定案譯名（regex, 替換）。繁簡都套。
# 只收「這個字串只可能是這個術語」的；一般用字（倒地、翅膀）不收。
# ---------------------------------------------------------------
TERM = [
    (r'絆摔', '摔絆'),                       # Trip（CHM v2.28.5 全書統一）
    (r'快速醫療|快速痊癒', '快速治療'),        # Fast Healing
    (r'特技動作', '特技'),                   # Acrobatics
    (r'傷勢穩定', '穩定'),                   # Stable
    (r'(?<!擊)破武', '擊破'),                # Sunder；「擊破武器」本來就對，不動
    (r'徒手擊打', '徒手打擊'),               # Unarmed Strike
    (r'因無武裝受到', '因徒手打擊受到'),       # 指徒手攻擊的「無武裝」；「無武裝生物」指沒拿武器的生物，不改
    (r'恍惚接觸|眩目之觸', '暈眩之觸'),        # Dazing Touch
    (r'電瞬步', '瞬時加速'),                 # Sudden Speed
    (r'化身異怪', '異怪形態'),               # Aberrant Form
    (r'毒素抗力', '毒性抗力'),               # Poison Resistance
    (r'強酸鏢', '酸蝕鏢'),                   # Acid Dart
    (r'(?<![蝕強])酸鏢', '酸蝕鏢'),
    (r'戰技精通', '戰技熟稔'),               # Maneuver Mastery
    (r'怖懼狂嚎|可怖狂嚎', '驚駭狂嚎'),        # Terrifying Howl
    (r'高等狩獵目標', '精通狩獵目標'),         # Improved Quarry
    (r'狂怒激發|狂怒之示', '激發凶性'),        # Inspire Ferocity
    # Acid 只改傷害類型、能量類型、抗力；強酸箭、強酸噴吐、強酸瓶這類名稱不動
    (r'強酸(?=傷害|抗力|能量)', '酸蝕'),
    (r'(?<=[（(、，或和及])強酸(?=[、或和及）)])', '酸蝕'),
]

# ---------------------------------------------------------------
# WORDS：對岸用語 → 台灣用語。只套繁體版。
# 合集包裡的「界面」是「第一世界面容」誤抓、「兼容並蓄」是專長名、「遺傳代碼」不是程式碼，都不收。
# ---------------------------------------------------------------
WORDS = [
    (r'文本', '內文'),                       # 法術欄位「見文本」
    (r'信息', '訊息'),
    (r'激活', '啟動'),
    (r'添加到', '加到'),
    (r'添加上', '加上'),
    (r'复', '復'),
    (r'钟', '鐘'),
    (r'數據', '資料'),
    (r'鏈接', '連結'),
    (r'(?<!沒有)(?<!絕對)質量', '品質'),     # 「沒有質量」「絕對質量」是物理的質量
    (r'(?<!可)變量', '變數'),                # 「可變量值」不動
    (r'創建', '建立'),
    (r'默認', '預設'),
    (r'刷新', '重置'),
    (r'圖標', '圖示'),
]

# 不能動的片段：HTML 標籤、網址、@UUID[...] 的識別碼
PROTECT = re.compile(r'<[^>]+>|https?://[^\s"<>]+|@\w+\[[^\]]*\]')


def make_rules(pairs, cn):
    if not cn:
        return [(re.compile(p), r) for p, r in pairs]
    import opencc
    t = opencc.OpenCC('tw2s')
    return [(re.compile(t.convert(p)), t.convert(r)) for p, r in pairs]


def sub_text(s, rules, stat):
    if not isinstance(s, str) or not s:
        return s
    out, last = [], 0
    for m in PROTECT.finditer(s):
        out.append(_sub(s[last:m.start()], rules, stat))
        out.append(m.group(0))
        last = m.end()
    out.append(_sub(s[last:], rules, stat))
    return ''.join(out)


def _sub(seg, rules, stat):
    for rx, rep in rules:
        seg, n = rx.subn(rep, seg)
        if n:
            stat[rx.pattern] += n
    return seg


def walk(node, rules, stat):
    if isinstance(node, dict):
        return {k: walk(v, rules, stat) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, rules, stat) for v in node]
    return sub_text(node, rules, stat)


CJK = re.compile(r'[㐀-鿿]')


def zh_base(name, key):
    """名稱的中文本體：去掉附的英文、職業標記。"""
    n = name.strip()
    m = re.search(r'\s*[（(]\s*' + re.escape(key) + r'\s*[)）]?$', n) or re.search(r'\s+' + re.escape(key) + r'$', n)
    if m:
        n = n[:m.start()].strip()
    else:
        m = re.search(r'\s*[（(]([^（()）]*)[)）]$', n)
        if m and not CJK.search(m.group(1)):
            n = n[:m.start()].strip()
    if re.search(r'\s\([A-Z]{2,4}\)$', key):
        n = re.sub(r'\s*[（(][^（()）]*[)）]$', '', n)
    return n.replace(' · ', '·')


def fix_name(entry, key, new, conv, stat):
    """把 entry['name'] 的中文本體換成 new（繁或簡）。回傳是否有改。"""
    name = entry.get('name')
    if not isinstance(name, str):
        return False
    en = key.split('/')[-1]
    base = zh_base(name, en)
    target = conv(new)
    if not CJK.search(base) or base == target:
        return False
    raw = base if base in name else base.replace('·', ' · ')
    if raw not in name:
        stat['名稱對不上（略過）'] += 1
        return False
    entry['name'] = name.replace(raw, target, 1)
    return True


def dump(path, data, ref_text):
    for ind in (2, 1):
        if json.dumps(json.loads(ref_text), ensure_ascii=False, indent=ind) + '\n' == ref_text:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=ind) + '\n', encoding='utf-8')
            return
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(folder, cn, dry):
    if not folder.exists():
        print(f'（找不到 {folder}，略過）')
        return
    conv = (lambda s: s)
    if cn:
        import opencc
        _t = opencc.OpenCC('tw2s')
        conv = _t.convert
    rules = make_rules(TERM, cn) + ([] if cn else make_rules(WORDS, False))
    names = dict(NAME)
    for a, b in TWINS.items():
        if a in names:
            names[b] = names[a]
    stat, renamed, touched = Counter(), 0, 0
    for path in sorted(folder.glob('*.json')):
        ref = path.read_text(encoding='utf-8')
        data = json.loads(ref)
        ents = data.get('entries')
        for key, new in names.get(path.name, {}).items():
            if '/' in key:
                k, pg = key.split('/', 1)
                e = (ents.get(k) or {}).get('pages', {}).get(pg)
            else:
                e = ents.get(key) if isinstance(ents, dict) else None
            if e is None:
                stat['條目不存在（略過）'] += 1
                continue
            renamed += fix_name(e, key, new, conv, stat)
        new_data = walk(data, rules, stat)
        if new_data != json.loads(ref):
            touched += 1
            if not dry:
                dump(path, new_data, ref)
    print(f'[{"簡" if cn else "繁"}] {folder}')
    print(f'  名稱改了 {renamed} 條，動到 {touched} 個檔')
    for p, n in stat.most_common():
        print(f'  {n:>5}  {p}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    run(TR, False, a.dry)
    run(TR_CN, True, a.dry)
