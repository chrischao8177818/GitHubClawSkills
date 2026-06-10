# 價格歷史儲存與查詢參考

## 主帳位置

使用 `price-history/entries/YYYY/MM.jsonl` 作為價格歷史的標準明細資料來源，並使用 `price-history/indexes/item-summary.json` 作為摘要索引。這些資料放在 repo 根目錄下，刻意和 `artifacts/` 交付物、`bookkeeping/YYYY/MM/` 完整記帳資料分開，避免價格歷史查詢影響任務輸出與月報。

建議結構：

```text
price-history/
  entries/
    2026/
      04.jsonl
      06.jsonl
  indexes/
    item-summary.json
```

## JSONL Schema

每一行代表一個採買品項：

```json
{
  "date": "2026-06-01",
  "merchant": "待確認",
  "item_name": "澳牛肩里炒肉片",
  "canonical_item": "澳洲炒牛肉片",
  "query_group": "牛肉",
  "category": "肉類",
  "quantity": 1,
  "unit_price": 120,
  "subtotal": 120,
  "currency": "NT$",
  "source_comment_id": "待確認",
  "status": "confirmed",
  "notes": ""
}
```

## 欄位說明

- `date`：使用 `YYYY-MM-DD`。若缺少日期，使用台灣當天日期。
- `merchant`：有商家名稱時填入商家；否則使用 `待確認`。
- `item_name`：保留使用者或收據上的原始品項文字。
- `canonical_item`：修正明顯 OCR 變體與別名，但仍保留具體品項層級。
- `query_group`：儲存使用者可能查詢的較大種類，例如 `牛肉`、`高麗菜`、`雞蛋`。
- `category`：儲存記帳式分類，例如 `肉類`、`蔬菜`、`水果`、`蛋類`、`其他`。
- `quantity`：已知時使用數字；否則使用 `待確認`。
- `unit_price`：已知時使用數字；否則使用 `待確認`。
- `subtotal`：已知時使用數字；否則使用 `待確認`。
- `currency`：預設為 `NT$`。
- `source_comment_id`：有 issue comment id 時填入；否則使用 `待確認`。
- `status`：可用於統計的數字紀錄使用 `confirmed`；關鍵資訊不確定時使用 `pending`。
- `notes`：保留 OCR 不確定性、收據脈絡或人工修正備註。

## 比對行為

1. 正規化查詢文字：移除空白，刪掉 `歷史價格`、`歷史金額`、`最高`、`最低`、`平均` 這類常見詞，保留品項關鍵字。
2. 精準品項查詢時，先比對 `canonical_item` 與 `item_name`。
3. 若沒有精準命中，再比對 `query_group`。
4. 若 `query_group` 命中多個標準品項，回覆候選清單，並附上各品項的次數、最近價格、平均、最低與最高。
5. 若沒有直接命中，使用子字串與模糊相似度列出相近候選。

## 統計規則

只納入符合以下條件的紀錄：

- `status` 為 `confirmed`。
- `unit_price` 是數字。

回覆時包含：

- 依日期判斷的最近 confirmed 價格
- 最高價
- 最低價
- 平均價
- confirmed 購買次數
- 若有 pending 紀錄，顯示 pending 筆數

除非使用者明確要求小數，平均值四捨五入到整數新台幣。

## 索引規則

- 每次新增明細後，重建 `indexes/item-summary.json`。
- 索引只保存摘要，不取代 `entries/YYYY/MM.jsonl` 原始明細。
- 索引至少包含每個 `canonical_item` 與 `query_group` 的 confirmed 次數、pending 次數、最近價格、最高、最低與平均。
- 若索引遺失或懷疑過期，使用 `scripts/price_history.py rebuild-index` 從月份明細重建。
- 若發現舊資料在 `artifacts/price-history/ledger.jsonl` 或 `price-history/ledger.jsonl`，使用 `migrate-ledger` 轉入月份檔；遷移後查詢以 `price-history/entries/` 為準。

## 圖片批次寫入規則

- 純圖片訊息辨識為收據、發票或採購明細後，必須同步寫入價格歷史。
- 所有有價格的商品或服務明細都要寫入，包含購物袋與服務費；不要寫入小計、總計、實付金額、折扣與付款資訊。
- 使用 `add-batch --input <json>` 一次寫入同張收據的所有明細，寫完後只重建一次索引。
- 批次 JSON 可使用單一品項物件、品項陣列，或 `{"items": [...]}`。
- 每筆資料仍使用標準 JSONL schema；品名不確定但價格可辨識時設定 `status=pending`。
- `source_comment_id` 明確時，防重複鍵為來源 comment id、日期、商家、原始品名、數量與單價；同一張圖片重跑時會略過已存在紀錄。來源 comment id 為 `待確認` 時不啟用防重複，避免誤刪真正不同的購買。

## 輸出風格

使用繁體中文 Markdown。回覆要簡短，並且能幫助使用者判斷要不要購買。歷史明細與候選清單優先使用表格。
