---
name: price-history
description: 記錄採買品項價格與查詢歷史價格。當使用者輸入採買明細、購買清單、收據文字、發票或採買照片時使用；即使訊息只有圖片附件、沒有文字，只要圖片辨識為收據、發票或採購明細，也必須使用此技能保存品項與金額。詢問「歷史價格」、「歷史金額」、「最高」、「最低」、「平均」、「最近一次」、「買貴嗎」、「牛肉多少」、「高麗菜歷史價格」等品項或種類價格查詢時也使用。此技能只處理品項價格歷史，不取代 bookkeeping 的完整記帳、月報與月清單功能。
---

# 價格歷史

## 用途

使用這個技能維護輕量的採買品項價格帳，並回答品項歷史價格問題。此技能要和 `bookkeeping` 分開：`bookkeeping` 負責完整記帳、月報與月清單；此技能只負責品項名稱、價格歷史，以及「現在買算不算貴」這類查詢。

## 核心流程

1. 判斷使用者是在記錄採買資料，還是在查詢歷史價格。
2. 若訊息只有圖片附件，先辨識是否為收據、發票或採購明細；是則繼續寫入，不是則不要新增價格歷史。
3. 若是記錄採買，從文字或圖片萃取結構化品項，使用批次寫入將每個有價格的明細各自追加成一筆 JSON 到 `price-history/entries/YYYY/MM.jsonl`。
4. 完成採買 Markdown 整理後，必須實際執行 `scripts/price_history.py add-batch`；不可只輸出表格。
5. 若是查詢價格，讀取 `price-history/entries/` 與 `price-history/indexes/item-summary.json`，用精準品項名稱與較大的查詢種類進行比對，再用 Markdown 回覆統計結果。
6. 一律保留不確定性。無法確認的品名、金額、日期、商家或數量，必須寫成 `待確認` 或 `status=pending`。
7. 使用此技能時，不要修改 `.agents/skills/bookkeeping` 或它的輸出資料。

## 資料規則

- 標準明細固定存放於 `price-history/entries/YYYY/MM.jsonl`。
- 摘要索引固定存放於 `price-history/indexes/item-summary.json`。
- 每個品項追加一行；不要重寫無關的主帳紀錄。
- 預設幣別為 `NT$`。
- 若缺少日期，使用台灣當天日期。
- 同時保留原始品名與正規化欄位：
  - `item_name`：收據或使用者輸入的原始文字，例如 `澳牛肩里炒肉片`。
  - `canonical_item`：穩定的標準品名，例如 `澳洲炒牛肉片`。
  - `query_group`：較大的查詢種類，例如 `牛肉`。
- 只有 `status=confirmed` 且價格是數字的紀錄，才納入最高、最低與平均統計。
- `pending` 紀錄仍要保留在主帳中，方便日後修正；查詢時要另外列出或提示。
- 收據上的所有有價格明細都要寫入，包含購物袋與服務費；小計、總計、實付金額、折扣與付款資訊不得寫入。
- `source_comment_id` 使用原始使用者訊息的 comment id。
- 使用來源 comment id、日期、商家、原始品名、數量與單價判斷重複，讓同一張圖片重跑時不會重複新增。

## 查詢規則

- 精準品項查詢要先比對 `canonical_item` 與 `item_name`。
- 種類查詢要比對 `query_group`。
- 若種類查詢命中多個 `canonical_item`，回覆候選品項表，不要直接混在一起計算。
- 若使用者回覆候選品項名稱或 `全部`，再執行更精準的查詢或完整種類彙總。
- 若沒有精準或種類命中，從既有主帳值列出相近候選。
- 若使用者指定 `最近 30 天`、`今年`、`最近 5 次` 這類範圍，先套用範圍再計算統計。

## 腳本

使用 `scripts/price_history.py` 進行可重複驗證的明細寫入、索引重建、舊檔遷移與價格查詢。

新增一個品項：

```bash
python .agents/skills/price-history/scripts/price_history.py add-entry --date 2026-06-01 --item-name 牛肉 --canonical-item 牛肉 --query-group 牛肉 --category 肉類 --unit-price 120
```

批次新增同一張收據的品項：

```bash
python .agents/skills/price-history/scripts/price_history.py add-batch --input artifacts/{issue-comment-id}/price-history-items.json
```

查詢單一品項或種類：

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

變更主帳 schema、查詢行為或輸出格式前，先閱讀 `references/storage-and-query.md`。
