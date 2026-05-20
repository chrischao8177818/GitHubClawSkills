# cooking-video-summary

料理內容整理與查找入口。

這個 skill 會先呼叫 `gemini-summary`，再把摘要整理成 `recipes/` 裡的標準食譜檔。
如果你只是想查舊資料，直接輸入短句就可以，不需要手動指定搜尋範圍。

## 使用方式

整理新內容時，直接貼網址或來源內容即可：

- `cooking-video-summary https://www.youtube.com/watch?v=...`
- `cooking-video-summary https://youtu.be/...`
- `cooking-video-summary Gemini Summary 摘要`
- `cooking-video-summary YouTube 逐字稿`
- `cooking-video-summary 食譜文章`

也支援短別名：

- `cooking <網址>`
- `煮飯 <網址>`
- `做菜 <網址>`
- `料理 <網址>`

查找舊資料時，直接輸入短句：

- `列出目前所有清單`
- `幫我找「客家小炒」的作法`
- `找所有炒菜`
- `查「鮮魚炊飯」`

## 查找規則

預設查找順序：

1. `recipes/`
2. `artifacts/`

命中後會優先回傳原始 `.md` 內容，不會先幫你二次摘要。
如果沒有命中，會直接說明找不到，並建議改用更精確的關鍵字。

## 輸出位置

- 正式料理成品：repo 根目錄的 `recipes/`
- 任務回報：`artifacts/{issue-comment-id}/result.md`

## 詳細規則

完整欄位格式、分類規則與失敗處理，請看 [`SKILL.md`](SKILL.md)。