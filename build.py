"""Builds data.js for the codebase guide from notes.py and a snapshot of the HDFC project.

Usage (from this folder):
  python build.py ../Hdfc-bank-custom-llm-pipeline-project      # snapshot origin/main of that repo, then build
  python build.py                                               # rebuild from the existing _snapshot folder
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import notes

HERE = Path(__file__).parent
SNAPSHOT = HERE / "_snapshot"
LANGS = {".py": "python", ".html": "xml", ".json": "json", ".yml": "yaml", ".yaml": "yaml", ".md": "markdown",
         ".csv": "plaintext", ".txt": "plaintext", ".example": "bash", "Dockerfile": "dockerfile",
         ".dockerignore": "plaintext", ".gitignore": "plaintext"}
MAX_CSV_LINES = 60  # human-review sheets are long; show the start, the full file is on GitHub


def take_snapshot(repo):
    """Export the committed origin/main of the project, so the guide never shows local or secret files."""
    if SNAPSHOT.exists():
        shutil.rmtree(SNAPSHOT)
    SNAPSHOT.mkdir()
    subprocess.run(["git", "-C", repo, "fetch", "-q"], check=True)
    archive = subprocess.run(["git", "-C", repo, "archive", "origin/main"], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(SNAPSHOT)], input=archive, check=True)
    commit = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "origin/main"], check=True,
                            capture_output=True, text=True).stdout.strip()
    (SNAPSHOT / ".commit").write_text(commit)


def language(path):
    return LANGS.get(path.name) or LANGS.get(path.suffix, "plaintext")


def find_line(lines, text):
    for number, line in enumerate(lines, start=1):
        if text in line:
            return number
    return None


def main():
    if len(sys.argv) > 1:
        take_snapshot(sys.argv[1])
    commit = (SNAPSHOT / ".commit").read_text().strip()
    paths = sorted(p for p in SNAPSHOT.rglob("*") if p.is_file() and p.name != ".commit")

    files, missing = [], []
    for path in paths:
        rel = path.relative_to(SNAPSHOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        truncated = path.suffix == ".csv" and len(lines) > MAX_CSV_LINES
        note = notes.FILES.get(rel, {})
        if not note:
            missing.append(rel)
        items = []
        for find, explanation in note.get("items", []):
            line = find_line(lines, find)
            if line is None:
                print(f"[WARN] {rel}: could not find {find!r}")
            items.append({"name": find.strip(" ={(").replace("@app.", "").replace("def ", "").replace("class ", ""),
                          "line": line, "text": explanation})
        files.append({
            "path": rel, "lang": language(path), "lines": len(lines),
            "code": "\n".join(lines[:MAX_CSV_LINES]) if truncated else text,
            "truncated": truncated,
            "summary": note.get("summary", ""), "role": note.get("role", ""),
            "points": note.get("points", []), "items": items,
            "questions": [{"q": q, "a": a} for q, a in note.get("questions", [])],
        })

    data = {
        "commit": commit,
        "repo": "https://github.com/pranatipradhanwork-alt/Hdfc-bank-custom-llm-pipeline-project",
        "pitch": notes.PITCH,
        "flow": [{"step": s, "file": f, "text": t} for s, f, t in notes.FLOW],
        "numbers": [{"label": l, "value": v} for l, v in notes.NUMBERS],
        "files": files,
        "qa": [{"topic": topic, "items": [{"q": q, "a": a} for q, a in items]} for topic, items in notes.QA],
        "glossary": [{"term": t, "text": d} for t, d in notes.GLOSSARY],
    }
    (HERE / "data.js").write_text("window.GUIDE = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"[OK] data.js: {len(files)} files, {sum(f['lines'] for f in files)} lines, commit {commit}")
    if missing:
        print(f"[INFO] files without notes: {missing}")


if __name__ == "__main__":
    main()
