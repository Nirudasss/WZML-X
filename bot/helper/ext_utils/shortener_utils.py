import aiohttp
import asyncio
from base64 import b64encode
from random import choice, random
from urllib.parse import quote
from cloudscraper import create_scraper
from urllib3 import disable_warnings
from ... import LOGGER, shortener_dict
from ...core.config_manager import Config

async def get_encrypted_url(link):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://short.gkbotz.qzz.io/api/encrypt",
                params={"url": link},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            ) as res:
                if res.status == 200:
                    data = await res.json()
                    token = data.get("encrypted_url")
                    if token:
                        return token
    except Exception as e:
        LOGGER.error(f"GKBotz encryption error: {e}")
    return None
    
async def short_url(longurl, attempt=0):
    if not shortener_dict and not Config.PROTECTED_API:
        return longurl
    if attempt >= 4:
        return longurl

    cget = create_scraper().request
    disable_warnings()

    try:
        # STEP A: Protected API
        if Config.PROTECTED_API:
            res = cget("GET", Config.PROTECTED_API, params={"url": longurl}).json()
            if res.get("status") == "success":
                return res["url"]
            raise Exception(f"Protected API Error: {res}")

        # STEP B: GKBotz encryption
        encrypted_url = await get_encrypted_url(longurl)
        if encrypted_url:
            return encrypted_url

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

        else:
            return longurl

    except Exception as e:
        LOGGER.error(e)
        await asyncio.sleep(0.8)
        attempt += 1
        return await short_url(longurl, attempt)
