# -*- coding: utf-8 -*-
"""
Astra TV Extension Repository Manifest Builder
Scans providers/ folder and automatically generates repo.json and plugins.json.
Replicates Cloudstream Phisher repo architecture.
"""

import os
import re
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROVIDERS_DIR = os.path.join(BASE_DIR, "providers")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "github_user": "YOUR_GITHUB_USERNAME",
    "repo_name": "astra-tv-extensions",
    "branch": "main",
    "name": "Astra TV Extensions",
    "description": "Official Scrapers & Providers Repository for Astra TV"
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return DEFAULT_CONFIG


def parse_provider(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Match class block
    class_m = re.search(r"class\s+(\w+Provider|\w+):\s*(.*?)(?=\nclass\s|\Z)", content, re.DOTALL)
    class_body = class_m.group(2) if class_m else content

    # Name
    name_m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', class_body, re.MULTILINE)
    name = name_m.group(1) if name_m else os.path.splitext(os.path.basename(file_path))[0]

    # Language
    lang_m = re.search(r'^\s*lang\s*=\s*["\']([^"\']+)["\']', class_body, re.MULTILINE)
    lang = lang_m.group(1) if lang_m else "hi"

    # Supported Types
    types_m = re.search(r'^\s*supported_types\s*=\s*(\[[^\]]+\])', class_body, re.MULTILINE)
    tv_types = ["Movie", "TvSeries"]
    if types_m:
        try:
            tv_types = json.loads(types_m.group(1).replace("'", '"'))
        except Exception:
            pass

    # Version
    ver_m = re.search(r'^\s*version\s*=\s*(\d+)', class_body, re.MULTILINE)
    version = int(ver_m.group(1)) if ver_m else 1

    # Description (from module docstring)
    desc_m = re.search(r'"""(.*?)"""', content, re.DOTALL)
    description = ""
    if desc_m:
        lines = [l.strip() for l in desc_m.group(1).strip().split("\n") if l.strip()]
        description = lines[0] if lines else f"{name} Scraper"
    else:
        description = f"{name} Scraper for Astra TV"

    # Default icons
    icon_url = "https://raw.githubusercontent.com/recloudstream/extensions/master/img/default.png"
    if "hdhub" in name.lower():
        icon_url = "https://new10.hdhub4u.cl/favicon.ico"
    elif "desi" in name.lower():
        icon_url = "https://www.desi-serials.to/favicon.ico"

    return {
        "name": name,
        "internalName": name,
        "version": version,
        "description": description,
        "authors": ["Astra TV"],
        "tvTypes": tv_types,
        "language": lang,
        "iconUrl": icon_url,
        "fileSize": os.path.getsize(file_path),
        "status": 1
    }


def build():
    config = load_config()
    raw_base = f"https://raw.githubusercontent.com/{config['github_user']}/{config['repo_name']}/{config['branch']}"

    plugins = []
    if os.path.exists(PROVIDERS_DIR):
        for f in sorted(os.listdir(PROVIDERS_DIR)):
            if f.endswith(".py") and not f.startswith("__"):
                full_path = os.path.join(PROVIDERS_DIR, f)
                p_data = parse_provider(full_path)
                p_data["url"] = f"{raw_base}/providers/{f}"
                plugins.append(p_data)

    # 1. Write plugins.json
    plugins_file = os.path.join(BASE_DIR, "plugins.json")
    with open(plugins_file, "w", encoding="utf-8") as f:
        json.dump(plugins, f, indent=2, ensure_ascii=False)
    print(f"Generated {plugins_file} with {len(plugins)} scrapers:")
    for p in plugins:
        print(f" - {p['name']} (v{p['version']}, {', '.join(p['tvTypes'])})")

    # 2. Write repo.json
    repo_data = {
        "name": config["name"],
        "description": config["description"],
        "manifestVersion": 1,
        "pluginLists": [
            f"{raw_base}/plugins.json"
        ]
    }
    repo_file = os.path.join(BASE_DIR, "repo.json")
    with open(repo_file, "w", encoding="utf-8") as f:
        json.dump(repo_data, f, indent=2, ensure_ascii=False)
    print(f"Generated {repo_file}")


if __name__ == "__main__":
    build()
