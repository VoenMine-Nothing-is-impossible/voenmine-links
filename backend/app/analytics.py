"""Мини-парсер User-Agent + Geo-заглушка (без внешних БД)."""


def parse_ua(ua: str = "") -> tuple[str, str, str]:
    ua_l = (ua or "").lower()
    # browser
    if "yabrowser" in ua_l:
        browser = "Yandex"
    elif "edg" in ua_l:
        browser = "Edge"
    elif "opr" in ua_l or "opera" in ua_l:
        browser = "Opera"
    elif "firefox" in ua_l:
        browser = "Firefox"
    elif "chrome" in ua_l:
        browser = "Chrome"
    elif "safari" in ua_l:
        browser = "Safari"
    elif "bot" in ua_l or "crawl" in ua_l or "spider" in ua_l:
        browser = "Bot"
    else:
        browser = "Other"
    # os
    if "windows" in ua_l:
        os = "Windows"
    elif "android" in ua_l:
        os = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l or "ios" in ua_l:
        os = "iOS"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os = "macOS"
    elif "linux" in ua_l:
        os = "Linux"
    else:
        os = "Other"
    # device
    if "mobile" in ua_l or "android" in ua_l or "iphone" in ua_l:
        device = "mobile"
    elif "tablet" in ua_l or "ipad" in ua_l:
        device = "tablet"
    elif "bot" in ua_l or "crawl" in ua_l:
        device = "bot"
    else:
        device = "desktop"
    return browser, os, device


def guess_country(ip: str = "") -> str:
    if not ip or ip.startswith(("127.", "10.", "192.168.", "::1", "172.")):
        return "local"
    return "unknown"
