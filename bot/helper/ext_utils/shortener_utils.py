import asyncio
import requests
from base64 import b64encode
from random import choice, random
from asyncio import sleep as asleep
from urllib.parse import quote

from cloudscraper import create_scraper
from urllib3 import disable_warnings

from ... import LOGGER, shortener_dict
from ...core.config_manager import Config

# 1️⃣ Synchronous GKBotz encryption
def get_encrypted_url(link):
    try:
        res = requests.get(
            "https://short.gkbotz.qzz.io/api/encrypt",
            params={"url": link},
            timeout=10
        )
        if res.status_code == 200:
            encrypted = res.json().get("encrypted_url")
            if encrypted:
                return encrypted
    except Exception as e:
        LOGGER.error(f"Encryption API error: {e}")
    return None

# 2️⃣ Async short_url
async def short_url(longurl, attempt=0):
    if not shortener_dict and not Config.PROTECTED_API:
        return longurl
    if attempt >= 4:
        return longurl

    cget = create_scraper().request
    disable_warnings()

    try:
        # STEP A: Try Protected API first
        if Config.PROTECTED_API:
            res = cget("GET", Config.PROTECTED_API, params={"url": longurl}).json()
            if res.get("status") == "success":
                return res["url"]
            raise Exception(f"Protected API Error: {res}")

        # STEP B: Try GKBotz encryption first
        encrypted_url = await asyncio.to_thread(get_encrypted_url, longurl)
        if encrypted_url:
            return encrypted_url  # RETURN immediately if encrypted link exists

        # STEP C: Fallback to other shorteners
        _shortener, _shortener_api = choice(list(shortener_dict.items()))

        if "shorte.st" in _shortener:
            headers = {"public-api-token": _shortener_api}
            data = {"urlToShorten": quote(longurl)}
            return cget(
                "PUT", "https://api.shorte.st/v1/data/url", headers=headers, data=data
            ).json()["shortenedUrl"]

        elif "linkvertise" in _shortener:
            url = quote(b64encode(longurl.encode("utf-8")))
            linkvertise = [
                f"https://link-to.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://up-to-down.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://direct-link.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
                f"https://file-link.net/{_shortener_api}/{random() * 1000}/dynamic?r={url}",
            ]
            return choice(linkvertise)

        # Add other shorteners if needed
        else:
            return longurl

    except Exception as e:
        LOGGER.error(e)
        await asleep(0.8)
        attempt += 1
        return await short_url(longurl, attempt)
