#!/usr/bin/env python
import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload-only", action="store_true", help="Only upload existing dist files, skip build")
    parser.add_argument("--release", action="store_true", help="Upload to正式 pypi instead of testpypi")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    # 构建 twine 命令参数
    # twine 的子命令必须紧跟在 "twine" 后面；子命令选项应放在子命令之后
    twine_base = ["twine", "upload"]
    if not args.release:
        twine_base += ["--repository", "testpypi"]

    dist_dir = root / "dist"

    preferred_version: Optional[str] = None
    if not args.upload_only:
        pyproject_path = root / "pyproject.toml"
        if not pyproject_path.exists():
            raise SystemExit("pyproject.toml not found")

        now = datetime.now()
        preferred_version = f"{now:%y}{now.month}.{now.day}.{now:%H%M}"
        text = pyproject_path.read_text(encoding="utf-8")
        pattern = r'^version\s*=\s*"[^\"]*"'
        replacement = f'version = "{preferred_version}"'
        if not re.search(pattern, text, flags=re.MULTILINE):
            raise RuntimeError("version field not found in pyproject.toml")
        updated = re.sub(pattern, replacement, text, flags=re.MULTILINE, count=1)
        pyproject_path.write_text(updated, encoding="utf-8")
        print(f"Updated version to {preferred_version}")

        result = subprocess.run([sys.executable, "-m", "build"], check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    files = [p for p in dist_dir.glob("clawos-*") if p.is_file()]
    if not files:
        raise SystemExit("No dist files found. Build first or check dist/ directory.")

    by_version: dict[str, list[Path]] = {}
    for p in files:
        name = p.name
        v: Optional[str] = None
        if name.startswith("clawos-"):
            if name.endswith(".tar.gz"):
                base = name[: -len(".tar.gz")]
                m = re.match(r"^clawos-(.+)$", base)
                v = m.group(1) if m else None
            elif name.endswith(".zip"):
                base = name[: -len(".zip")]
                m = re.match(r"^clawos-(.+)$", base)
                v = m.group(1) if m else None
            elif name.endswith(".whl"):
                m = re.match(r"^clawos-([^-]+)-", name)
                v = m.group(1) if m else None

        if not v:
            continue
        by_version.setdefault(v, []).append(p)

    if not by_version:
        raise SystemExit("No recognizable dist artifacts found for project 'clawos'.")

    if preferred_version and preferred_version in by_version:
        picked_version = preferred_version
    else:
        picked_version = max(by_version.keys(), key=lambda v: max(p.stat().st_mtime for p in by_version[v]))

    upload_files = sorted(by_version[picked_version], key=lambda p: (p.suffix != ".whl", p.name))

    print(f"Uploading version {picked_version}:")
    for p in upload_files:
        print(f"  - {p.name}")
    result = subprocess.run(twine_base + [str(p) for p in upload_files], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
