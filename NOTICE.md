# 授權與來源聲明

本模組（`pf1e-compendium-zhtw`）為 Pathfinder 1e 系統的合集包內容提供繁體中文
（臺灣）翻譯，需搭配 Babele 使用。

本模組整體以 **GNU General Public License v3.0** 授權發布（見 `LICENSE`）。

## 來源

譯文與程式碼衍生自
[fvtt-cn/pf1e_compendium_chn](https://github.com/fvtt-cn/pf1e_compendium_chn)。

`translations/` 底下的 29 個 JSON 由該專案的簡體譯稿經 OpenCC（`s2tw`）字形轉換
與臺灣用語校正而成，共 31,451 條字串。`scripts/` 底下的程式碼取自該專案，僅修改
語系識別（`cn` → `zh-tw`）與模組 ID。

## 相對上游的修正

- **修正 `pf-content.pf-tables.json` 的 JSON 語法錯誤**（物件結尾多餘逗號）。
  該檔在上游無法被 `JSON.parse` 解析，Babele 因而載入失敗。
- 將 `scripts/babele.js` 中寫死的 `lang: "cn"` 與
  `game.settings.get("core","language") !== "cn"` 改為 `zh-tw`。
- 修正 `scripts/utils.js` 中殘留的舊模組 ID。

## OGL

本模組翻譯的內容包含 Pathfinder 1e 的遊戲資料（法術、專長、物品、怪物等），
其原文受 Open Game License 涵蓋。使用時請一併遵守 PF1 系統與各內容模組所載之
OGL 條款。

## 覆蓋率

上游譯稿本身即非完整翻譯。以條目名稱計，整體約 64% 已譯，其中：

- 法術 98%、護甲盾牌 100%、專長（pf1.feats）81%
- 怪物圖鑑僅 18～32%，且多數只譯名稱、無描述

本模組未新增翻譯，僅做字形與用語轉換，故覆蓋率與上游相同。

## 作者

果園瑪莉卡
