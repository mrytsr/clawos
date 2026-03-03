import json
import re
import sys
from pathlib import Path


def flatten(value, prefix=""):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, p))
        return out
    return {prefix: value}


def load_lang_keys(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(flatten(data).keys())


def collect_referenced_keys(root: Path) -> set[str]:
    key_re = re.compile(r"I18n\.t\(\s*(['\"])(.+?)\1\s*\)")
    attr_res = [
        re.compile(r'data-i18n\s*=\s*"([^"]+)"'),
        re.compile(r'data-i18n-title\s*=\s*"([^"]+)"'),
        re.compile(r'data-i18n-aria-label\s*=\s*"([^"]+)"'),
        re.compile(r'data-i18n-placeholder\s*=\s*"([^"]+)"'),
    ]
    vue_t_re = re.compile(r"\bt\(\s*(['\"])(.+?)\1\s*\)")

    skip_names = {
        "vanilla-jsoneditor.js",
        "vue.esm-browser.js",
        "vue.global.prod.js",
        "vue-simple-context-menu.umd.js",
        "clipboard.min.js",
        "highlight.min.js",
        "tabulator.min.js",
        "xlsx.full.min.js",
    }

    ref_keys: set[str] = set()
    scan_dirs = [root / "templates", root / "static" / "js"]
    for d in scan_dirs:
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if path.is_dir():
                continue
            if path.name in skip_names:
                continue
            if path.name.endswith(".min.js"):
                continue
            if path.suffix.lower() not in (".js", ".html"):
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
            except Exception:
                pass

            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in key_re.finditer(text):
                ref_keys.add(m.group(2))
            for r in attr_res:
                for m in r.finditer(text):
                    ref_keys.add(m.group(1))
            if path.suffix.lower() == ".html":
                for m in vue_t_re.finditer(text):
                    k = m.group(2)
                    if "." in k:
                        ref_keys.add(k)

    return ref_keys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    lang_dir = root / "static" / "lang"
    langs = {"zh": lang_dir / "zh.json", "en": lang_dir / "en.json", "ja": lang_dir / "ja.json"}
    lang_keys = {code: load_lang_keys(p) for code, p in langs.items()}

    ref_keys = collect_referenced_keys(root)
    missing = {code: sorted(k for k in ref_keys if k not in keys) for code, keys in lang_keys.items()}

    any_missing = any(missing.values())
    print(f"Referenced keys: {len(ref_keys)}")
    for code in ("zh", "en", "ja"):
        miss = missing.get(code) or []
        print(f"{code} missing: {len(miss)}")
        for k in miss:
            print(f"  {k}")

    return 1 if any_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
