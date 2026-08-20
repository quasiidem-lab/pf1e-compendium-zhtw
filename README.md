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

## 覆蓋率

**上游譯稿本身就不完整**，本模組僅做繁化，未新增翻譯：

| 項目 | 名稱已譯 |
|---|---:|
| 護甲與盾牌 | 100% |
| 法術 | 98% |
| 專長（pf1.feats） | 81% |
| 種族 | 78% |
| 武器彈藥 | 75% |
| 職業能力 | 63% |
| 物品 | 49% |
| **怪物圖鑑** | **18～32%** |

未譯的部分會顯示英文原文。

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

簡體中文使用者請直接使用上游的
[pf1e_compendium_chn](https://github.com/fvtt-cn/pf1e_compendium_chn)。

## 相對上游的修正

修正了 `pf-content.pf-tables.json` 的 JSON 語法錯誤（多餘逗號）——該檔在上游
無法解析，Babele 載入時會失敗。

## 授權

GPL v3。來源與 OGL 說明見 [`NOTICE.md`](NOTICE.md)。

## 作者

果園瑪莉卡
