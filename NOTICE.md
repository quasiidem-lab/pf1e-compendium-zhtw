# 授權與來源聲明

本模組（`pf1e-compendium-zhtw`）為 Pathfinder 1e 系統的合集包內容提供繁體中文
（臺灣）翻譯，需搭配 Babele 使用。

## 授權範圍（分兩部分，不是整包一個授權）

| 部分 | 授權 |
|---|---|
| `scripts/` 的程式碼 | **GPL-3.0**（見 `LICENSE`），本專案自行撰寫 |
| `translations/` 的譯文 | **權利歸原作者**，見下方「譯文的授權狀況」 |

早期版本把整包宣告為 GPL-3.0，那是不正確的——譯文不是本專案的原創表達，
無權代為重新授權。此處更正。

## 譯文的授權狀況 ⚠

`translations/` 的譯文由
[fvtt-cn/pf1e_compendium_chn](https://github.com/fvtt-cn/pf1e_compendium_chn)
（FVTT-CN）的簡體譯稿經 OpenCC（`s2tw`）字形轉換與臺灣用語校正而成。

**該上游專案沒有 LICENSE 檔，也沒有任何授權聲明**（2026-08-23 查核：repo 根目錄
與模組內皆無）。依著作權法，未聲明即為保留所有權利。

需要釐清的一點：PF1 系統本身確實附有 OGL 1.0a 與 GPL-3.0，OGL §1(b)、§1(g) 也
明確把 translation 算進 Derivative Material 與 Use——但 OGL 授權的是「**依原文
自行翻譯**」，不是「拿他人已完成的譯稿改作」。簡體譯文是 FVTT-CN 的原創表達，
其著作權獨立於 OGL 之外。

因此本模組**尚未取得譯文的散布授權**。已就此聯繫上游，在取得同意前，
散布行為的風險由使用者自行承擔。若上游明確拒絕，替代路徑是依 OGL
從英文原文重新翻譯。

## 程式碼相對上游的差異

`scripts/` 已全部改為自行實作，不再沿用上游程式碼：

- `converters.js` 自行撰寫六個 Babele 轉換器
  （`actions`／`contextNotes`／`containerItems`／`subSchool`／`learnedAt`／`descriptors`），
  其中領域、職業、子學派的對照表輸出正體中文（上游輸出簡體）。
- `babele.js` 改於 `babele.init` 鉤子註冊。Babele 2.9 起，`register()` 與
  `registerConverters()` 一旦過了 runtime session 建立即拋錯；而 Babele 於自身的
  `Hooks.once('init')` 才發出 `babele.init`，模組載入順序無保證，掛 Foundry 的
  `init` 並不可靠。保留 `init` 後援以相容 Babele 2.6.x。
- 修正 `babele.js` 使用 `OriginalNameFilter` 卻未 import 所導致的 `ReferenceError`。
- 移除上游帶有 `require()` 的 Node 建置腳本（`files.js`／`merge.js`／
  `orderEntries.js`／`utils.js`）——Foundry 無法載入，屬打包冗餘。

## 譯文相對上游的修正

- **修正 `pf-content.pf-tables.json` 的 JSON 語法錯誤**（物件結尾多餘逗號）。
  該檔在上游無法被 `JSON.parse` 解析，Babele 因而載入失敗。
- 語系識別由 `cn` 改為 `zh-tw`。

## OGL

本模組翻譯的內容包含 Pathfinder 1e 的遊戲資料（法術、專長、物品、怪物等），
其原文受 Open Game License 1.0a 涵蓋。依 OGL §10，本模組隨附授權全文，
見 `OGL.txt`。使用時請一併遵守 PF1 系統與各內容模組所載之 OGL 條款。

## 覆蓋率

上游譯稿本身即非完整翻譯。以條目名稱計，整體約 64% 已譯，其中：

- 法術 98%、護甲盾牌 100%、專長（pf1.feats）81%
- 怪物圖鑑僅 18～32%，且多數只譯名稱、無描述

本模組未新增翻譯，僅做字形與用語轉換，故覆蓋率與上游相同。

## 作者

果園瑪莉卡
