#!/usr/bin/env python3
"""Skill 体检的机械检查。只读，不修改任何文件。

用法：python scan.py <Skill文件夹> [--project <项目文件夹>] [--no-usage]
需要 Python 3.8 以上，只用标准库。对话记录只在本机统计次数和日期，不输出对话内容。
"""
import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HOME = Path.home()
AGENT_DIRS = {
    "Claude Code": [HOME / ".claude" / "skills"],
    "Codex": [HOME / ".codex" / "skills", HOME / ".agents" / "skills"],
    "WorkBuddy": [HOME / ".workbuddy" / "skills"],
}
PROJECT_DIRS = {"Claude Code": [".claude/skills"], "Codex": [".agents/skills"]}
LOG_ROOTS = {"Claude Code": HOME / ".claude" / "projects", "Codex": HOME / ".codex" / "sessions"}
TEXT_EXT = {".md", ".txt", ".py", ".ps1", ".sh", ".js", ".mjs", ".ts", ".json",
            ".yaml", ".yml", ".toml", ".html", ".css", ".csv", ".xml", ".cmd", ".bat"}
SKIP_ORPHAN = re.compile(r"^(readme|license|changelog|contributing|notice)", re.I)
NEGATION = re.compile(r"不得|禁止|不要|严禁|切勿|不能|不可|不准|\bdo not\b|\bdon't\b|\bnever\b|\bmust not\b", re.I)
ROLE_LINE = re.compile(r"^\s*(你是一[个位名]|you are (an?|the) )", re.I)
POINTER = re.compile(r"(?:\.{1,2}/)*(?:[\w.-]+/)*[\w.\-\u4e00-\u9fff（）()]+\.(?:md|py|ps1|sh|js|mjs|json|ya?ml|txt|html|csv|svg|docx|xlsx)", re.I)
BARE_PATH = re.compile(r"\b(?:scripts|references|reference|templates|assets)/[\w.\-]+")  # 不带扩展名的写法
SHARED_SKIP = re.compile(r"^(license|licence|readme|changelog|contributing|notice)", re.I)  # 许可、说明文件相同属正常
STOPWORDS = set("a an the and or of to for in on with when whenever if any all this that these it its is are be by as from do does want wants ask asks include includes mention mentions user users use used using skill skills".split())
QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”")  # 引号里的多是举例，不算真实指向

# 以下数值来自 Anthropic《技能编写最佳实践》：name 不超过 64 字符，description 不超过 1024 字符，
# SKILL.md 正文最好少于 500 行，超过 100 行的参考文件应在开头放目录。
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
DESC_MAX, BODY_MAX, TOC_MIN = 1024, 500, 100
# 一次对话读取 6 个以上不同 Skill，多半是在维护或检查 Skill，不算正常使用。
MAINT_THRESHOLD = 6
# 少于 30 个字的句子重复出现很常见（如"见下表"），不计入重复段落。
DUP_MIN_CHARS = 30

# 安全线索：对应 Anthropic《企业级 Skills》审查清单中的风险指标。只列出位置，由人判断是否合理。
SECURITY = {
    "外部网址": re.compile(r"https?://[^\s)\]'\"`<>，。]+"),
    "联网调用": re.compile(r"\brequests\.(get|post|put)|urllib|httpx|aiohttp|\bcurl\b|\bwget\b|Invoke-(WebRequest|RestMethod)|\bfetch\(", re.I),
    "疑似硬编码密钥": re.compile(r"(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][^'\"\s]{8,}|\bsk-[A-Za-z0-9]{20,}", re.I),
    "删除或系统命令": re.compile(r"rm\s+-rf|Remove-Item|shutil\.rmtree|os\.remove|os\.unlink|\brmdir\b|\bdel\s+/|DROP\s+TABLE|subprocess|os\.system", re.I),
    "要求忽略规则或隐瞒": re.compile(r"ignore (all |any )?(previous|prior|above) instructions|do not (tell|inform) the user|忽略(之前|以上|上述|所有)的?(规则|指令|要求)|不要告诉用户|向用户隐瞒|对用户隐瞒", re.I),
    "Skill 目录以外的路径": re.compile(r"(?<![\w])(~[/\\]|\$HOME|%USERPROFILE%|[A-Za-z]:\\\\?[A-Za-z一-鿿_]{2,}|/Users/|/home/|\.\./)"),
}


def read_text(p):
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        try:
            return p.read_text(encoding="gbk")
        except Exception:
            return ""


def find_skill_md(folder):
    for n in ("SKILL.md", "skill.md", "Skill.md"):
        if (folder / n).exists():
            return folder / n
    return None


def frontmatter(text):
    """返回 (字段字典, 正文起始行号)。只处理简单的 YAML。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields, key, buf, block = {}, None, [], False
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            if key:
                fields[key] = " ".join(buf).strip()
            return fields, i + 1
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            if key:
                fields[key] = " ".join(buf).strip()
            key, val = m.group(1), m.group(2).strip()
            block = val in ("|", ">", "|-", ">-", "|+", ">+")
            buf = [] if block else [val.strip("'\"")]
        elif key:
            buf.append(line.strip())
    return fields, 0


def file_hash(p):
    try:
        return hashlib.md5(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def skill_files(folder):
    return [p for p in folder.rglob("*") if p.is_file() and ".git" not in p.parts
            and "__pycache__" not in p.parts]


def static_checks(folder, out):
    md = find_skill_md(folder)
    if not md:
        out.append("没有找到 SKILL.md。")
        return None
    text = read_text(md)
    fields, body_start = frontmatter(text)
    lines = text.splitlines()
    body = lines[body_start:]
    name, desc = fields.get("name", ""), fields.get("description", "")

    out.append("## 主文件")
    nchars = len(re.sub(r"\s", "", text))
    out.append(f"- {md.name}：{len(lines)} 行（正文 {len(body)} 行），{nchars} 字符")
    if len(body) > BODY_MAX:
        out.append(f"  ← 正文超过 {BODY_MAX} 行")
    out.append(f"- name：{name or '（缺失）'}")
    if name and (not NAME_RE.match(name) or re.search("anthropic|claude", name)):
        out.append("  ← 不符合命名规则：只能用小写字母、数字和连字符，不超过 64 字符，不能含 anthropic、claude")
    out.append(f"- description：{len(desc)} 字符" if desc else "- description：（缺失）")
    if desc:
        out.append(f"  {desc}")
        if len(desc) > DESC_MAX:
            out.append(f"  ← 超过 {DESC_MAX} 字符的上限")
        if re.search(r"<[^>]+>", desc):
            out.append("  ← 含 XML 标签，不符合要求")
        if re.search(r"我可以|我能|你可以用|I can help|You can use", desc, re.I):
            out.append("  ← 不是第三人称写法")
    # 版本与来源：frontmatter 的 version、metadata 字段，或 SKILL.md、README 里的仓库地址、版本说明
    readme = next((p for p in folder.iterdir() if p.is_file() and p.name.lower().startswith("readme")), None)
    meta_text = text + "\n" + (read_text(readme) if readme else "")
    clues = []
    if any(k in fields for k in ("version", "metadata", "source")):
        clues.append("frontmatter 有 " + "、".join(k for k in ("version", "metadata", "source") if k in fields))
    repo = re.search(r"https?://(?:github\.com|gitee\.com|gitlab\.com)/[\w.\-]+/[\w.\-]+", meta_text)
    if repo:
        clues.append("仓库地址 " + repo.group(0))
    ver = re.search(r"(?:版本|version)\s*[:：]?\s*v?\d+(?:\.\d+)+|\bv\d+\.\d+(?:\.\d+)?\b", meta_text, re.I)
    if ver:
        clues.append("写有版本号（" + ver.group(0).strip() + "）")
    if (folder / "CHANGELOG.md").exists():
        clues.append("有 CHANGELOG.md")
    out.append("- 版本与来源：" + ("；".join(clues) if clues else "未找到（没写来源地址、版本或更新记录）"))
    role = [body_start + i + 1 for i, l in enumerate(body[:20]) if ROLE_LINE.search(l)]
    if role:
        out.append(f"- 角色设定句：第 {', '.join(map(str, role))} 行")
    neg = [i + 1 for i, l in enumerate(lines) if NEGATION.search(l)]
    if neg:
        where = f"第 {neg[0]} 行" if len(neg) == 1 else f"分布在第 {neg[0]}–{neg[-1]} 行"
        out.append(f"- 否定句（不得、不要等）：{len(neg)} 处，{where}")

    # 指向关系：从 SKILL.md 出发，沿文本里提到的文件名找可到达的文件，记下层级
    files = skill_files(folder)
    rel = {p: p.relative_to(folder).as_posix() for p in files}
    by_name = {}
    for p, r in rel.items():
        by_name.setdefault(p.name.lower(), []).append(p)
        by_name.setdefault(r.lower(), []).append(p)
    depth, queue, missing, no_ext = {md: 0}, [md], [], []
    stems = {}
    for p, r in rel.items():
        stems.setdefault(r.rsplit(".", 1)[0].lower(), []).append(p)
    while queue:
        cur = queue.pop(0)
        if cur.suffix.lower() not in TEXT_EXT:
            continue
        for ln, line in enumerate(read_text(cur).splitlines(), start=1):
            for m in POINTER.finditer(QUOTED.sub("", line)):
                ref = m.group(0).lstrip("./")
                if any(c in ref for c in "<>{}*"):
                    continue
                cand = (cur.parent / m.group(0)).resolve()
                hits = [p for p in files if p.resolve() == cand] or by_name.get(ref.lower()) \
                    or by_name.get(Path(ref).name.lower())
                if hits:
                    for h in hits:
                        if h not in depth:
                            depth[h] = depth[cur] + 1
                            queue.append(h)
                elif "/" in ref and ref.split("/")[0] in ("references", "scripts", "templates",
                                                           "assets", "methods", "examples"):
                    missing.append(f"{rel.get(cur, cur.name)}:{ln} → {ref}")
            for m in BARE_PATH.finditer(QUOTED.sub("", line)):
                ref = m.group(0)
                if "." in ref.rsplit("/", 1)[-1] or ref.lower() in by_name:
                    continue
                hits = stems.get(ref.lower())
                if hits:
                    no_ext.append(f"{rel.get(cur, cur.name)}:{ln} → {ref}（实际文件 {rel[hits[0]]}）")
                    for h in hits:
                        if h not in depth:
                            depth[h] = depth[cur] + 1
                            queue.append(h)
    orphans = [rel[p] for p in files if p not in depth and not SKIP_ORPHAN.match(p.name)
               and p.suffix.lower() in TEXT_EXT and p.parts[-2] not in ("evals", "tests", "agents")
               and len(p.relative_to(folder).parts) > 1]
    nested = [f"{rel[p]}（第 {d} 层）" for p, d in depth.items() if d >= 2 and p.suffix.lower() == ".md"]
    no_toc = []
    for p in depth:
        if p is md or p.suffix.lower() != ".md":
            continue
        t = read_text(p).splitlines()
        if len(t) > TOC_MIN and not re.search(r"目录|contents", "\n".join(t[:15]), re.I):
            no_toc.append(f"{rel[p]}（{len(t)} 行）")
    out.append("\n## 文件与指向")
    out.append(f"- 共 {len(files)} 个文件")
    out.append("- 指向不存在的文件：" + ("；".join(missing[:10]) if missing else "无"))
    out.append("- 未被指到的文件：" + ("、".join(sorted(orphans)[:15]) if orphans else "无"))
    if no_ext:
        out.append("- 引用漏写扩展名（照写运行会找不到文件）：" + "；".join(no_ext[:10]))
    out.append("- 只能经由其他参考文件到达（二级引用）：" + ("、".join(sorted(nested)[:10]) if nested else "无"))
    out.append(f"- 超过 {TOC_MIN} 行、开头没有目录的参考文件：" + ("、".join(no_toc) if no_toc else "无"))

    # 重复段落：同一句在 Skill 内出现两次以上（跳过代码块）
    seen = {}
    for p in files:
        if p.suffix.lower() != ".md":
            continue
        in_code = False
        for ln, line in enumerate(read_text(p).splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            norm = re.sub(r"^[\s>*#\-\d.、|]+", "", line).strip()
            if not in_code and len(norm) >= DUP_MIN_CHARS:
                seen.setdefault(norm, []).append(f"{rel[p]}:{ln}")
    dups = [(k, v) for k, v in seen.items() if len(v) > 1]
    out.append("\n## 重复段落")
    if dups:
        for k, v in sorted(dups, key=lambda x: -len(x[1]))[:8]:
            out.append(f"- 出现 {len(v)} 次（{'，'.join(v[:4])}）：{k[:60]}")
    else:
        out.append("- 无")

    # 安全线索
    hits = {k: [] for k in SECURITY}
    for p in files:
        if p.suffix.lower() not in TEXT_EXT:
            continue
        for ln, line in enumerate(read_text(p).splitlines(), start=1):
            for k, rx in SECURITY.items():
                m = rx.search(line)
                if m:
                    hits[k].append(f"{rel[p]}:{ln}（{m.group(0)[:40]}）")
    out.append("\n## 安全线索（只列位置，是否合理需结合用途判断）")
    found = False
    for k, v in hits.items():
        if v:
            found = True
            more = f" 等 {len(v)} 处" if len(v) > 6 else ""
            out.append(f"- {k}：{'；'.join(v[:6])}{more}")
    if not found:
        out.append("- 无")
    return {"md": md, "desc": desc, "files": files, "name": name or folder.name}


def agent_dirs(project):
    dirs = {a: list(ds) for a, ds in AGENT_DIRS.items()}
    if project:
        for a, subs in PROJECT_DIRS.items():
            dirs[a] += [Path(project) / s for s in subs]
    return dirs


def copies_and_neighbors(folder, info, project, out):
    name = folder.name
    target_md_hash = file_hash(info["md"])
    out.append("\n## 本机安装的版本")
    any_copy = False
    for agent, ds in agent_dirs(project).items():
        found = []
        for d in ds:
            c = d / name
            md = find_skill_md(c) if c.is_dir() else None
            if md:
                mt = datetime.fromtimestamp(max(p.stat().st_mtime for p in skill_files(c))).strftime("%Y-%m-%d")
                same = "与被检查的版本相同" if file_hash(md) == target_md_hash else "SKILL.md 内容不同"
                found.append(f"{c}（{mt}，{same}）")
        if found:
            any_copy = True
            flag = "  ← 同一 Agent 里有多份" if len(found) > 1 else ""
            out.append(f"- {agent}：{'；'.join(found)}{flag}")
    if not any_copy:
        out.append("- 各 Agent 的 Skill 文件夹里都没有同名 Skill")

    # 与其他 Skill 完全相同的文件、描述相近的 Skill
    others = {}
    roots = {folder.parent.resolve()} | {d.resolve() for ds in agent_dirs(project).values() for d in ds if d.exists()}
    for r in roots:
        for c in r.iterdir() if r.exists() else []:
            if c.is_dir() and c.name != name and find_skill_md(c):
                others.setdefault(c.name, c)
    hashes = {}
    for p in info["files"]:
        if p.stat().st_size > 200 and not SHARED_SKIP.match(p.name):
            hashes[(p.name, file_hash(p))] = p.relative_to(folder).as_posix()
    shared = {}
    for oname, c in others.items():
        for p in skill_files(c):
            if any(k[0] == p.name for k in hashes):
                h = file_hash(p)
                if (p.name, h) in hashes:
                    shared.setdefault(hashes[(p.name, h)], set()).add(oname)
    out.append("\n## 与其他 Skill 相同的文件")
    if shared:
        for f, names in shared.items():
            out.append(f"- {f}：另有 {len(names)} 个 Skill 中有完全相同的文件（{'、'.join(sorted(names))}）")
    else:
        out.append("- 无")

    def tokens(t):
        return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", t.lower())

    def meaningful(span):
        han = sum(1 for w in span if re.match(r"[\u4e00-\u9fff]", w))
        words = [w for w in span if not re.match(r"[\u4e00-\u9fff]", w)]
        content = [w for w in words if w not in STOPWORDS and w not in name_words]
        return han >= 4 or (han == 0 and len(content) >= 2) or (han >= 2 and len(content) >= 1)

    def shared_spans(a, b):
        bset = {tuple(b[i:i + n]) for n in range(2, 13) for i in range(len(b) - n + 1)}
        spans, i = [], 0
        while i < len(a) - 1:
            j = i + 2
            if tuple(a[i:j]) in bset:
                while j < len(a) and j - i < 12 and tuple(a[i:j + 1]) in bset:
                    j += 1
                if meaningful(a[i:j]):
                    spans.append(a[i:j])
                i = j
            else:
                i += 1
        return spans

    def show(span):
        return re.sub(r"(?<=[a-z0-9]) (?=[\u4e00-\u9fff])|(?<=[\u4e00-\u9fff]) (?=[a-z0-9])|(?<=[\u4e00-\u9fff]) (?=[\u4e00-\u9fff])", "", " ".join(span))
    name_words = set(re.findall(r"[a-z0-9]+", " ".join(list(others) + [name]).lower()))
    a = tokens(info["desc"])
    sims = []
    for oname, c in others.items():
        f, _ = frontmatter(read_text(find_skill_md(c)))
        spans = shared_spans(a, tokens(f.get("description", "")))
        if a and spans:
            cover = sum(map(len, spans)) / len(a)
            uniq = sorted({show(sp) for sp in spans}, key=len, reverse=True)
            sims.append((cover, oname, uniq))
    sims = [x for x in sorted(sims, reverse=True) if x[0] >= 0.1 or len(x[2]) >= 3][:4]
    out.append("\n## 描述相近的其他 Skill（列出两段描述里共有的片段）")
    if sims:
        for cover, oname, spans in sims:
            out.append(f"- {oname}（共有片段占本描述 {cover:.0%}）：{' | '.join(spans[:8])}")
    else:
        out.append("- 无")


def usage(name, out):
    nb = re.escape(name.encode("utf-8"))
    path_any = re.compile(rb"skills(?:/|\\+)([\w.\-]+)(?:/|\\+)SKILL\.md")
    claude_extra = re.compile(rb'"skill":"(?:[^"]*:)?' + nb + rb'"|<command-name>/?(?:[^<]*:)?' + nb + rb"</command-name>")
    ts = re.compile(rb'"timestamp":"(\d{4}-\d{2}-\d{2})')
    out.append("\n## 使用记录")
    for agent, root in LOG_ROOTS.items():
        if not root.exists():
            out.append(f"- {agent}：没有找到对话记录（{root}）")
            continue
        sessions = {}
        for f in root.rglob("*.jsonl"):
            try:
                data = f.read_bytes()
            except OSError:
                continue
            if name.encode("utf-8") not in data:
                continue
            key = f.parent.parent.name if f.parent.name == "subagents" else f.stem
            hit_dates, all_skills = [], set()

            def tool_line(start):
                end = data.find(b"\n", start)
                line = data[data.rfind(b"\n", 0, start) + 1: end if end != -1 else len(data)]
                if agent == "Claude Code":
                    ok = b'"tool_use"' in line or b"<command-name>" in line
                else:
                    ok = (b'"session_meta"' not in line and b'"turn_context"' not in line
                          and b'"role":"developer"' not in line and b'"role":"system"' not in line
                          and (b"function_call" in line or b"CommandExecution" in line
                               or b"local_shell_call" in line or b"custom_tool_call" in line
                               or b"exec_command" in line))
                return ok, line
            for m in path_any.finditer(data):
                ok, line = tool_line(m.start())
                if ok:
                    all_skills.add(m.group(1).lower())
                    if m.group(1).lower() == name.lower().encode("utf-8"):
                        d = ts.search(line)
                        hit_dates.append(d.group(1).decode() if d else "")
            if agent == "Claude Code":
                for m in claude_extra.finditer(data):
                    ok, line = tool_line(m.start())
                    if ok:
                        d = ts.search(line)
                        hit_dates.append(d.group(1).decode() if d else "")
            if hit_dates:
                s = sessions.setdefault(key, {"dates": [], "skills": set()})
                s["dates"] += [d for d in hit_dates if d]
                s["skills"] |= all_skills
        used = {k: v for k, v in sessions.items() if len(v["skills"]) < MAINT_THRESHOLD}
        maint = len(sessions) - len(used)
        dates = sorted(d for v in used.values() for d in v["dates"])
        line = f"- {agent}：{len(used)} 次对话中使用"
        if dates:
            line += f"，最早 {dates[0]}，最近 {dates[-1]}"
        if maint:
            line += f"；另有 {maint} 次对话属于批量读取多个 Skill（维护或检查），未计入"
        out.append(line)
    out.append("- WorkBuddy 等其他工具：没有可查的记录")
    out.append("- 注：本次体检读取这个 Skill，也可能被记为一次使用")


def main():
    ap = argparse.ArgumentParser(description="Skill 体检的机械检查（只读）")
    ap.add_argument("skill", help="Skill 文件夹路径")
    ap.add_argument("--project", help="项目文件夹，用于检查项目级的 Skill 文件夹")
    ap.add_argument("--no-usage", action="store_true", help="跳过对话记录检索")
    a = ap.parse_args()
    folder = Path(a.skill).expanduser().resolve()
    if folder.is_file():
        folder = folder.parent
    out = [f"# 扫描结果：{folder.name}", f"位置：{folder}", ""]
    info = static_checks(folder, out)
    if info:
        copies_and_neighbors(folder, info, a.project, out)
        if not a.no_usage:
            usage(folder.name, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
