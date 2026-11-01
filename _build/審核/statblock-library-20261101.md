# Statblock Library 怪物名稱對照（2026-11-01）

Foundry 裡大部分的怪物在 Statblock Library（SBL）這個模組，這次替它補中文名稱。做法跟基本怪物、怪物模板那兩次一樣：只翻名稱，不翻內文，譯名不自己翻。

- 新檔：`translations/statblock-library.*.json`，**34 個**（理由見下一節）
- 簡體版：`_build/審核/zhcn/` 同名 34 檔（要手動複製到 pf1e-compendium-zhcn 的 `translations/`）
- **譯名表：`_build/statblock-library譯名.tsv`**（Excel 打得開）。一列一個英文名，譯名、來源、各來源的寫法、沒收的理由都在裡面
- 條目清單：`_build/statblock-library條目.tsv`（從 SBL 原始碼抓的 10,387 條，產生對照檔時用）
- 產生程式：`_build/statblock_library.py`。改了譯名表就重跑它
- 分支：`statblock-library-map`，沒合進 main、沒升版號、沒發 release

## 先講一件跟交代不一樣的事

**SBL 不是 PF1 系統內建的合集包。** PF1 11.11 的原始碼（pf1-data）裡沒有 statblock-library 這包；它是 PF1 社群另外發的模組：

- 模組代號 `statblock-library`，標題「Pathfinder 1e Statblock Library (SBL)」，這次對的是 0.8.0（2026-03 發布）
- 原始碼：gitlab.com/foundryvtt_pathfinder1e/pf1-statblock-library
- **48 個合集包**（怪物圖鑑 1–3、4–6、Tome of Horrors、NPC 圖鑑、PFS、22 套冒險之路……），共 **10,387 條**
- 每條不是怪物角色卡，而是一則**日誌**（JournalEntry），裡面一頁數據方塊文字（給 SBC 一鍵匯入用）、一頁封面圖

Babele 規定一個合集包一個對照檔，沒辦法把 48 包塞進一檔，所以交代的「`translations/` 只新增一個檔」做不到，改成**有譯名的合集包各一檔，共 34 檔**（另外 14 包一條都對不到，不產檔）。檔名都是 `statblock-library.` 開頭，其他譯文檔一個都沒動。

要在 Foundry 看到效果，你的世界必須**有裝 SBL 模組**。沒裝的話這 34 檔不會被讀，也不會出錯。

## 一句話

10,387 條（9,547 個不同的英文名）裡，**補了 1,140 條（915 個名稱）**，其餘留英文。
SBL 有將近一半（約 4,700 條）是冒險之路與 PFS 裡有名有姓的 NPC，CHM 和上游都沒有，這部分本來就補不到；怪物圖鑑 1–3 補到一半以上。

## 數字

| | 名稱數 | 條數 |
|---|---:|---:|
| SBL 總數 | 9,547 | 10,387 |
| **已補** | **915** | **1,140** |
| 　└ 來源：果園 CHM | 756 | 934 |
| 　└ 來源：上游（本模組舊 bestiary 檔，CHM 有同詞佐證） | 90 | 110 |
| 　└ 來源：用語集（雲端拿得到的片段） | 56 | 78 |
| 　└ 來源：本模組既有對照檔（基礎怪物） | 13 | 18 |
| 留英文 | 8,632 | 9,247 |

同一個英文名在不同合集包會共用一個譯名（例如 Goblin 在怪物圖鑑和 Rappan Athuk 都是「地精」），所以條數比名稱數多。

補得比較多的合集包：

| 合集包 | 總條數 | 已補 |
|---|---:|---:|
| 怪物圖鑑 1–3 | 957 | 535 |
| 怪物圖鑑 4–6 | 793 | 142 |
| NPC 圖鑑（NPCs and Villians） | 825 | 101 |
| Tome of Horrors | 1,007 | 75 |
| PFS | 1,726 | 58 |
| 魔寵（Familiars） | 104 | 53 |
| 戰役設定（Companion and Campaign Settings） | 416 | 36 |
| 其他 27 包 | 4,559 | 140 |
| 一條都沒補到的 14 包 | — | 0 |

一條都沒有的：Giantslayer、Ironfang Invasion、Ruins of Azlant、Curse of the Crimson Throne、We Be Goblins 等，全是有名有姓的 NPC。

## 顯示出來長怎樣

- 合集包列表、日誌標題：`凶暴鼠（Dire Rat）(CR 0.33)`。中文在前、英文原名接著，CR 或職業等級照原文留在最後（跟其他怪物對照檔一樣，打英文也搜得到）
- 打開日誌，數據方塊那一頁的標題也換成同一個名字
- **數據方塊內文、封面頁、合集包名稱都維持英文**。數據方塊是給 SBC 解析的英文文字，翻了會匯入失敗
- 用 SBC 匯入後的怪物名稱是從數據方塊內文抓的，所以**匯入出來的角色仍是英文名**。這是 SBC 的行為，對照檔管不到

## 怎麼決定的

來源優先序（照「CHM 優先」，加上你定過的東西）：

1. **用語集定案**：pf1-chm-src `_資料/用語集對照-CHM不一致.tsv` 裡層級「定案」、分類含 npc／monster 的列。這是用語集裡跟 CHM 不一致的那部分，雲端只拿得到這份
2. **既有對照檔**：`pf1.basic-monsters.json` 已經定的（Acolyte 侍祭、Wasp Swarm 黃蜂群等），兩處寫法一致
3. **CHM**：CHM 裡「中文（English）」寫在一起的地方。CHM 沒有一隻一隻的怪物頁，取的是召喚表、魔寵表、動物夥伴、專長、冒險模組裡提到這隻怪的寫法
4. **上游**：本模組 10/31 刪掉的八個 pf1-bestiary 舊檔（上游 fvtt-cn 簡體稿繁化）。**只有上游一個來源的，要 CHM 裡找得到同一個詞才收**，而且 CHM 沒把這個詞配給別的英文

CHM 抽出來的中文前面常黏著別的字（「或是黑熊」「1d4 頭穴巨人」「例如幽魂或附鬼」），程式會切掉前面的虛詞、量詞；切不乾淨、看起來還像半句話的一律不收，原文留在譯名表的「CHM寫法」欄。
同一個英文 CHM 有兩種以上寫法的，主寫法要佔三倍以上才收（標 ⚠），其餘等你裁定。

最後**每一條都人工看過一遍**。發現程式規則擋不住的錯，寫進程式裡的排除清單（`REJECT`），重跑也不會跑回來。主要是英文剛好撞到普通單字：

- SBL 裡叫 Beetle、Talon、Spike、Glory、Craven、Jackdaw 的其實是有名字的 NPC 或動物夥伴，CHM 的「甲蟲」「爪擊」「釘刺」「榮耀」是別的東西
- Tome of Horrors 的 Fisherman、Haunt、Phantasm、Protector、Aberrant、Living Monolith 是怪物，CHM 的「漁夫」「作祟」「魅影幻覺」「戍衛寵」「異怪」「活體石像」是職業、陷阱、幻術子派、魔寵變體、血統、進階職業
- 上游舊檔有 6 條 CHM 的「同詞」其實指別的：Nightwalker（CHM「暗夜行者」是神恩 Come by Night）、Dullahan（CHM「無頭騎士」是作祟 Headless Horseman）、Siren、Giant Bee、Taotieh、Jinushigami

完整 38 條排除理由在譯名表「說明」欄，開頭寫「不收：」。

另外 4 條是 CHM 字串黏著前文、程式切不準，**人工照 CHM 原文定邊界**（詞本身是 CHM 的寫法，沒有改字）：

| 英文 | CHM 原文 | 收的寫法 |
|---|---|---|
| Choral the Conqueror | 遠在征服者卓拉爾（Choral the Conqueror） | 征服者卓拉爾 |
| Mammon | 魔鬼大公瑪門（Mammon） | 瑪門 |
| Plague Zombie | 會產生染疫喪屍（plague zombie） | 染疫喪屍 |
| Witchfire | 摧毀巫火（witchfire） | 巫火（上游寫「巫焰」） |

## ⚠ 請你看一眼

### 一、用語集定案跟 CHM 不同（照用語集）

26 條，都是 NPC 圖鑑的職業 NPC。用語集是你定的，照用語集：

| 英文 | 用語集（已用） | CHM 寫法 |
|---|---|---|
| Bandit | 強盜 | 土匪 |
| Burglar | 飛賊 | 夜行大盜 |
| Captain | 船長 | 上尉 |
| Cutpurse | 剪綹賊 | 扒手 |
| Enforcer | 戒律官 | 脅迫者 |
| Giant Slayer | 巨人斬 | 巨人殺手 |
| Medusa | 蛇髮女妖 | 美杜莎 |
| Merisiel | 梅瑞希爾 | 梅莉雪 |
| Noble Scion | 世家子弟 | 貴族後裔 |
| Tomb Raider | 盜墓者 | 古墓麗影 |
| Vaultbreaker | 寶庫破襲者 | 通天大盜 |
| Wanderer | 流浪者 | 漫遊者 |

其餘 14 條（Barkeep、Beast Master、Court Poet……）在譯名表，來源欄寫「用語集」。

### 二、CHM 跟上游寫法不同（照 CHM）

| 英文 | 上游 | 這次用（CHM） |
|---|---|---|
| Astral Deva | 星界神使 | 星界使徒 |
| Centaur | 人馬 | 半人馬 |
| Dire Wolf | 恐狼 | 凶暴狼 |
| Drow | 卓爾精靈 | 卓爾 |
| Gorgon | 銅牛 | 石化牛 |
| Greater Shadow | 高等幽影 | 高等暗影 |
| Gug | 古革 | 古革巨人 |
| Hydra | 多頭蛇 | 多頭蛇蜥 |
| Leucrotta | 擬聲尖牙獸 | 吸血狼 |
| Planetar | 異界神侍 | 界天使 |
| Tiefling | 提夫林 | 魔裔 |
| Triton | 梭螺魚人 | 特里同 |
| Trumpet Archon | 號角神使 | 號角聖使 |
| Vanara | 靈猴裔 | 靈猴族 |

### 三、CHM 有兩種以上寫法，取了多數的（59 條，標 ⚠）

大部分只是 CHM 某一處多黏了一個字（「要創造神裔」「取代野豬」），不影響。真的有不同寫法、值得看的：

| 英文 | 收的寫法 | CHM 其他寫法 |
|---|---|---|
| Ghoul | 食屍鬼 ×11 | 屍鬼 ×1 |
| Horse | 馬 ×16 | 馬匹 ×5、驍駿 ×1 |
| Monkey | 猴子 ×10 | 猿猴 ×3、猴 ×2 |
| Manticore | 蠍獅 ×6 | 蠍尾獅 ×2 |
| Quasit | 小惡魔 ×5 | 誇塞魔、誇賽魔 各 1 |
| Troglodyte | 戰蜥人 ×4 | 穴居人 ×1 |
| Trumpet Archon | 號角聖使 ×6 | 號手神使 ×1 |
| Ghaele Azata | 迦勒天 ×5 | 迦勒天使 ×1 |
| Satyr | 薩特羊人 ×9 | 薩提爾、薩特 各 1 |
| Agathion | 福使 ×14 | 獅首神使 ×3（這是 Leonal 的譯名，CHM 有一處配錯） |

### 四、寫法不一、沒填，等你裁定（73 條）

兩種寫法差不多多，沒辦法替你挑。譯名表「說明」欄寫「CHM 寫法不一，等裁定」，各寫法與次數在「CHM寫法」欄。比較常用到的：

| 英文 | CHM 寫法 | 上游 |
|---|---|---|
| Shadow（不死生物） | 陰影 ×13（多半是描述符、子派）、幽影 ×4、暗影 ×3 | — |
| Lich | 活屍化 ×2（恐怖冒險的腐化）、巫染 ×2、巫妖 ×1 | 巫妖 |
| Tiger | 虎 ×8、老虎 ×3 | 虎 |
| Owl | 梟 ×10、夜梟 ×4、貓頭鷹 ×4 | — |
| Hawk | 鷹 ×9、獵鷹 ×4 | — |
| Elephant | 象 ×13、大象 ×5 | 象 |
| Deep One | 深潛者 ×4、深裔 ×3 | — |
| Catfolk | 貓族 ×4、貓人 ×4 | 貓人族 |
| Faerie Dragon | 妖精龍 ×2、仙靈龍 ×2 | — |
| Allosaurus | 異龍 ×3、異特龍 ×2 | 異龍 |
| Mephistopheles | 墨菲斯托費利斯 ×3、墨菲斯托 ×2 | — |
| Shadow Mastiff | 幽影獒犬 ×2、暗影獒犬 ×2 | 暗影獒犬 |
| Phoenix | 鳳凰 ×2、不死鳥 ×1 | 鳳凰 |
| Weasel | 黃鼠狼 ×7、鼬 ×4 | — |
| Red Mantis Assassin | 紅螳螂刺客 ×3、紅螳螂殺手 ×2 | — |
| Razmiran Priest | 拉茲密安牧師 ×2、拉茲密爾祭司 ×2 | — |

Lich 跟上次模板資料夾一樣，CHM 的「活屍化」是腐化不是巫妖模板，你裁定時請留意。

### 五、只差一步的（列了候選，沒填）

- **上游有、CHM 把同一個詞配給「幾乎同一個英文」的 12 條**：CHM 那邊是複數或英文打錯，例如 Mummy 木乃伊（CHM 寫 mummies）、Wood Golem 木魔像（CHM 拼成 wood gelem）、Shocker Lizard 閃電蜥蜴（CHM 寫 shockerlizard）、Raktavarna 化物羅剎（CHM 寫 raktavarna rakshasa）。看過覺得是同一隻就把上游寫法抄進「譯名」欄
  - 但其中 Thunderbird「雷鳥」在 CHM 是 Ptarmigan（雷鳥這種鳥），Shinigami「死神」在 CHM 是 Reaper，這兩條真的不同，不要抄
- **上游有、CHM 完全找不到這個詞的 196 條**：其中 39 條是龍（成年黑龍、古金龍……，CHM 沒有成年、古老這些年齡段的龍名），其餘是 CHM 沒收錄的怪物（Akata、Chupacabra、Destrachan……）。不符合「CHM 有同詞」的條件，沒收；上游寫法在「上游寫法」欄。**用語集裡如果有龍的年齡段定名，那 39 條能一口氣補上**
- **CHM 有提到、但抽出來黏著前後文切不準的 74 條**：原文在「CHM寫法」欄，看一眼就知道該怎麼切
- **英文跟法術、專長、裝備同名的 13 條**（Fire Snake 在 CHM 是法術「火蛇術」、Klar 是盾牌、Nightmare 是法術「夢魘」等），怕 CHM 那個詞指的是同名的另一個東西，沒收。跟怪物模板、職業同名而譯名一致的（Vampire 吸血鬼、Zombie 喪屍、Ghost 幽魂、Cleric 牧師）有收
- **CHM 只有一處單字的 3 條**：Deer 鹿、Ermine 貂、Moth 蛾。單字最容易抓錯邊界，沒收

### 六、其他

- **凶暴／兇暴**：CHM 繁體寫「凶暴鼠」「凶暴狼」，本模組舊有譯文（上游繁化）多寫「兇暴」。照 CHM 優先用「凶暴」。要統一成「兇暴」的話，在譯名表搜尋取代就好。同理「岩漿怪」用「岩」
- **同一個中文對到兩個英文**：Sea Krait、Sea Serpent 都是「海蛇」（CHM 前者是魔寵海蛇、後者是海怪），Peacock、Peafowl 都是「孔雀」。照 CHM 原樣，沒有自己區分
- **Kyra**：CHM 有一處寫「凱拉斯」，跟常見譯法差很多，沒收，等用語集

**用語集能幫最多的就是這幾批**：上游有寫法但 CHM 沒有的 196 條（含 39 條龍）、寫法不一的 73 條、冒險之路的 NPC 人名。用語集在你本機，雲端拿不到。

## 載入會不會壞

- 對照檔**沒寫 mapping**，用 Babele 2.9.1 內建的日誌對應（名稱 → `name`、頁面 → `pages`）。這是讀 Babele 2.9.1 原始碼（`default-mappings.js` 的 JournalEntry、`document` 轉換器）確認的，不會指到不存在的轉換器，也沒動 `scripts/`
- 頁面用頁的文件 ID 當鍵，Babele 會先比對 ID 再比對名稱；同一個合集包裡名稱重複的條目用條目的文件 ID 當鍵
- 只寫了 `name` 與數據方塊那一頁的 `name`，沒寫內文、封面頁、合集包名稱，Babele 遇到沒給的欄位就保留原文
- 條目清單是程式直接從 SBL 0.8.0 原始碼讀出來的，每個鍵都存在
- 雲端沒能在 Foundry 裡實際跑（沒有 Foundry 環境），下面的實測一定要做

## 驗證（verify_compendium.py）

`KNOWN_ADDED` 加了「檔名以 `statblock-library.` 開頭」這條（34 檔會隨譯名表增減，用檔名開頭登記比逐檔列安全）。比對來源跟上次一樣用上游 `430934d`。

| 項目 | main | 這個分支 |
|---|---|---|
| 檔案集合一致 | 過 | 過 |
| entries 鍵集合、mapping、結構、HTML 標籤、連結 ID | 過 | 過 |
| 無殘留簡體 | 不過，9 處 | 不過，同樣 9 處 |

9 處都是 main 原本就有的「樑」字誤報（雲端 OpenCC 比你本機新），跟這次無關。

驗證程式只比對上游有的檔，新檔另外查過：結構只有 `entries`／`name`／`pages`，1,140 條都對得上條目清單。OpenCC 掃出 30 處「可能是簡體」，全是 凶／兇、岩／巖、游／遊 這類一字多形（CHM 繁體版本來就這樣寫），不是簡體字。

## 刻意沒做的

- **數據方塊內文**：SBC 要讀英文
- **合集包名稱**（Bestiaries 1-3、AP - Kingmaker 等）：要翻書名，CHM 有部分書名但沒逐一對過，留英文
- **SBL 有的、PF1 系統內建 basic-monsters 也有的**：兩邊各自有對照檔，譯名一致
- `build_chm.py` 的比對邏輯、其他譯文檔：都沒動。根目錄 README 那句「statblock-library 還沒有對照檔」也沒改，等你決定要不要發版再改

## 在 Foundry 裡實測

先確認世界裡有啟用 **Pathfinder 1e Statblock Library (SBL)** 模組。

1. 切到這個分支，或把 `translations/statblock-library.*.json`（34 檔）複製到你 Foundry 的 `Data/modules/pf1e-compendium-zhtw/translations/`
2. 重新整理網頁（Babele 只在載入時讀對照檔）
3. F12 主控台確認沒有 `pf1e-compendium-zhtw | 向 Babele 註冊失敗` 或 Babele 的紅字錯誤
4. 合集包分頁，Statblocks 資料夾：
   - 「Bestiaries 1-3」：標題維持英文；列表裡 Dire Rat 顯示「凶暴鼠（Dire Rat）(CR 0.33)」、Aboleth 顯示「底棲魔魚（Aboleth）(CR 7)」，Alchemical Golem 維持英文
   - 「NPCs and Villians」：Bandit 顯示「強盜（Bandit）(warrior 2)」
   - 「Familiars」：Cat 顯示「貓（Cat）(CR 1/4)」
5. 點開「凶暴鼠」那則日誌：
   - 日誌標題、數據方塊那一頁的標題是中文
   - 數據方塊內文、封面頁維持英文，版面正常
   - 按頁面上的匯入鈕（要裝 SBC），確認還是能正常匯入（匯入出來的怪物名稱是英文，正常）
6. 合集包的搜尋框打 `Dire`，應該找得到「凶暴鼠（Dire Rat）」等
7. 其他合集包（法術、專長、基礎怪物、怪物模板）隨便點幾條，確認沒被影響

要給簡體版：把 `_build/審核/zhcn/statblock-library.*.json` 複製到 pf1e-compendium-zhcn 的 `translations/`，簡體 Foundry 照上面再測一次。

## 改譯名、重跑

- 只改譯名：直接改 `_build/statblock-library譯名.tsv` 的「譯名」欄，然後 `python _build/statblock_library.py`。會重寫 34 檔（某包的譯名全刪光，那包的檔也會刪掉）
- 重新比對（CHM 發新版、SBL 更新）：`python _build/statblock_library.py --scan`。**會蓋掉譯名表，先把你手改的「譯名」欄備份**。需要 PyYAML（`pip install pyyaml`）、OpenCC，環境變數 `PF1_CHM_DIR` 指 pf1-chm-src、`PF1_SBL_SRC` 指 SBL 原始碼的 `src\`。人工排除與人工定邊界寫在程式開頭的 `REJECT`、`BOUNDARY`，重跑會沿用

`_build/審核/` 在 `.gitignore` 裡，這份報表與簡體稿是硬加進分支的；`.gitignore` 本身沒改。
