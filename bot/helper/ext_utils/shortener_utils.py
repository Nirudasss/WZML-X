
from base64 import b64encode
from random import choice, random
from asyncio import sleep as asleep
from urllib.parse import quote
from aiohttp import ClientSession
from cloudscraper import create_scraper
from urllib3 import disable_warnings
from ... import LOGGER, shortener_dict

WORKER_URL = "https://antibypass.tellycloudapi.workers.dev/create"

async def short_url(longurl, attempt=0):
    if not longurl:
        return longurl
    if attempt >= 4:
        LOGGER.warning(f"Max attempts reached → {longurl}")
        return longurl
    disable_warnings()
    cget = create_scraper().request
    # ----------------------------------------------------
    # METHOD 1 → CLOUDFLARE WORKER (NEW API)
    # ----------------------------------------------------
    try:
        async with ClientSession() as session:
            payload = {
                "url": longurl,
                # Optional fields - add as needed:
                # "alias": "mylink",
                # "expiry": 7,
                # "password": "auto",
                # "apitoken": "1eb2c8965c222bcb19d9069be47997aa1ac65b7f",
                # "apiurl": "https://softurl.in/api",
                # "apidomain": "softurl.in",
                # "channels": [
                #     {
                #         "name": "Elite Botz",
                #         "url": "https://t.me/Radh_Rani_Backup"
                #     }
                # ]
            }
            async with session.post(
                WORKER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") and data.get("shortUrl"):
                        shorted = data["shortUrl"]
                        LOGGER.info(f"Worker Shortened → {shorted}")
                        return shorted
    except Exception as e:
        LOGGER.error(f"Worker failed → {e}")
    # No shortener configured = return original URL
    if not shortener_dict:
        return longurl
    # ----------------------------------------------------
    # METHOD 2 → OLD SHORTENER SYSTEM
    # ----------------------------------------------------
    _shortener, _shortener_api = choice(list(shortener_dict.items()))
    try:
        # shorte.st
        if "shorte.st" in _shortener:
            headers = {"public-api-token": _shortener_api}
            data = {"urlToShorten": quote(longurl)}
            res = cget("PUT", "https://api.shorte.st/v1/data/url", headers=headers, data=data).json()
            return res.get("shortenedUrl", longurl)
        # Linkvertise
        if "linkvertise" in _shortener:
            enc = quote(b64encode(longurl.encode()).decode())
            options = [
                f"https://link-to.net/{_shortener_api}/{random()*1000}/dynamic?r={enc}",
                f"https://up-to-down.net/{_shortener_api}/{random()*1000}/dynamic?r={enc}",
                f"https://direct-link.net/{_shortener_api}/{random()*1000}/dynamic?r={enc}",
                f"https://file-link.net/{_shortener_api}/{random()*1000}/dynamic?r={enc}",
            ]
            return choice(options)
        # Bitly
        if "bitly.com" in _shortener:
            headers = {"Authorization": f"Bearer {_shortener_api}"}
            res = cget("POST", "https://api-ssl.bit.ly/v4/shorten",
                       json={"long_url": longurl}, headers=headers).json()
            return res.get("link", longurl)
        # Ouo.io
        if "ouo.io" in _shortener:
            return cget("GET", f"http://ouo.io/api/{_shortener_api}?s={longurl}", verify=False).text or longurl
        # Cutt.ly
        if "cutt.ly" in _shortener:
            res = cget("GET", f"http://cutt.ly/api/api.php?key={_shortener_api}&short={longurl}").json()
            return res.get("url", {}).get("shortLink", longurl)
        # GENERIC SHORTENER (GPLinks, UrlShortX etc.)
        res = cget("GET", f"https://{_shortener}/api?api={_shortener_api}&url={quote(longurl)}").json()
        shorted = res.get("shortenedUrl")
        # fallback via shrtco
        if not shorted:
            fallback = cget("GET", f"https://api.shrtco.de/v2/shorten?url={quote(longurl)}").json()
            sc = fallback.get("result", {}).get("full_short_link")
            if sc:
                res2 = cget("GET", f"https://{_shortener}/api?api={_shortener_api}&url={sc}").json()
                shorted = res2.get("shortenedUrl")
        return shorted or longurl
    except Exception as e:
        LOGGER.error(e)
        await asleep(0.8)
        return await short_url(longurl, attempt + 1)
