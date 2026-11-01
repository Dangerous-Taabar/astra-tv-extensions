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

# Secure runtime de-obfuscator for credentials
_u = lambda s: bytes([b ^ 0x73 for b in base64.b64decode(s)]).decode('utf-8')

# Masked Remote Config & Decryption Credentials
FIREBASE_API_KEY = _u("MjoJEiAKMhtKGRg2JkM2LCYqCztDHiwxODIHXgYmICcaJyMCGxFL")
FIREBASE_APP_ID = _u("QklKRUBDQUNBQktGQEZJEh0XARwaF0lHRBYQRkBBRkEQRUcVEUAQShBEEUtB")
FIREBASE_PROJECT_NUMBER = _u("SkVAQ0FDQUJLRkBG")
PACKAGE_NAME = _u("EBweXRABGhAVCl0HBQ==")
DEFAULT_BASE_URL = _u("GwcHAwBJXFwQFQoeEgEYABASHRkaHAAHEgFLQ10HHAM=")

# Masked AES Keys for cats.txt decryption
KEY1 = (bytes.fromhex(_u("QEBFS0dLRBJES0ZKR0JFREZAR0RHSkBLQRVFS0VCRRc=")), bytes.fromhex(_u("RkZEQkdAREVFEURFRRJFRkVAR0ZHSkQSQEtAR0BBRkU=")))
KEY2 = (bytes.fromhex(_u("RxdEQkVGRkpHREdARkdAR0dCRkpHEUUVR0tHEURBRkc=")), bytes.fromhex(_u("RRVHS0cRREFGR0ZCREZGQ0RLQEtEEkUQQEtFFUcSQRE=")))
KEYS = [KEY1, KEY2]
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
                info_part, title = line.rsplit(",", 1)
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
            elif "license_type=" in prop:
                current.setdefault("drm", {})["license_type"] = prop.split("license_type=", 1)[1].strip()
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

    def get_categories(self, tv_type=None):
        """Returns verified active live TV channel playlists."""
        if tv_type == "LiveEvents":
            return []  # Cricfy has only 24/7 TV channels, no match events

        return [
            ("[Live TV] FanCode Sports Channels", "https://raw.githubusercontent.com/doctor-8trange/zyphx8/refs/heads/main/data/fancode.m3u"),
            ("[Live TV] Prime Video Sports Channels", "https://raw.githubusercontent.com/srhady/willow-event/refs/heads/main/primevideo_sports.m3u"),
            ("[Live TV] India TV Channels", "https://iptv-org.github.io/iptv/languages/hin.m3u"),
            ("[Live TV] Samsung TV Plus Channels", "https://alex4528.site/playlist/samsungtv.m3u"),
            ("[Live TV] Free TV Global Streams", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
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
