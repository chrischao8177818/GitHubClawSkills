---
name: bookkeeping
description: 整理記帳、收據、發票、消費明細、照片辨識與月報分析。當使用者要記錄支出、把收據或照片轉成結構化記帳資料、將記錄存到 `bookkeeping/YYYY/MM/`，或使用「本月開銷」、「上月開銷」、「月報」、「YYYY-MM 記帳」、「分析 X 月開銷」、「這個月花多少」等語句要求產生指定月份月報與圓餅圖時使用。
---

# Bookkeeping

## 概要

這個技能用來把零散的記帳文字、收據或照片，整理成可長期保存的月資料，並在需要時重新產生月報。

## 流程

1. 把每一筆記帳整理成一個 Markdown 檔，存到 `bookkeeping/YYYY/MM/`。
2. 一個檔案對應一筆記錄；若內容修正，直接更新原檔，不另外複製。
3. 月報只讀取該月份的 entry 檔，排除 `summary.md`、`summary.svg` 和 `monthly-list.md`。
4. 使用者要求某月月報時，重新產生摘要檔與月報清單；摘要檔包含分類合計、占比、簡短分析與圓餅圖，月報清單則列出該月所有逐筆明細。
5. 需要建立標準記錄檔時，可用 `scripts/bookkeeping.py new-entry --date YYYY-MM-DD --title ...`。

## 記錄規則

- 保留原本記帳欄位：`日期`、`品項`、`分類`、`數量`、`單價`、`小計`、`備註`。
- 無法確認的內容一律寫成 `待確認`。
- 預設幣別為 `NT$`。
- 若日期缺漏，使用台灣當天日期。
- 優先使用結構化 Markdown 表格，讓月報腳本可以穩定回讀。
- 儲存根目錄使用 `bookkeeping/YYYY/MM/`，月份需補零。
- 每筆記錄檔名建議用 `YYYY-MM-DD__slug.md`。

## 月報

- 使用 `scripts/bookkeeping.py month-report --month YYYY-MM` 重新產生月報。
- 月報要能彙總分類金額、計算占比、顯示總計。
- 月報要附上簡短分析，不只列數字。
- 月報要同步輸出 `monthly-list.md`，作為該月完整逐筆明細清單。
- `summary.md` 內優先放 Mermaid 圓餅圖，另輸出 `summary.svg` 方便單獨查看。
- 重新彙整時要排除生成檔，避免重複計算。
- 若某分類刻意不納入占比分析，要在獨立區塊列出，且不計入圓餅圖。

## 參考

詳見 `references/storage-and-reporting.md`，裡面有資料夾結構、記錄範本與月報規則。
