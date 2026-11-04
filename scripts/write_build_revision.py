"""Bind Docker runtime metadata to local source without copying .git or credentials."""

import hashlib
import json
import subprocess
from pathlib import Path


def main():
    fingerprint = hashlib.sha256()
    paths = [
        p
        for directory in ["src", "migrations", "knowledge", "web/src"]
        for p in Path(directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    paths += [
        Path(p)
        for p in [
            "config/retail-tariffs-v2.json",
            "pyproject.toml",
            "uv.lock",
            "web/package.json",
            "web/pnpm-lock.yaml",
        ]
    ]
    for path in sorted(paths):
        fingerprint.update(str(path).encode())
        fingerprint.update(path.read_bytes())
    revision = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "source_sha256": fingerprint.hexdigest(),
        "worktree": "local uncommitted changes; no publication",
    }
    Path("config/build-revision.json").write_text(json.dumps(revision, indent=2))
    print(json.dumps(revision))


if __name__ == "__main__":
    main()
