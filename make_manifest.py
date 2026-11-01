# -*- coding: utf-8 -*-
"""
Astra TV Extension Repository Manifest & .atx Builder
Packages scrapers into secure .atx (Astra TV Extension) packages inside builds/
and generates plugins.json and repo.json with SHA-256 integrity verification.
"""

import os
import re
import json
import zipfile
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROVIDERS_DIR = os.path.join(BASE_DIR, "providers")
BUILDS_DIR = os.path.join(BASE_DIR, "builds")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "github_user": "Dangerous-Taabar",
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


def parse_provider_metadata(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Match class block
    class_m = re.search(r"class\s+(\w+Provider|\w+)\s*(\([^\)]*\))?:", content)
    class_name = class_m.group(1) if class_m else "Provider"

    # Name
    name_m = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    name = name_m.group(1) if name_m else os.path.splitext(os.path.basename(file_path))[0]

    # Language
    lang_m = re.search(r'^\s*lang\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    lang = lang_m.group(1) if lang_m else "hi"

    # Supported Types
    types_m = re.search(r'^\s*supported_types\s*=\s*(\[[^\]]+\])', content, re.MULTILINE)
    tv_types = ["Movie", "TvSeries"]
    if types_m:
        try:
            tv_types = json.loads(types_m.group(1).replace("'", '"'))
        except Exception:
            pass

    # Version
    ver_m = re.search(r'^\s*version\s*=\s*(\d+)', content, re.MULTILINE)
    version = int(ver_m.group(1)) if ver_m else 1

    # Description (from module docstring)
    desc_m = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if desc_m:
        lines = [l.strip() for l in desc_m.group(1).strip().split("\n") if l.strip()]
        description = lines[0] if lines else f"{name} Scraper"
    else:
        description = f"{name} Scraper for Astra TV"

    # Icon
    icon_url = "https://raw.githubusercontent.com/recloudstream/extensions/master/img/default.png"
    lower_name = name.lower()
    if "hdhub" in lower_name:
        icon_url = "https://new10.hdhub4u.cl/favicon.ico"
    elif "desi" in lower_name:
        icon_url = "https://www.desi-serials.to/favicon.ico"
    elif "anime" in lower_name:
        icon_url = "https://www.animedubhindi.link/favicon.ico"
    elif "cricfy" in lower_name:
        icon_url = "https://raw.githubusercontent.com/recloudstream/extensions/master/img/live.png"
    elif "livxow" in lower_name:
        icon_url = "https://www.livxow.site/logo.jpg"

    return {
        "name": name,
        "internalName": name,
        "className": class_name,
        "version": version,
        "description": description,
        "authors": ["Astra TV"],
        "tvTypes": tv_types,
        "language": lang,
        "iconUrl": icon_url
    }


def package_atx(file_path, meta):
    """
    Builds a .atx ZIP archive containing:
      - manifest.json
      - provider.py
    """
    os.makedirs(BUILDS_DIR, exist_ok=True)
    atx_filename = f"{meta['internalName']}.atx"
    atx_path = os.path.join(BUILDS_DIR, atx_filename)

    manifest_data = {
        "name": meta["name"],
        "internalName": meta["internalName"],
        "className": meta["className"],
        "version": meta["version"],
        "description": meta["description"],
        "authors": meta["authors"],
        "tvTypes": meta["tvTypes"],
        "language": meta["language"],
        "iconUrl": meta["iconUrl"],
        "entrypoint": "provider.py"
    }

    with open(file_path, "rb") as pf:
        provider_code = pf.read()

    with zipfile.ZipFile(atx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest_data, indent=2, ensure_ascii=False))
        zf.writestr("provider.py", provider_code)

    file_size = os.path.getsize(atx_path)
    with open(atx_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    return atx_path, file_size, sha256


def build():
    config = load_config()
    raw_base = f"https://raw.githubusercontent.com/{config['github_user']}/{config['repo_name']}/{config['branch']}"

    plugins = []
    if os.path.exists(PROVIDERS_DIR):
        for f in sorted(os.listdir(PROVIDERS_DIR)):
            if f.endswith(".py") and not f.startswith("__"):
                full_path = os.path.join(PROVIDERS_DIR, f)
                meta = parse_provider_metadata(full_path)
                
                # Package into .atx
                atx_path, file_size, sha256 = package_atx(full_path, meta)
                
                plugin_entry = {
                    "name": meta["name"],
                    "internalName": meta["internalName"],
                    "version": meta["version"],
                    "description": meta["description"],
                    "authors": meta["authors"],
                    "tvTypes": meta["tvTypes"],
                    "language": meta["language"],
                    "iconUrl": meta["iconUrl"],
                    "url": f"{raw_base}/builds/{meta['internalName']}.atx",
                    "fileSize": file_size,
                    "sha256": sha256,
                    "status": 1
                }
                plugins.append(plugin_entry)

    # 1. Write plugins.json
    plugins_file = os.path.join(BASE_DIR, "plugins.json")
    with open(plugins_file, "w", encoding="utf-8") as f:
        json.dump(plugins, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {plugins_file} with {len(plugins)} extensions:")
    for p in plugins:
        print(f" - {p['name']}.atx ({p['fileSize']} bytes, SHA256: {p['sha256'][:10]}..., {', '.join(p['tvTypes'])})")

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
