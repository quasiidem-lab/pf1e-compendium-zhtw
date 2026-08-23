/**
 * Babele 轉換器（正體中文）。
 *
 * 對照表的 mapping 區會指名 converter，Babele 找不到就整個欄位不翻。
 * pf1.spells / pf1.items / pf1.buffs / pf1.class-abilities 共用到五個：
 *   actions, contextNotes, containerItems, subSchool, learnedAt, descriptors
 *
 * 這裡是自行實作，不沿用來源模組的 scripts/（那份是上游的程式碼，
 * 授權未明；見 README「授權現況」）。行為以「對得上 mapping 的欄位形狀」為準。
 */

/** 把翻譯後的 actions 併回原始 action 陣列。 */
export function actions(value, translations) {
  if (!translations || !Array.isArray(value)) return value;

  value.forEach((action, index) => {
    const data = translations[index];
    if (!data) return;

    if (data.name) action.name = data.name;
    if (action.range?.value && data.range) action.range.value = data.range;
    if (action.save?.description && data.savingThrow) {
      action.save.description = data.savingThrow;
    }
    if (action.duration?.value && data.duration) {
      action.duration.value = data.duration;
    }
    if (action.target?.value && data.target) {
      action.target.value = data.target;
    }
    if (data.spellArea) action.spellArea = data.spellArea;
    if (data.spellEffect) action.spellEffect = data.spellEffect;
    if (data.effectNotes?.length) action.effectNotes = data.effectNotes;
  });

  return value;
}

/** 情境註記：逐項換掉 text，數量對不上就整組不動（寧可留英文也不要錯位）。 */
export function contextNotes(original, translated) {
  if (!Array.isArray(original) || !Array.isArray(translated)) return original;

  const withText = original.filter((n) =>
    Object.prototype.hasOwnProperty.call(n, 'text')
  );
  if (translated.length !== withText.length) {
    console.warn(
      `pf1e-compendium-zhtw | 情境註記數量不符 ${translated.length}/${withText.length}，該項不翻`
    );
    return original;
  }

  original.forEach((note, i) => {
    if (translated[i]?.text) note.text = translated[i].text;
  });
  return original;
}

/** 容器內的物品：沿用合集包裡已翻好的同一件物品。 */
export function containerItems(items) {
  if (!items) return items;

  Object.values(items).forEach((item) => {
    const uuid = item.flags?.core?.sourceId;
    if (!uuid) return;

    const source = fromUuidSync(uuid);
    if (!source?.flags?.babele?.translated) return;

    item.name = source.name;
    if (source.system?.description?.value) {
      item.system.description.value = source.system.description.value;
    }
  });
  return items;
}

const SUB_SCHOOL = new Map([
  ['calling', '呼喚'],
  ['charm', '魅惑'],
  ['compulsion', '脅迫'],
  ['creation', '創造'],
  ['figment', '虛假幻覺'],
  ['glamer', '五官幻覺'],
  ['haunted', '作祟'],
  ['healing', '醫療'],
  ['pattern', '心靈幻覺'],
  ['phantasm', '魅影幻覺'],
  ['polymorph', '變形'],
  ['scrying', '探知'],
  ['shadow', '幽影幻覺'],
  ['summoning', '召喚'],
  ['teleportation', '傳送'],
]);

export function subSchool(value) {
  if (!value || typeof value !== 'string') return value;
  let out = value;
  SUB_SCHOOL.forEach((zh, en) => {
    out = out.replace(en, zh);
  });
  return out;
}

/**
 * 法術可用職業／領域／血脈的鍵名。
 * 這些鍵是顯示在法術資訊面板上的字串，不是系統識別字，翻了不影響查找。
 */
const DOMAIN = new Map([
  ['Air', '氣領域'], ['Animal', '動物領域'], ['Artifice', '手藝領域'],
  ['Chaos', '混亂領域'], ['Charm', '魅惑領域'], ['Community', '團隊領域'],
  ['Darkness', '黑暗領域'], ['Death', '死亡領域'], ['Destruction', '毀滅領域'],
  ['Earth', '土領域'], ['Evil', '邪惡領域'], ['Fire', '火領域'],
  ['Glory', '榮耀領域'], ['Good', '善良領域'], ['Healing', '醫療領域'],
  ['Knowledge', '知識領域'], ['Law', '秩序領域'], ['Liberation', '解放領域'],
  ['Luck', '機運領域'], ['Madness', '狂亂領域'], ['Magic', '魔法領域'],
  ['Nobility', '高貴領域'], ['Plant', '植物領域'], ['Protection', '保護領域'],
  ['Repose', '安眠領域'], ['Rune', '符文領域'], ['Scalykind', '鱗類領域'],
  ['Strength', '力量領域'], ['Sun', '太陽領域'], ['Travel', '旅行領域'],
  ['Trickery', '詭術領域'], ['Void', '虛空領域'], ['War', '戰爭領域'],
  ['Water', '水領域'], ['Weather', '天氣領域'],
]);

const CLASS = new Map([
  ['adept', '導師'], ['alchemist', '煉金術士'], ['antipaladin', '反聖騎士'],
  ['arcanist', '奧能師'], ['barbarian', '野蠻人'], ['bard', '吟遊詩人'],
  ['bloodrager', '血脈狂怒者'], ['brawler', '拳師'], ['cavalier', '騎將'],
  ['cleric', '牧師'], ['druid', '德魯伊'], ['hunter', '獵人'],
  ['inquisitor', '審判者'], ['investigator', '調查員'], ['kineticist', '操念使'],
  ['magus', '魔戰士'], ['medium', '通靈者'], ['mesmerist', '催眠師'],
  ['monk', '武僧'], ['ninja', '忍者'], ['oracle', '先知'],
  ['occultist', '祕學士'], ['paladin', '聖騎士'], ['psychic', '異能者'],
  ['ranger', '遊俠'], ['rogue', '遊蕩者'], ['samurai', '武士'],
  ['shaman', '薩滿'], ['skald', '歌者'], ['slayer', '殺手'],
  ['sorcerer', '術士'], ['spiritualist', '喚魂師'], ['summoner', '召喚師'],
  ['summonerUnchained', '掉鏈召喚師'], ['swashbuckler', '遊蕩劍客'],
  ['vigilante', '俠客'], ['warpriest', '戰鬥祭司'], ['witch', '女巫'],
  ['wizard', '法師'],
]);

/** 就地把物件的鍵換成中文（值不動）。 */
function renameKeys(obj, map) {
  if (!obj) return;
  map.forEach((zh, en) => {
    if (Object.prototype.hasOwnProperty.call(obj, en)) {
      obj[zh] = obj[en];
      delete obj[en];
    }
  });
}

export function learnedAt(value) {
  if (!value) return value;
  renameKeys(value.domain, DOMAIN);
  renameKeys(value.class, CLASS);
  return value;
}

/** 描述符：目前不轉換，保留原值（上游同樣停用）。 */
export function descriptors(value) {
  return value;
}

export default {
  actions,
  contextNotes,
  containerItems,
  subSchool,
  learnedAt,
  descriptors,
};
