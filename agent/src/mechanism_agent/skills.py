"""Bundled skills: discovery and loading.

Skills live in `agent/skills/<name>/SKILL.md` with a small front
matter block (name / description / roles). They are playbooks, not
code: the loader injects the ones matching an agent's role into that
agent's system prompt, so a fresh deployment gets the mechanism's
working habits along with its machinery.

Front matter is parsed with a deliberately tiny parser (no YAML
dependency); unknown fields are ignored, missing name/description
is an error — a skill that cannot say what it is for does not load.
"""
from __future__ import annotations

import os

DEFAULT_SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "skills")


def _parse_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("skill file has no front matter")
    head, _, body = text[3:].partition("\n---")
    meta: dict = {}
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "roles":
            meta["roles"] = [r.strip() for r in
                             value.strip("[]").split(",") if r.strip()]
        else:
            meta[key] = value
    if not meta.get("name") or not meta.get("description"):
        raise ValueError("skill front matter must carry name and description")
    return meta, body.strip()


def discover(skills_dir: str = DEFAULT_SKILLS_DIR) -> list[dict]:
    """All bundled skills as {name, description, roles, path, body}."""
    out = []
    if not os.path.isdir(skills_dir):
        return out
    for name in sorted(os.listdir(skills_dir)):
        path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            meta, body = _parse_front_matter(fh.read())
        meta.update(path=path, body=body)
        out.append(meta)
    return out


def for_role(role: str, skills_dir: str = DEFAULT_SKILLS_DIR) -> list[dict]:
    return [s for s in discover(skills_dir) if role in s.get("roles", [])]


def prompt_block(role: str, skills_dir: str = DEFAULT_SKILLS_DIR) -> str:
    """The skill texts for a role, ready to append to a system prompt."""
    blocks = [f"## Skill: {s['name']}\n\n{s['body']}" for s in for_role(role, skills_dir)]
    return "\n\n".join(blocks)
