# 建置管線

譯文分兩層，**CHM 優先**（2026-10-10 定）：

1. **底稿** `base/`：上游 `pf1e_compendium_chn` 繁化＋人工修訂的譯文（就是套 CHM 之前的 `translations/`）
2. **CHM 層**：`build_chm.py` 從果園 CHM 抽條目，有的就整條（名稱＋內文）換掉

```powershell
python _build/build_chm.py          # base/ ＋ CHM → translations/（繁）；上游簡體稿＋CHM → ../pf1e-compendium-zhcn/translations/（簡）
python _build/make_zhcn.py          # 繁中版 scripts/、styles/ → 簡體模組（改了程式碼才要跑）
python _build/verify_compendium.py  # 驗證
```

簡體模組 `pf1e-compendium-zhcn` 是另一個 repo（quasiidem-lab/pf1e-compendium-zhcn），但沒有自己的建置流程，
程式碼與譯文都從這裡產生；它自己只手寫 `module.json`、`README.md`、`NOTICE.md`（FVTT-CN 署名在那裡，不要刪）。

CHM 週五發版後重跑 `build_chm.py` 就會跟著更新。定位靠 CHM 線插的條目錨點，
CHM 線每多做一類錨點，在 `build_chm.py` 的 `KINDS` 加一列就多吃一類；用法與壞掉的症狀寫在它開頭。
每條內文結尾附出處行（譯者、書目、CHM 果園原帖、AoN），是公開發布的條件，不要拿掉。

**要改底稿（上游繁化、用語集補名稱 `glossary_names.py`）就改 `base/`，再重跑 `build_chm.py`。**
直接改 `translations/` 的東西下次建置會被蓋掉。

以下是底稿層的舊管線：從上游的簡體對照表重新產生底稿。
只有上游更新時才需要跑；平常維護模組本身用不到。

```powershell
_build\build.bat        # 建置 + 驗證，驗證沒過回傳非零
```

在含中文的路徑下要用絕對路徑呼叫 `build.bat`，相對路徑 cmd 會找不到檔案。

## ⚠ 不要用 build.bat 重建 translations/

**現行的譯文不是純管線產出，重建會讓譯文倒退。**

裡面有大量人工修訂的台灣用詞，上游並非如此：

| 現行（人工修訂） | 上游原詞 | 數量 |
|---|---|---|
| 訊息 | 消息／信息 | 508 |
| 目前 | 當前 | 229 |
| 儲存 | 保存 | 99 |
| 範本 | 模板 | 74 |
| 搜尋 | 搜索 | 49 |
| 設定陷阱 | 設置陷阱 | 6 |

共約 455 條。`build.bat` 會忠實照上游轉換，把這些全部蓋回大陸用詞。

另外介面層的 `TERM_MAP` 有一條在合集語料裡會**切到詞中間**：
`可選->選用` 碰上「你可以多次選擇本專長」會變成「僅選用擇一次」（39 處）。
替換表是純字串 replace，不看詞界。

所以 `build_compendium.py` 只在**上游重大更新、需要從頭重建**時才用，
而且用了之後得把人工修訂重新套回去。日常修正請用下一節的工具。

## 修殘留的簡體：fix_residual.py

已發布的 v0.1.1 裡有 1,529 條未轉換的簡體（集中在「戰策增益」那一段，
像 `战策增益`、`消耗2点耐力`）：

```
python _build/fix_residual.py
```

這支只做一件事：對「確實是簡體字」的字元做字形轉換，
**不套任何用語替換表**，所以人工修訂一字不動。

切分順序是「先切標籤、再切網址」，反過來的話
`<a href="...中文...">` 的屬性值會被當成一般文字轉換
（來源的 Demand 法術就有這種破損網址），驗證會判定 HTML 標籤遭竄改。

## 術語表的正本

`TERM_MAP` 與 `PROTECTED` 從介面層 import，不在這裡複製一份：

```
D:\TRPG\4_工具與筆記\pf1-zhtw\_build\build_zhtw.py
```

改譯名只改那一份，兩層才會一致。合集層另有 `EXTRA_TERMS`／`EXTRA_PROTECTED`
放規則書內文才出現的詞，寫在 `build_compendium.py` 開頭。

## 驗證項目

`verify_compendium.py` 檢查七項，任一不過回傳非零：

1. 檔案集合一致（30 檔）
2. `entries` 鍵集合一致（Babele 靠英文鍵比對）
3. `mapping` 完全未變（欄位路徑被轉換 Babele 會壞）
4. 結構一致
5. HTML 標籤完好
6. `@` 連結的文件 ID 完好
7. 無殘留簡體（OpenCC 反向轉換偵測）

改 mapping 值、刪 entries 鍵、注入簡體、改連結 ID 這四種破壞都實測會被抓到。

## 轉換時的三個坑

**一、`{...}` 在介面層與合集層意義相反。** 介面層的大括號是 Foundry 插值變數
要保護；合集層的大括號幾乎都是中文——3,119 個 `@Compendium[...]{中文名}`
顯示標籤，加上 180 個 `{2+智力修正}` 算式。沿用介面層的 `PLACEHOLDER`
會把這 3,299 處全留在簡體。真正不可動的只有方括號裡的文件 ID。

**二、`<[^>]+>` 抓標籤太貪心。** 來源有 21 處長得像標籤但不是：
`<水晶球 (crystal ball)>` 這種拿角括號當引號的物品名（18 處），
和 `<p被壓制的生物…` 漏打 `>` 的破損標籤（3 處）。
寬鬆比對會把後面的中文一起當標籤保護。改成限定 `</?標籤名 …>` 的形狀。

**三、反向偵測殘簡會誤報。** OpenCC 一對多映射會想把已經正確的繁體再改一次：
斗轉星移→鬥、無厘頭→釐、風采→採、趨吉避凶→兇。驗證改成逐字比對並跳過
`AMBIGUOUS` 那組，另外排除網址與標籤內部的文字（`#TOC-黑暗视觉` 是
d20pfsrd 錨點，轉了連結失效）。

## 上游的既有破損

- `pf-content.pf-tables.json` 有尾逗號，strict JSON 解析不過（Foundry 容忍）。
  建置時自動修掉，來源不動
- `Demand` 法術的 `href` 網址裡被誤貼中文，那段連結上游就是壞的
