# -*- coding: utf-8 -*-
"""
Cricfy Provider for Astra TV
Ported from CloudStream com.cncverse.CricifyProvider (Kotlin).
Provides Live Sports, Cricket, and TV channels with Firebase remote config and AES decryption.
"""

import json
import base64
import urllib.request
import urllib.parse
import ssl
import re
import uuid

try:
    from resources.lib.aes import AES
except ImportError:
    try:
        from aes import AES
    except ImportError:
        AES = None

# Firebase Remote Config credentials from Cricfy APK
FIREBASE_API_KEY = "AIzaSyAh9jkEU0E_UYxH0m_BKAt-uUSTiTPqhb8"
FIREBASE_APP_ID = "1:963020218535:android:47ec53252c64fb3c9c7b82"
FIREBASE_PROJECT_NUMBER = "963020218535"
PACKAGE_NAME = "com.cricfy.tv"

# AES Keys for cats.txt decryption
KEY1 = (bytes.fromhex("3368487a78594167534749382f68616d"), bytes.fromhex("557143766b766a656345497a38343256"))
KEY2 = (bytes.fromhex("4d7165594743543441594b6f484b7254"), bytes.fromhex("6f484b725451755078387a6c386f4a2b"))
KEYS = [KEY1, KEY2]

DEFAULT_BASE_URL = "https://cfymarkscanjiostar80.top"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch_url(url, headers=None, data=None, timeout=6):
    if not url or not url.startswith("http"):
        return None
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception:
        return None


def decrypt_data(encrypted_base64):
    """Decrypts cats.txt using CryptoUtils logic."""
    if not encrypted_base64 or not AES:
        return None
    clean = encrypted_base64.replace("\n", "").replace("\r", "").replace(" ", "").replace("\t", "").strip()
    try:
        ciphertext = base64.b64decode(clean)
    except Exception:
        return None

    for key, iv in KEYS:
        try:
            aes = AES(key, iv)
            decrypted_bytes = aes.decrypt(ciphertext)
            if decrypted_bytes:
                pad_len = decrypted_bytes[-1]
                if 0 < pad_len <= 16:
                    decrypted_bytes = decrypted_bytes[:-pad_len]
                result = decrypted_bytes.decode('utf-8', errors='ignore')
                if result.startswith("{") or result.startswith("[") or "http" in result:
                    return result
        except Exception:
            pass
    return None


def decrypt_content(content):
    """Custom Cricify M3U decryptor from Cricify.kt (decryptContent)."""
    if not content or not AES:
        return content
    try:
        if content.startswith("#EXTM3U") or content.startswith("#EXTINF") or content.startswith("#KODIPROP"):
            return content

        trimmed = content.strip()
        if len(trimmed) < 79:
            return trimmed

        part1 = trimmed[0:10]
        part2 = trimmed[34:len(trimmed) - 54]
        part3 = trimmed[len(trimmed) - 10:]

        encrypted_data = part1 + part2 + part3
        iv_base64 = trimmed[10:34]
        key_base64 = trimmed[len(trimmed) - 54:len(trimmed) - 10]

        iv = base64.b64decode(iv_base64)
        key = base64.b64decode(key_base64)
        encrypted = base64.b64decode(encrypted_data)

        aes = AES(key, iv)
        decrypted_bytes = aes.decrypt(encrypted)
        if decrypted_bytes:
            pad_len = decrypted_bytes[-1]
            if 0 < pad_len <= 16:
                decrypted_bytes = decrypted_bytes[:-pad_len]
            return decrypted_bytes.decode('utf-8', errors='ignore')
    except Exception:
        pass
    return content


def get_base_url():
    """Fetches base URL from Firebase Remote Config, falls back to default."""
    url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{FIREBASE_PROJECT_NUMBER}/namespaces/firebase:fetch"
    app_instance_id = str(uuid.uuid4()).replace("-", "")
    payload = {
        "appInstanceId": app_instance_id,
        "appInstanceIdToken": "",
        "appId": FIREBASE_APP_ID,
        "countryCode": "US",
        "languageCode": "en-US",
        "platformVersion": "30",
        "timeZone": "UTC",
        "appVersion": "5.0",
        "appBuild": "50",
        "packageName": PACKAGE_NAME,
        "sdkVersion": "22.1.0",
        "analyticsUserProperties": {}
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Android-Package": PACKAGE_NAME,
        "X-Goog-Api-Key": FIREBASE_API_KEY,
        "X-Google-GFE-Can-Retry": "yes"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=6) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            entries = res_json.get("entries", {})
            api_url = entries.get("cric_api2") or entries.get("cric_api1")
            if api_url:
                return api_url.rstrip("/")
    except Exception:
        pass
    return DEFAULT_BASE_URL


def parse_m3u(text):
    """Parses M3U playlist extracting channels, headers, and DRM info."""
    channels = []
    current = {}
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            try:
                info_part, title = line.split(",", 1)
                current["title"] = title.strip()
                logo_match = re.search(r'tvg-logo="([^"]+)"', info_part)
                if logo_match:
                    current["poster"] = logo_match.group(1)
                group_match = re.search(r'group-title="([^"]+)"', info_part)
                if group_match:
                    current["group"] = group_match.group(1)
            except Exception:
                current["title"] = line
            current["headers"] = {}
            current["drm"] = {}
        elif line.startswith("#EXTVLCOPT:"):
            opt = line.replace("#EXTVLCOPT:", "").strip()
            if "=" in opt:
                k, v = opt.split("=", 1)
                k = k.lower().strip()
                if "user-agent" in k:
                    current.setdefault("headers", {})["User-Agent"] = v.strip()
                elif "referer" in k or "referrer" in k:
                    current.setdefault("headers", {})["Referer"] = v.strip()
                elif "cookie" in k:
                    current.setdefault("headers", {})["Cookie"] = v.strip()
        elif line.startswith("#EXTHTTP:"):
            try:
                headers_json = line.replace("#EXTHTTP:", "").strip()
                headers = json.loads(headers_json)
                if isinstance(headers, dict):
                    current.setdefault("headers", {}).update(headers)
            except Exception:
                pass
        elif line.startswith("#KODIPROP:"):
            prop = line.replace("#KODIPROP:", "").strip()
            if "license_key=" in prop:
                current.setdefault("drm", {})["license_key"] = prop.split("license_key=", 1)[1].strip()
            elif "manifest_type=" in prop:
                current.setdefault("drm", {})["manifest_type"] = prop.split("manifest_type=", 1)[1].strip()
        elif not line.startswith("#"):
            if current.get("title"):
                current["url"] = line
                channels.append(current)
                current = {}
    return channels


class CricfyProvider:
    """Cricfy Live Sports & TV Provider for Astra TV."""
    name = "Cricfy"
    lang = "en"
    supported_types = ["LiveStream", "Live"]
    version = 1

    def __init__(self):
        self.base_url = None

    def get_categories(self):
        """Returns list of (label, path) tuples matching Astra TV architecture."""
        if not self.base_url:
            self.base_url = get_base_url()

        cats_url = f"{self.base_url}/cats.txt"
        res = fetch_url(cats_url, timeout=6)

        categories = []
        if res:
            decrypted = decrypt_data(res)
            if decrypted:
                try:
                    data = json.loads(decrypted)
                    for item in data:
                        title = (item.get("title") or "").strip()
                        cat_link = (item.get("catLink") or "").strip()
                        # Only include valid http links
                        if title and cat_link.startswith("http") and cat_link.lower() != "null":
                            categories.append((title, cat_link))
                except Exception:
                    pass

        if categories:
            return categories

        # Fallback sports playlists if remote API fails
        return [
            ("India TV & Sports Streams", "https://iptv-org.github.io/iptv/languages/hin.m3u"),
            ("FanCode Live Sports", "https://raw.githubusercontent.com/doctor-8trange/zyphx8/refs/heads/main/data/fancode.m3u"),
            ("SonyLiv Live Events", "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"),
            ("Pirates TV Sports", "https://raw.githubusercontent.com/FunctionError/PiratesTv/refs/heads/main/combined_playlist.m3u"),
            ("Samsung TV Plus", "https://alex4528.site/playlist/samsungtv.m3u"),
        ]

    def get_items(self, path="", page=1):
        """Fetches and parses channels from a specific M3U playlist path."""
        if not path or not path.startswith("http"):
            return []

        res = fetch_url(path, timeout=7)
        if not res:
            return []

        decrypted = decrypt_content(res)
        channels = parse_m3u(decrypted)

        items = []
        default_logo = "https://raw.githubusercontent.com/Dangerous-Taabar/astra-tv-extensions/main/img/cricfy.png"
        for ch in channels:
            title = ch.get("title", "Unknown Channel").strip()
            ch_url = ch.get("url", "").strip()
            if not ch_url:
                continue

            # Pass headers and DRM info embedded if present
            headers = ch.get("headers", {})
            drm = ch.get("drm", {})
            payload = {
                "title": title,
                "url": ch_url,
                "headers": headers,
                "drm": drm,
                "is_live": True
            }

            items.append({
                "title": title,
                "url": json.dumps(payload),
                "poster": ch.get("poster") or default_logo,
                "group": ch.get("group", ""),
                "is_live": True,
                "is_series": False,
                "is_folder": False
            })
        return items

    def search(self, query, page=1):
        """Searches channels in CricHD default playlist."""
        query = query.lower().strip()
        items = self.get_items("https://raw.githubusercontent.com/abusaeeidx/CricHd-playlists-Auto-Update-permanent/raw/main/ALL.m3u")
        return [i for i in items if query in i.get("title", "").lower()]

    def load(self, url):
        """Prepares direct playable options for Astra TV's show_media_streams."""
        target_url = url
        title = "Live Stream"
        headers = {"User-Agent": "Mozilla/5.0"}

        if url.startswith("{"):
            try:
                data = json.loads(url)
                target_url = data.get("url", url)
                title = data.get("title", "Live Stream")
                if data.get("headers"):
                    headers.update(data["headers"])
            except Exception:
                pass

        return {
            "title": title,
            "options": [
                {
                    "label": f"[Live HD] Stream Direct ({title})",
                    "urls": [target_url]
                }
            ]
        }
