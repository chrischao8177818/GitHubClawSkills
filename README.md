# GitHubClawSkills

這個 repo 是 Codex Skill 的集合頁。

## 技能清單

| 技能名稱 | 路徑 |
|---|---|
| `cooking-video-summary` | [`cooking-video-summary/SKILL.md`](./cooking-video-summary/SKILL.md) |

## 安裝方式

只需要替換 `<skill-path>`，其他部分都固定使用這個 repo。

```bash
install-skill-from-github.py --url https://github.com/chrischao8177818/GitHubClawSkills/tree/main/<skill-path>
```

```bash
install-skill-from-github.py --repo chrischao8177818/GitHubClawSkills --path <skill-path>
```

`<skill-path>` 代表技能資料夾名稱，例如 `cooking-video-summary`。

## 安裝範例

如果你要安裝 `cooking-video-summary`，可以直接這樣下：

```bash
install-skill-from-github.py --url https://github.com/chrischao8177818/GitHubClawSkills/tree/main/cooking-video-summary
```

或是：

```bash
install-skill-from-github.py --repo chrischao8177818/GitHubClawSkills --path cooking-video-summary
```

## 備註

- 技能說明請看各自資料夾內的 `SKILL.md`
- `LICENSE` 是授權檔
