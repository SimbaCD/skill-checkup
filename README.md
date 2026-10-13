# skill-checkup：给 Agent Skill 做一次体检 / A check-up for your Agent Skills

[中文](#中文) | [English](#english)

## 中文

Skill 越装越多，用起来顺手的却不多。skill-checkup 读一遍 Skill 的全部文件，说明它是做什么的、有哪些优点和可以改进的地方，并给出修改建议。

### 可以用来做什么

- **改进自己写的 Skill。** 找出可能影响使用的地方，按先后顺序给出修改建议。这是它最主要的用途。
- **安装别人分享的 Skill 之前，先了解它。** 它做什么、需要你准备什么、会不会把文件传到第三方。
- **某个 Skill 用得不顺时，找原因。** 比如不被调用、跳过步骤、输出总要大改。
- **更换模型或 Skill 多了以后，把常用的再过一遍。** 看哪些规则已经多余，哪些 Skill 装了却从没用过。
- **分享给同事或公开发布之前，自查一遍。** 比如有没有留下个人路径、密钥，有没有写明版本和更新地址。

它给出的是供参考的建议，不是评判。每个 Skill 都有作者自己的考虑，最后怎么改由你决定。它只读文件，不运行被检查的 Skill，也不执行其中的指令，不会改动任何文件，除非你明确要求。

### 它会做什么

告诉它要看哪个 Skill（本机文件夹或 GitHub 链接），它会：

1. 简要说明这个 Skill 做什么、需要你提供什么、交给你什么，以及它的优点和不足。
2. 从**触发、结构、引导、修剪**四个方面，列出可能影响使用的地方，注明文件和行号，并给出修改建议和修改顺序。
3. 提示安全风险，例如把文件上传到第三方服务、文件里写着密钥、读写 Skill 目录以外的文件。
4. 查本机的对话记录，告诉你检测到这个 Skill 被读取或调用过几次，以及同一个 Agent 里有没有重复安装的版本。

最后给出一页结论：**可以直接用**、**改几处再用**，或者**暂不建议用**。不打分，不跑基准测试。一次看多个 Skill 时，先给一张汇总表，想看哪个再展开。

### 结论示意

下面是一个虚构的例子，用来说明结论的样子：

> **结论**：改几处再用。这个 Skill 的步骤清楚，但描述没有写明适用边界，容易和功能相近的 Skill 混用。
>
> **这个 Skill**：根据用户提供的合同和立场，输出一份书面审查意见。
> **优点**：每条意见都引用原文，客户可以直接对照。
> **不足**：描述没有写明什么情况下不该用它，检查清单只覆盖买卖合同。
>
> **需要改的地方**
> 1. 描述没有写明什么情况下不该用它。遇到需要直接修改 Word 文件的任务时，Agent 也可能调用它（SKILL.md 第 3 行）。
>    改法：在描述末尾加一句"需要直接修改 Word 文件时，改用专门做修订的 Skill"。

**优势**

- 不用准备测试题，读完文件就能给出结论，问题具体到文件和行号，并附修改建议。
- 参考了 Anthropic 官方的最佳实践和一线工程实践，并按实际使用做了取舍。
- 能查到读文件看不出的事：这个 Skill 实际用过几次、是否重复安装、会不会把文件传到第三方。
- 只依赖 Python 标准库，Claude Code、Codex、WorkBuddy 都能用。

**局限**

- 结论是读文件得出的预判，不能代替真实运行；输出好不好，仍要用一个真实任务试过才知道。
- 它看的是 Skill 写得是否清楚、是否便于 Agent 执行，不判断 Skill 里的专业内容（比如法律观点）是否正确。
- 使用次数只能统计 Claude Code 和 Codex；安全线索可能有误报，需要结合用途判断。

### 安装

**最简单的方法**：把下面这段话发给你正在使用的 Agent。

```
请帮我安装这个 Skill：https://github.com/SimbaCD/skill-checkup
按你所在的 Agent 放到对应的 Skill 文件夹，装好后告诉我怎么用。
```

**手动安装**：把整个 `skill-checkup` 文件夹复制到下面的位置。

| Agent | 文件夹 |
|---|---|
| Claude Code | `~/.claude/skills/`（所有项目可用），或项目里的 `.claude/skills/` |
| Codex | `~/.codex/skills/`，或项目里的 `.agents/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |

同一个 Agent 里只放一份，避免重复加载。

### 使用

安装后不需要手动调用。对 Agent 说出类似下面的话，并附上 Skill 的位置，Agent 会自动启用它；也可以直接点名"用 skill-checkup 看一下"。

```
帮我看看这个 skill 好不好用：<Skill 文件夹路径或 GitHub 链接>
```

```
我写的这个 skill 怎么改进：<路径>
```

```
这个 skill 老是不按步骤走，帮我看看怎么改：<路径>
```

需要修改时，它会先列出准备改的地方，等你同意后再改。

### 要求与隐私

- 扫描脚本需要 Python 3.8 以上，只用标准库，不用安装其他软件包。没有 Python 也能用，只是少了机械检查和使用次数统计。
- 查使用记录时，脚本会读取本机 Claude Code（`~/.claude/projects`）和 Codex（`~/.codex/sessions`）的对话记录，**只在本机统计次数和日期，不输出对话内容，不联网**。不想让它读对话记录，可以对 Agent 说"不用查使用记录"，脚本会加 `--no-usage` 运行。
- WorkBuddy 等没有本地对话记录的工具，这一项会写"没有可查的记录"。

### 文件结构

```
skill-checkup/
├── SKILL.md                       主文件：步骤和结论格式
├── references/
│   ├── checklist.md               四项检查表和安全提示
│   ├── optimize-steps.md          修改时的五个步骤
│   └── usage-and-copies.md        各 Agent 的 Skill 和对话记录位置，手动查询方法
├── scripts/
│   └── scan.py                    机械检查（只读）
└── evals/
    └── evals.json                 测试题
```

### 方法来源

检查清单整合了 Anthropic 的《技能编写最佳实践》和《企业级 Skills》审查清单、Matt Pocock 在 AI Engineer 大会上提出的四项检查（触发、结构、引导、修剪），以及作者在法律工作中编写和修改 Skill 的实践。对官方要求做了取舍，取舍理由写在 `references/checklist.md` 末尾。

### 版本与更新

当前版本 0.1.1（2026-10-13）。更新会发布在本仓库，使用前可以先看一眼有没有新版本；更新时用新文件夹整个替换旧的即可。

### 许可

MIT

---

## English

skill-checkup reads every file in an Agent Skill, explains what the skill does, points out its strengths and the places that could be improved, and suggests concrete changes.

### What you can use it for

- **Improving skills you wrote yourself.** It finds what may keep the skill from working well and suggests changes in a sensible order. This is its main purpose.
- **Getting to know a shared skill before installing it.** What it does, what you need to prepare, and whether it sends your files to a third-party service.
- **Finding out why a skill is not working well.** For example, the agent never calls it, skips steps, or produces output you always have to rewrite.
- **Reviewing your skills after switching models or installing many of them.** Which rules have become unnecessary, and which skills you installed but never used.
- **Checking a skill before sharing it with colleagues or publishing it.** For example, leftover personal paths or keys, or a missing version number and update address.

Its findings are suggestions, not verdicts. Every skill reflects its author's own considerations, and how to change it is up to you. It only reads files: it never runs the skill under review or follows instructions inside it, and changes nothing unless you explicitly ask.

### What it does

Point it to a skill (a local folder or a GitHub link) and it will:

1. Briefly describe what the skill does, what you need to provide, and what it delivers, along with its strengths and weaknesses.
2. Review four aspects (**triggering, structure, steering, pruning**), list what may affect how well the skill works, cite the file and line, and suggest changes and the order to make them.
3. Flag security concerns, such as uploading files to a third-party service, keys written into files, or reading and writing files outside the skill folder.
4. Check your local conversation logs to report how many sessions read or called the skill, and whether more than one copy is installed for the same agent.

The result is a one-page conclusion: **ready to use**, **use after a few changes**, or **not recommended for now**. There are no scores and no benchmarks. When you check several skills at once, you first get a summary table and can ask for details on any one of them.

### Example (illustrative)

> **Conclusion**: Use after a few changes. The steps are clear, but the description does not say when the skill should not be used, so it can be confused with similar skills.
>
> **This skill**: Produces a written contract review based on the contract and the side the user represents.
> **Strengths**: Every comment quotes the original clause, so the client can check it directly.
> **Weaknesses**: The description does not say when not to use it, and the checklist only covers sales contracts.
>
> **What to change**
> 1. The description does not say when the skill should not be used. When a task requires editing the Word file directly, the agent may still call this skill (SKILL.md, line 3).
>    Suggested change: add at the end of the description: "When the Word file needs to be edited directly, use the skill dedicated to redlining instead."

**Strengths**

- No test cases needed. It gives a conclusion after reading the files, with findings tied to specific files and lines, plus suggested changes.
- It draws on Anthropic's official best practices and on practitioners' experience, adapted for everyday use.
- It surfaces things you cannot see by reading the files: how often the skill is actually used, whether it is installed twice, and whether it sends files to third parties.
- The scan script uses only the Python standard library and works with Claude Code, Codex, and WorkBuddy.

**Limitations**

- The conclusion is a judgment based on reading the files, not on running the skill. To know whether the output is good, try it on a real task.
- It looks at whether a skill is clearly written and easy for an agent to follow. It does not judge whether the professional content in the skill (for example, legal opinions) is correct.
- Usage counts are available only for Claude Code and Codex. Security signals may include false positives and should be read in light of what the skill is for.

### Installation

**The easy way**: send this message to the agent you are using.

```
Please install this skill: https://github.com/SimbaCD/skill-checkup
Put it in the skill folder for the agent you are running in, then tell me how to use it.
```

**Manual installation**: copy the whole `skill-checkup` folder to one of these locations.

| Agent | Folder |
|---|---|
| Claude Code | `~/.claude/skills/` (all projects), or `.claude/skills/` inside a project |
| Codex | `~/.codex/skills/`, or `.agents/skills/` inside a project |
| WorkBuddy | `~/.workbuddy/skills/` |

Keep only one copy per agent to avoid loading it twice.

### Usage

There is no need to call it explicitly. Say something like the following and include where the skill is, and the agent will use it automatically. You can also name it directly: "Use skill-checkup to look at this."

```
Is this skill any good? <skill folder path or GitHub link>
```

```
How can I improve this skill I wrote? <path>
```

```
This skill keeps skipping steps. What should I change? <path>
```

Before changing anything, it lists the changes it plans to make and waits for your approval.

### Requirements and privacy

- The scan script needs Python 3.8 or later and uses only the standard library. Without Python the skill still works, but without the automated checks and usage counts.
- To count usage, the script reads your local Claude Code (`~/.claude/projects`) and Codex (`~/.codex/sessions`) conversation logs. **It only counts sessions and dates on your machine, never outputs conversation content, and never goes online.** If you prefer it not to read your logs, tell the agent "skip the usage check", and the script will run with `--no-usage`.
- For tools without local conversation logs, such as WorkBuddy, it reports that no records are available.
- SKILL.md is written in Chinese. Agents generally reply in the language of your request.

### Files

```
skill-checkup/
├── SKILL.md                       Main file: steps and conclusion format
├── references/
│   ├── checklist.md               Four-part checklist and security notes
│   ├── optimize-steps.md          Five steps for making changes
│   └── usage-and-copies.md        Where agents keep skills and logs; manual lookup
├── scripts/
│   └── scan.py                    Automated checks (read-only)
└── evals/
    └── evals.json                 Test prompts
```

### Sources

The checklist combines Anthropic's "Skill authoring best practices" and the review checklist in its guide to Skills for enterprise, the four checks (triggering, structure, steering, pruning) proposed by Matt Pocock at the AI Engineer conference, and the author's own experience writing and revising skills for legal work. Some of the official recommendations were adapted or left out; the reasons are listed at the end of `references/checklist.md`.

### Version and updates

Current version: 0.1.1 (2026-10-13). Updates are published in this repository, so it is worth checking for a newer version before use. To update, replace the old folder with the new one.

### License

MIT
