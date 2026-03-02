#!/usr/bin/env python
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def update_version(pyproject_path: Path, version: str) -> None:
    text = pyproject_path.read_text(encoding="utf-8")
    pattern = r'^version\s*=\s*"[^\"]*"'
    replacement = f'version = "{version}"'
    if not re.search(pattern, text, flags=re.MULTILINE):
        raise RuntimeError("version field not found in pyproject.toml")
    updated = re.sub(pattern, replacement, text, flags=re.MULTILINE, count=1)
    pyproject_path.write_text(updated, encoding="utf-8")


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload-only", action="store_true", help="Only upload existing dist files, skip build")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    if args.upload_only:
        dist_dir = root / "dist"
        dist_files = sorted(dist_dir.glob("clawos-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not dist_files:
            raise SystemExit("No dist files found. Run without --upload-only first.")
        latest = dist_files[0]
        print(f"Uploading {latest.name}")
        run(["twine", "upload", "--repository", "testpypi", "--config-file", ".pypirc", str(latest)])
        return

    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        raise SystemExit("pyproject.toml not found")

    now = datetime.now()
    version = f"{now:%y}{now.month}.{now.day}.{now:%H%M}"
    update_version(pyproject_path, version)
    print(f"Updated version to {version}")

    run([sys.executable, "-m", "build"])
    run(["twine", "upload", "--repository", "testpypi", "--config-file", ".pypirc", f"dist/clawos-{version}*"])


if __name__ == "__main__":
    main()
