# 使用记录和重复版本

扫描脚本会自动完成这两项。没有 Python 时，按下面的方法手动查。

## 各 Agent 从哪里读取 Skill

| Agent | 用户级文件夹 | 项目级文件夹 |
|---|---|---|
| Claude Code | `~/.claude/skills` | `<项目>/.claude/skills` |
| Codex | `~/.codex/skills`、`~/.agents/skills` | `<项目>/.agents/skills` |
| WorkBuddy | `~/.workbuddy/skills` | — |

同一个 Agent 读取的几个文件夹里有同名 Skill，就是重复版本。比较两份 SKILL.md 的内容是否相同；不同时，报告各自的位置和修改时间，不替用户判断哪份为准。

## 对话记录在哪里

| Agent | 位置 | 格式 |
|---|---|---|
| Claude Code | `~/.claude/projects/<项目>/*.jsonl` | 每行一条记录 |
| Codex | `~/.codex/sessions/<年>/<月>/<日>/*.jsonl` | 每行一条记录 |
| WorkBuddy 等 | 没有可查的记录 | 结论里写"没有可查的记录" |

## 什么算用过一次

以一次对话（一个 jsonl 文件）为单位，满足下面任一条件就算用过。只是打印、搜索或比较路径的命令不算：

- Claude Code：调用了 Skill 工具且参数是这个 Skill 的名字；用户输入了 `/名字`；工具调用读取了 `skills/名字/SKILL.md`。
- Codex：执行的命令或工具调用读取了 `skills/名字/SKILL.md`（Windows 上写作反斜杠，两种都算）。Codex 每次对话开头都会列出全部已装 Skill 的路径，这些不算。

一次对话里读取了六个以上不同 Skill 的，多半是在维护或检查 Skill，单独计数，不算作使用。这次体检本身也会被记成一次读取，报告时说明。

## 手动查询

PowerShell（把 `名字` 换成 Skill 的文件夹名）：

```powershell
# Claude Code：列出提到这个 Skill 的对话文件
Get-ChildItem $HOME\.claude\projects -Recurse -Filter *.jsonl | Select-String -Pattern 'skills[\\/]+名字[\\/]+SKILL\.md|"skill":"名字"' -List | Select-Object Path
# Codex
Get-ChildItem $HOME\.codex\sessions -Recurse -Filter *.jsonl | Select-String -Pattern 'skills[\\/]+名字[\\/]+SKILL\.md' -List | Select-Object Path
```

macOS 或 Linux（终端）：

```bash
grep -rlE 'skills/名字/SKILL\.md|"skill":"名字"' ~/.claude/projects --include='*.jsonl'
grep -rlE 'skills/名字/SKILL\.md' ~/.codex/sessions --include='*.jsonl'
```

手动查询无法排除 Codex 开头的路径列表，结果会偏多，报告时注明"手动查询，仅供参考"。
