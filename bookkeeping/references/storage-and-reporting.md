# 記帳儲存與月報規則

## 資料夾結構

記帳資料存放在：

```text
bookkeeping/
  2026/
    06/
      2026-06-03__早餐與午餐.md
      2026-06-04__信用卡帳單.md
      monthly-list.md
      summary.md
      summary.svg
```

- 月份資料夾使用 `bookkeeping/YYYY/MM/`。
- 月份名稱需補零，例如 `06`。
- 一個 Markdown 檔只放一筆記錄。
- 若內容需要修正，直接更新原檔，不要另外複製。
- `monthly-list.md`、`summary.md` 與 `summary.svg` 是生成檔，不視為來源資料。

## 記錄範本

使用可被機器讀取的 Markdown 表格：

```md
---
date: 2026-06-03
title: 早餐與午餐
source: telegram
---

# 記帳整理結果

## 明細

| 日期 | 品項 | 分類 | 數量 | 單價 | 小計 | 備註 |
|------|------|------|------|------|------|------|
| 2026-06-03 | 鐵板麵 | 餐飲 | 1 | NT$115 | NT$115 | 早餐 |

## 分類小計

| 分類 | 金額 |
|------|------|
| 餐飲 | NT$115 |

## 總計

| 項目 | 金額 |
|------|------|
| 合計 | NT$115 |
```

## 月報規則

- 只讀取該月份的 entry Markdown 檔。
- 忽略 `monthly-list.md`、`summary.md`、`summary.svg` 與其他生成檔。
- 依 `分類` 欄位彙總。
- 占比只根據可計算的數字金額計算。
- 若金額無法確認，保留在待確認區塊。
- 若某分類不納入占比分析，要獨立列出，且不計入圓餅圖。

## 常用指令

- `python .agents/skills/bookkeeping/scripts/bookkeeping.py new-entry --date 2026-06-03 --title 早餐與午餐`
- `python .agents/skills/bookkeeping/scripts/bookkeeping.py month-report --month 2026-06`

## 月報輸出

月報應包含：

- `monthly-list.md`：該月份所有逐筆明細清單，包含來源檔名。
- `summary.md`：分類分析、占比、總計與 Mermaid 圓餅圖。
- `summary.svg`：方便單獨查看的圓餅圖。
- 月份標題與期間。
- 分類金額與占比表。
- 總計。
- 簡短分析重點。
