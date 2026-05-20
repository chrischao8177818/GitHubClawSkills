# GitHubClawSkills

這個 repo 提供可直接安裝的 Codex Skill，主要用來整理料理影片、逐字稿、食譜文章與相關摘要內容。

## 目前提供的 Skill

| 技能名稱 | 技能說明 |
|---|---|
| `cooking-video-summary` | 先呼叫 `gemini-summary` 取得摘要，再整理成標準食譜 Markdown。支援料理網址、PDF、短別名與查找舊資料。 |

## 這個 Skill 可以做什麼

- 整理 YouTube、Shorts、Reels、食譜文章或 PDF
- 先摘要，再輸出成可重用的食譜內容
- 查找已整理好的料理資料
- 支援短別名：`cooking`、`煮飯`、`做菜`、`料理`

## 安裝方式

下列兩種方式擇一即可：

```bash
install-skill-from-github.py --url https://github.com/chrischao8177818/GitHubClawSkills/tree/main/cooking-video-summary
```

```bash
install-skill-from-github.py --repo chrischao8177818/GitHubClawSkills --path cooking-video-summary
```

## 使用範例

```text
cooking-video-summary https://www.youtube.com/watch?v=HWBpr2MH_bE
```

或直接使用替代關鍵字：

```text
煮飯 https://www.youtube.com/watch?v=HWBpr2MH_bE
```

## 補充說明

- `cooking-video-summary/`：實際可安裝的 Skill 套件
- `LICENSE`：授權檔