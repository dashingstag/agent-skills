"""Publish canonical skills/ to client discovery folders.

Default mode refreshes the in-repo discovery copies that Claude Code,
Codex and Copilot read directly from a checkout (.agents, .claude,
.github/skills). --check verifies they are current, for CI.
--install copies skills into personal skill folders in the home
directory so every client sees them in any project.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ".agent-skills-managed"

# In-repo discovery copies, committed so agents read them from a checkout.
REPO_TARGETS = [".agents/skills", ".github/skills", ".claude/skills"]

# Personal (home-directory) skill folders each client scans globally.
HOME_TARGETS = [
    ".agents/skills",   # agentskills.io standard, incl. Codex and Copilot
    ".claude/skills",   # Claude Code
    ".codex/skills",    # Codex
    ".copilot/skills",  # GitHub Copilot
]


def skill_dirs():
    return sorted(p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())


def sync_tree(source, target):
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    (target / MARKER).write_text(source.name + "\n", encoding="utf-8")


def tree_differs(source, target):
    if not target.is_dir():
        return True
    s_files = {p.relative_to(source) for p in source.rglob("*") if p.is_file()}
    t_files = {p.relative_to(target) for p in target.rglob("*") if p.is_file()} - {
        Path(MARKER)
    }
    if s_files != t_files:
        return True
    return any(
        (source / rel).read_bytes() != (target / rel).read_bytes() for rel in s_files
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if repo discovery copies are stale")
    parser.add_argument("--install", action="store_true",
                        help="also publish into home-directory skill folders")
    args = parser.parse_args()

    skills = skill_dirs()
    if not skills:
        sys.exit("no skills found under skills/")

    if args.check:
        stale = [
            f"{base}/{s.name}"
            for s in skills
            for base in REPO_TARGETS
            if tree_differs(s, ROOT / base / s.name)
        ]
        if stale:
            for path in stale:
                print(f"stale discovery copy: {path}")
            sys.exit("run tools/sync_skills.py to refresh")
        print(f"{len(skills) * len(REPO_TARGETS)} discovery copies verified")
        return

    bases = REPO_TARGETS[:]
    if args.install:
        bases += [str(Path.home() / t) for t in HOME_TARGETS]

    written = 0
    for skill in skills:
        for base in bases:
            target = Path(base) / skill.name
            if not target.is_absolute():
                target = ROOT / target
            if tree_differs(skill, target):
                sync_tree(skill, target)
                written += 1

    if args.install:
        # Only remove personal skills this repo installed before.
        canonical = {s.name for s in skills}
        for base in HOME_TARGETS:
            folder = Path.home() / base
            if not folder.is_dir():
                continue
            for child in folder.iterdir():
                if (
                    child.is_dir()
                    and child.name not in canonical
                    and (child / MARKER).is_file()
                ):
                    shutil.rmtree(child)
                    print(f"removed stale skill: {child}")

    print(
        f"{written} copies refreshed for {len(skills)} skills "
        f"({len(bases)} targets each)"
    )


if __name__ == "__main__":
    main()
