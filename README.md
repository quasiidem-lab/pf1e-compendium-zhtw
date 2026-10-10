# PF1e 合集包 繁體中文

Pathfinder 1e 系統合集包內容（法術、專長、物品、怪物等）的繁體中文（臺灣）翻譯。

**需要 [Babele](https://gitlab.com/riccisi/foundryvtt-babele)。**

## 內容

31,451 條字串，涵蓋 29 個翻譯檔：

| 檔案 | 內容 |
|---|---|
| `pf1.spells.json` | 3,029 個法術（98% 已譯） |
| `pf-content.pf-feats.json` | 3,328 個專長 |
| `pf1.class-abilities.json` | 4,352 個職業能力 |
| `pf1.items.json` | 物品 |
| `pf1-bestiary.*.json` | 怪物圖鑑 ×8 |
| 其餘 | 種族、武器、護甲、規則等 |

## 譯文來源

1. **果園 PF1 CHM 大全集**（v0.2.0 起，優先）：CHM 收錄的條目，名稱與內文直接採用 CHM 繁體版。
   每條結尾附出處行：譯者、書目、果園原帖、AoN。目前涵蓋專長與法術。
2. **上游譯稿**：CHM 沒有的條目，沿用 [fvtt-cn/pf1e_compendium_chn](https://github.com/fvtt-cn/pf1e_compendium_chn) 簡體譯稿的繁化版。

詳見 [`NOTICE.md`](NOTICE.md)。

## 覆蓋率

上游譯稿本身就不完整。名稱已譯的條目數，2026-10-11 在 Foundry 13.351＋PF1 11.11 實測（專長、法術已含 CHM 補譯）：

| 合集包 | 名稱已譯 |
|---|---:|
| 法術 | 2,985／3,029 |
| 護甲與盾牌 | 62／66 |
| 種族 | 59／80 |
| 武器彈藥 | 346／474 |
| 附加專長（pf-content） | 2,366／3,251 |
| 專長（pf1.feats） | 246／313 |
| 職業能力 | 2,565／4,651 |
| 物品 | 274／1,031 |

未譯的部分會顯示英文原文。怪物圖鑑的八個對照檔（`pf1-bestiary.*`）對應的是舊版合集包，PF1 11 沒有這些合集包，所以目前不會顯示。

## 安裝

```
https://github.com/quasiidem-lab/pf1e-compendium-zhtw/releases/latest/download/module.json
```

安裝後啟用本模組與 Babele，介面語言設為繁體中文（`zh-tw`）。

## 搭配

- **PF1 系統介面** → [`pf1-zhtw`](https://github.com/quasiidem-lab/pf1-zhtw)
- **模組介面** → [`pf1-mods-zhtw`](https://github.com/quasiidem-lab/pf1-mods-zhtw)
- **Foundry 核心** → [`foundry-core-zh-tw`](https://gitlab.com/fvtt-zh_TW/foundry-core-zh-tw)

## 簡體中文版

[`pf1e-compendium-zhcn`](https://github.com/quasiidem-lab/pf1e-compendium-zhcn)：同一套建置流程產生的簡體版（FVTT-CN 譯稿為底，CHM 條目改用 CHM 簡體版）。
上游的 [pf1e_compendium_chn](https://github.com/fvtt-cn/pf1e_compendium_chn) 在 Babele 2.9 下無法載入。

## 相對上游的修正

修正了 `pf-content.pf-tables.json` 的 JSON 語法錯誤（多餘逗號）——該檔在上游
無法解析，Babele 載入時會失敗。

## 授權

程式碼（`scripts/`）為 GPL-3.0；譯文權利歸原譯者（果園 CHM 各譯者、FVTT-CN），不在 GPL 範圍內。
來源、出處與 OGL 說明見 [`NOTICE.md`](NOTICE.md)。

## 作者

果園瑪莉卡
