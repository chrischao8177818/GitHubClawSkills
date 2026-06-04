# bookkeeping

整理日常記帳、收據、發票、消費明細與月報分析的 Codex skill。

這個技能適合用在你平常直接丟文字或圖片給小龍蝦的情境，例如：

- `早餐 鐵板麵 115`
- `7-11 買咖啡 55、飯糰 39、茶葉蛋 18`
- 收據、發票、菜單、購買明細照片
- `幫我整理本月開銷`
- `幫我做上月月報`
- `分析 2026-06 開銷`
- `這個月花多少`

## 功能

- 將每次記帳輸入整理成 Markdown 明細。
- 將記錄存放到 `bookkeeping/YYYY/MM/`。
- 支援一筆輸入包含多個品項。
- 缺漏或無法辨識的欄位會保留為 `待確認`。
- 預設幣別為 `NT$`。
- 可產生指定月份的月報。
- 月報會輸出分類彙總、占比、分析重點與圓餅圖。
- 月報會另外產生 `monthly-list.md`，整理該月份所有逐筆明細。

## 輸出結構

日常記帳會產生單次記錄檔：

```text
bookkeeping/
  2026/
    06/
      2026-06-03__早餐與午餐.md
```

產生月報時，會在同一個月份資料夾產生：

```text
bookkeeping/
  2026/
    06/
      monthly-list.md
      summary.md
      summary.svg
```

檔案用途：

- `monthly-list.md`：該月份所有逐筆明細清單。
- `summary.md`：分類金額、占比、分析重點與 Mermaid 圓餅圖。
- `summary.svg`：可單獨查看的圓餅圖。

## 常用指令

建立標準記帳檔：

```bash
python .agents/skills/bookkeeping/scripts/bookkeeping.py new-entry --date 2026-06-03 --title 早餐與午餐
```

產生指定月份月報：

```bash
python .agents/skills/bookkeeping/scripts/bookkeeping.py month-report --month 2026-06
```

## 安裝

可透過技能安裝工具安裝到專案的 `.agents/skills`：

```bash
install-skill-from-github.py --repo chrischao8177818/GitHubClawSkills --path bookkeeping --dest .agents/skills
```

或使用 GitHub tree URL：

```bash
install-skill-from-github.py --url https://github.com/chrischao8177818/GitHubClawSkills/tree/main/bookkeeping --dest .agents/skills
```

## 主要檔案

- `SKILL.md`：技能觸發描述與執行規則。
- `agents/openai.yaml`：Codex UI 顯示資訊。
- `references/storage-and-reporting.md`：資料夾結構、記錄範本與月報規則。
- `scripts/bookkeeping.py`：建立記錄與產生月報的輔助工具。
