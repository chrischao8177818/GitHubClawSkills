# price-history

記錄採買品項價格與查詢歷史價格的 Codex skill。

這個技能適合用在你想知道「某個品項以前買多少」、「最高最低平均是多少」、「這次算不算買貴」的情境。它和 `bookkeeping` 分工不同：

- `bookkeeping`：完整記帳、月報、月清單。
- `price-history`：品項價格歷史、種類查詢、最高最低平均與候選品項。

## 使用方式

記錄採買資訊時，可以直接輸入文字或貼採買明細、收據、發票照片，例如：

- `6/1 牛肉 120，高麗菜 35`
- `今天買澳牛肩里炒肉片 146、葡萄 145`
- `幫我記錄這張採買明細`

查詢歷史價格時，可以直接用自然語言：

- `牛肉歷史金額`
- `澳洲炒牛肉片最高最低平均`
- `高麗菜最近一次多少`
- `雞蛋現在算貴嗎`

## 資料結構

長期資料會放在 repo 根目錄的 `price-history/`，不放在 `artifacts/`：

```text
price-history/
  entries/
    2026/
      04.jsonl
      05.jsonl
  indexes/
    item-summary.json
```

檔案用途：

- `entries/YYYY/MM.jsonl`：逐筆採買品項價格紀錄。
- `indexes/item-summary.json`：依品項與種類彙整的摘要索引。

## 常用指令

新增一筆價格紀錄：

```bash
python .agents/skills/price-history/scripts/price_history.py add-entry --date 2026-06-01 --item-name 牛肉 --canonical-item 牛肉 --query-group 牛肉 --category 肉類 --unit-price 120
```

查詢價格歷史：

```bash
python .agents/skills/price-history/scripts/price_history.py query-price 牛肉
```

重建摘要索引：

```bash
python .agents/skills/price-history/scripts/price_history.py rebuild-index
```

從舊的單一主帳遷移：

```bash
python .agents/skills/price-history/scripts/price_history.py migrate-ledger --source artifacts/price-history/ledger.jsonl
```

## 安裝

可透過技能安裝工具安裝到專案的 `.agents/skills`：

```bash
install-skill-from-github.py --repo chrischao8177818/GitHubClawSkills --path price-history --dest .agents/skills
```

或使用 GitHub tree URL：

```bash
install-skill-from-github.py --url https://github.com/chrischao8177818/GitHubClawSkills/tree/main/price-history --dest .agents/skills
```

## 主要檔案

- `SKILL.md`：技能觸發描述與執行規則。
- `agents/openai.yaml`：Codex UI 顯示資訊。
- `references/storage-and-query.md`：資料結構、查詢規則與索引規則。
- `scripts/price_history.py`：寫入、查詢、重建索引與遷移舊資料的輔助工具。

## 純圖片自動寫入

Skill 的觸發描述可以辨識採買與價格查詢意圖，但只有圖片、沒有文字時，宿主專案在看見圖片內容前無法判斷它是不是收據。因此，要讓純圖片辨識完成後自動寫入價格歷史，宿主專案的 `AGENTS.md` 也需要加入路由規則：

```md
### 採購圖片與價格歷史同步
- 使用者只提供圖片、沒有文字時，先判斷圖片是否為收據、發票或採購明細。
- 辨識為採購內容後，除了產生原本的記帳 Markdown，也必須使用 `.agents/skills/price-history` 同步寫入價格歷史。
- 所有有價格的商品或服務明細都要寫入；不要寫入小計、總計、實付金額、折扣與付款資訊。
- 完成整理後，實際執行 `price_history.py add-batch`，不可只輸出表格。
```

批次資料可直接使用 JSON 陣列，或使用 `{"items": [...]}`：

```bash
python .agents/skills/price-history/scripts/price_history.py add-batch --input artifacts/{issue-comment-id}/price-history-items.json
```

批次寫入會使用來源 comment id 明確時，批次寫入會使用來源 comment id、日期、商家、原始品名、數量與單價判斷重複；同一張圖片重跑時不會重複新增。

