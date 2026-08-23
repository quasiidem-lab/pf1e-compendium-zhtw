/**
 * pf1e-compendium-zhtw — 向 Babele 註冊繁體中文合集包對照表。
 *
 * 註冊時機走 `babele.init` 鉤子。
 *
 * Babele 2.9 起，register/registerConverters 一旦過了 runtime session 建立
 * 就直接 throw（"must be called during the babele.init hook"）。而 Babele 是
 * 在它自己的 Hooks.once('init') 裡才 callAll('babele.init')，模組之間的載入
 * 順序沒有保證——掛 Foundry 的 init 是碰運氣，排在 Babele 後面就整個不註冊，
 * 合集包一個字都不會翻。掛 `babele.init` 兩種順序都對。
 *
 * 舊版 Babele（2.6.x）沒有這個鉤子，因此保留一段 init 後援；
 * 已經註冊過就不重複做。
 */
import converters from "./converters.js";
import { OriginalNameFilter } from "./filters.mjs";

const MODULE_ID = "pf1e-compendium-zhtw";

let registered = false;

function registerWith(babele) {
  if (registered || !babele) return;

  try {
    babele.registerConverters({
      actions: converters.actions,
      contextNotes: converters.contextNotes,
      containerItems: converters.containerItems,
      subSchool: converters.subSchool,
      learnedAt: converters.learnedAt,
      descriptors: converters.descriptors,
    });

    babele.register({
      module: MODULE_ID,
      lang: "zh-tw",
      dir: "translations",
    });

    registered = true;
  } catch (err) {
    console.error(`${MODULE_ID} | 向 Babele 註冊失敗`, err);
  }
}

// Babele 2.7+ 的正規時機
Hooks.once("babele.init", (babele) => registerWith(babele));

Hooks.once("init", () => {
  game.settings.register(MODULE_ID, "enableDebug", {
    name: "顯示翻譯錯誤通知",
    hint: "除了主控台訊息外，翻譯過程中的錯誤也會以通知顯示。",
    scope: "world",
    config: true,
    default: false,
    type: Boolean,
  });

  if (registered) return;

  // 後援：舊版 Babele 沒有 babele.init
  const babele =
    (typeof Babele !== "undefined" && Babele.get?.()) || game.babele;

  if (!babele) {
    console.error(`${MODULE_ID} | 找不到 Babele，合集包不會被翻譯`);
    return;
  }

  registerWith(babele);
});

// 合集包瀏覽器加一個「以英文原名搜尋」的篩選器。
// 原本這裡用了 OriginalNameFilter 卻沒有 import，載入後會丟 ReferenceError。
Hooks.once("ready", () => {
  if (game.settings.get("core", "language") !== "zh-tw") return;

  const browsers = [
    pf1.applications.compendiumBrowser.ClassBrowser,
    pf1.applications.compendiumBrowser.ItemBrowser,
    pf1.applications.compendiumBrowser.SpellBrowser,
    pf1.applications.compendiumBrowser.FeatBrowser,
    pf1.applications.compendiumBrowser.RaceBrowser,
    pf1.applications.compendiumBrowser.CreatureBrowser,
    pf1.applications.compendiumBrowser.BuffBrowser,
  ];

  for (const browser of browsers) {
    if (!browser?.filterClasses) continue;
    if (browser.filterClasses.includes(OriginalNameFilter)) continue;
    browser.filterClasses.splice(0, 0, OriginalNameFilter);
  }
});
