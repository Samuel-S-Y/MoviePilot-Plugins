# -*- coding: utf-8 -*-
"""
RSSHubReader - MoviePilot v3 资讯源阅读器插件

功能：
  - 管理订阅源（增删改，存于插件数据目录 feeds.json）
  - **OPML 导入/导出**：与其它阅读器互迁订阅源
  - 定时拉取 RSSHub 路由输出（Atom/RSS），解析条目
  - 抓取文章正文，提取完整图片列表（比 RSS 里的 thumbnail 更全）
  - 后端图片代理，绕开豆瓣/B站等外链防盗链与跨域
  - **已读/未读标记**：按文章 id 持久化，支持单条/全部标记/未读数统计
  - **规则通知**：按字段（标题/描述/作者/分类/链接）+ 关键词或正则配置正向规则，
    刷新时对新条目匹配，命中即通过 MP 通知组件（MessageCenter / 各渠道）提醒，
    已通知/已读条目自动去重，通知后标记已读
  - Vuetify JSON 前端：订阅源管理 + 文章列表 + 图片画廊 + 通知规则管理

技术栈：feedparser（RSS/Atom）+ requests（正文抓取）+ BeautifulSoup（提取图片）
全部运行于 MP 插件体系，无需 Node/前端构建。
"""

import os
import io
import re
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import urlparse, urljoin
from xml.etree import ElementTree as ET

# ---- 依赖采用「可用即用、缺失降级」策略 ----
# feedparser / requests 在 MP 运行时通常由环境提供；本地测试或无网环境可降级为 stdlib
try:
    import requests as _requests
    HAVE_REQUESTS = True
except ImportError:
    _requests = None
    HAVE_REQUESTS = False

try:
    import feedparser as _feedparser
    HAVE_FEEDPARSER = True
except ImportError:
    _feedparser = None
    HAVE_FEEDPARSER = False

try:
    from bs4 import BeautifulSoup as _BeautifulSoup
    HAVE_BS4 = True
except ImportError:
    _BeautifulSoup = None
    HAVE_BS4 = False

# 兼容双环境：有 MoviePilot 运行时正常导入；本地测试时用桩替代
try:
    from app.helper import StorageHelper
    from app.schemas import NotificationType
    from app.log import logger
    from plugins._pluginbase import _PluginBase
except ImportError:  # pragma: no cover - 本地测试桩
    class StorageHelper:
        @staticmethod
        def get_data_path(name):
            path = os.path.join(os.path.dirname(__file__), "_test_data", name)
            os.makedirs(path, exist_ok=True)
            return path

    class NotificationType:
        Info = "info"

    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    class _PluginBase:
        config = {}
        def init(self, **kwargs):
            pass
        def get_config(self, key, default=None):
            return (self.config or {}).get(key, default)


# ---------- 常量 ----------
PLUGIN_NAME = "rsshub_reader"
USER_AGENT = (
    "Mozilla/5.0 (compatible; RSSHubReader/1.0; +https://github.com/jxxghp/MoviePilot)"
)
REQUEST_TIMEOUT = 20
# 单次抓取正文时最多提取的图片数，避免超长页面拖慢
MAX_IMAGES_PER_ENTRY = 30
# 允许通过代理返回的 Content-Type 白名单
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
}


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def _safe_name(s: str) -> str:
    """把任意字符串转成安全的文件名片段。"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def _parse_date(struct_time) -> str:
    """feedparser 的时间结构是 time.struct_time，转 ISO 字符串。"""
    if not struct_time:
        return ""
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", struct_time)
    except Exception:
        return ""


def _absolutize(base: str, url: str) -> str:
    """把相对 URL 转绝对 URL。"""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    try:
        return urljoin(base, url)
    except Exception:
        return url


def extract_images_from_html(html: str, base_url: str) -> list:
    """
    从文章正文的 HTML 中提取完整图片 URL 列表。

    策略（按优先级，去重后返回）：
      1. <img> 的 data-src / data-original / data-srcset（懒加载常见）
      2. <img> 的 src
      3. <source srcset>
    只返回绝对 URL，过滤掉明显非图片的占位/avatar。

    优先使用 BeautifulSoup；不可用时降级为 stdlib HTMLParser。
    """
    if not html:
        return []
    if HAVE_BS4:
        return _extract_images_bs4(html, base_url)
    return _extract_images_stdlib(html, base_url)


def _extract_images_bs4(html: str, base_url: str) -> list:
    try:
        soup = _BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.debug(f"[{PLUGIN_NAME}] BeautifulSoup 解析失败: {e}")
        return []
    seen = set()
    result = []
    for img in soup.find_all("img"):
        candidates = []
        for attr in ("data-src", "data-original", "data-url", "data-large"):
            v = img.get(attr)
            if v:
                candidates.append(v)
        srcset = img.get("srcset")
        if srcset:
            candidates.append(srcset.split(",")[0].strip().split(" ")[0])
        src = img.get("src")
        if src:
            candidates.append(src)
        for c in candidates:
            abs_url = _absolutize(base_url, c).split("?")[0]
            if not abs_url or abs_url in seen:
                continue
            low = abs_url.lower()
            if any(k in low for k in ("avatar", "placeholder", "pixel.", "1x1.", "blank.gif")):
                continue
            seen.add(abs_url)
            result.append(abs_url)
            if len(result) >= MAX_IMAGES_PER_ENTRY:
                return result
    return result


def _extract_images_stdlib(html: str, base_url: str) -> list:
    """无 bs4 时的降级实现（标准库 HTMLParser）。"""
    from html.parser import HTMLParser

    class ImgParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []

        def handle_starttag(self, tag, attrs):
            if tag != "img":
                # 也可处理 <source srcset>，这里聚焦 img
                return
            d = dict(attrs)
            cands = []
            for attr in ("data-src", "data-original", "data-url", "data-large"):
                if attr in d and d[attr]:
                    cands.append(d[attr])
            if "src" in d and d["src"]:
                cands.append(d["src"])
            for c in cands:
                u = _absolutize(base_url, c).split("?")[0]
                if u and u not in self.urls:
                    low = u.lower()
                    if not any(k in low for k in ("avatar", "placeholder", "pixel.", "1x1.", "blank.gif")):
                        self.urls.append(u)

    p = ImgParser()
    try:
        p.feed(html)
    except Exception as e:
        logger.debug(f"[{PLUGIN_NAME}] stdlib 解析图片失败: {e}")
    return p.urls[:MAX_IMAGES_PER_ENTRY]


def _strip_tags(html: str) -> str:
    """去掉 HTML 标签，用于生成纯文本摘要。"""
    if not html:
        return ""
    if HAVE_BS4:
        try:
            return _BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        except Exception:
            pass
    # 降级：简单正则去标签
    import re as _re
    return _re.sub(r"<[^>]+>", "", html)


def _http_get(url: str, extra_headers: dict = None) -> "requests.Response":
    """
    HTTP GET：优先 requests；不可用时降级为 stdlib urllib。
    返回类 Response 对象（含 content / text / raise_for_status）。
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/atom+xml,application/rss+xml,*/*"}
    if extra_headers:
        headers.update(extra_headers)
    if HAVE_REQUESTS:
        return _requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    # stdlib 降级
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    req = Request(url, headers=headers)
    try:
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        data = resp.read()
        class _Resp:
            def __init__(self, data, headers):
                self.content = data
                self.text = data.decode("utf-8", "ignore")
                self.headers = headers
            def raise_for_status(self):
                pass
        return _Resp(data, dict(resp.headers))
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"HTTP 请求失败: {e}")


def _http_post_json(url: str, payload: dict):
    """POST JSON：优先 requests，降级用 stdlib。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if HAVE_REQUESTS:
        _requests.post(url, data=body, headers=headers, timeout=REQUEST_TIMEOUT)
        return
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        urlopen(req, timeout=REQUEST_TIMEOUT).read()
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"Webhook 请求失败: {e}")


def parse_feed(feed_url: str, fetch_full: bool) -> dict:
    """
    解析单个 RSSHub 路由（Atom/RSS 自动识别）。

    优先使用 feedparser（容错最强）；不可用时降级为 stdlib XML 解析。
    返回：
        {
          "title": 源标题,
          "entries": [
             {"id","title","link","author","published","summary",
              "content","images","thumbnail", ...}
          ]
        }
    """
    resp = _http_get(feed_url)
    resp.raise_for_status()

    if HAVE_FEEDPARSER:
        return _parse_feed_feedparser(resp.content, feed_url, fetch_full)
    return _parse_feed_stdlib(resp.content, feed_url, fetch_full)


def _parse_feed_feedparser(content: bytes, feed_url: str, fetch_full: bool) -> dict:
    parsed = _feedparser.parse(content)
    feed_title = ""
    if hasattr(parsed, "feed"):
        feed_title = getattr(parsed.feed, "title", "") or ""

    entries = []
    for e in getattr(parsed, "entries", []):
        link = getattr(e, "link", "") or ""
        title = getattr(e, "title", "") or "(无标题)"
        content_html = ""
        if hasattr(e, "content") and e.content:
            content_html = e.content[0].get("value", "")
        if not content_html:
            content_html = getattr(e, "summary", "") or ""
        images = []
        for t in getattr(e, "media_thumbnail", []) or []:
            u = t.get("url") if isinstance(t, dict) else t
            if u:
                images.append(_absolutize(link, u))
        for enc in getattr(e, "enclosures", []) or []:
            if isinstance(enc, dict) and enc.get("type", "").startswith("image/"):
                images.append(_absolutize(link, enc.get("href", "")))
        if fetch_full and link and not content_html:
            try:
                r = _http_get(link, {"Accept-Language": "zh-CN,zh;q=0.9"})
                r.raise_for_status()
                content_html = r.text
            except Exception as ex:
                logger.debug(f"[{PLUGIN_NAME}] 抓取正文失败 {link}: {ex}")
        body_images = extract_images_from_html(content_html, link)
        for u in body_images:
            if u not in images:
                images.append(u)
        entries.append({
            "id": getattr(e, "id", "") or link or _safe_name(title),
            "title": title,
            "link": link,
            "author": getattr(e, "author", "") or "",
            "published": _parse_date(getattr(e, "published_parsed", None)
                                     or getattr(e, "updated_parsed", None)),
            "summary": _strip_tags(getattr(e, "summary", "") or "")[:300],
            "content": content_html,
            "images": images,
            "thumbnail": images[0] if images else "",
            "category": [getattr(t, "term", "") for t in (getattr(e, "tags", []) or [])],
        })
    return {"title": feed_title, "entries": entries}


def _parse_feed_stdlib(content: bytes, feed_url: str, fetch_full: bool) -> dict:
    """无 feedparser 时的降级解析（标准库 xml.etree，支持 RSS 2.0 / Atom）。"""
    root = ET.fromstring(content)
    # Atom: feed > entry；RSS: rss > channel > item
    feed_el = root
    if feed_el.tag.endswith("rss"):
        feed_el = root.find("channel") or root

    def _text(el, *names, default=""):
        for name in names:
            node = el.find(name)
            if node is not None and node.text:
                return node.text.strip()
        return default

    feed_title = _text(feed_el, "title")

    entries = []
    # 兼容 Atom (entry) 与 RSS (item)
    for item in feed_el.findall("item") or feed_el.findall("{http://www.w3.org/2005/Atom}entry"):
        link = _text(item, "link", "{http://www.w3.org/2005/Atom}link")
        if not link:
            # Atom link 可能是属性
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            if link_el is not None:
                link = link_el.get("href", "")
        title = _text(item, "title", "{http://www.w3.org/2005/Atom}title") or "(无标题)"
        author = _text(item, "author", "{http://www.w3.org/2005/Atom}author")
        summary = _text(item, "description", "summary", "{http://www.w3.org/2005/Atom}summary")
        content_html = _text(item, "content", "{http://www.w3.org/2005/Atom}content") or summary
        published = _text(item, "pubDate", "published", "{http://www.w3.org/2005/Atom}published")
        # 简易时间格式化
        pub_struct = None
        try:
            import email.utils as eu
            pub_struct = eu.parsedate(published)
        except Exception:
            pass

        images = []
        # enclosure / media:thumbnail
        for enc in item.findall("enclosure") + item.findall("{http://search.yahoo.com/mrss/}thumbnail"):
            url_attr = enc.get("url") or enc.get("href", "")
            if url_attr:
                images.append(_absolutize(link, url_attr))

        if fetch_full and link and not content_html:
            try:
                r = _http_get(link, {"Accept-Language": "zh-CN,zh;q=0.9"})
                r.raise_for_status()
                content_html = r.text
            except Exception as ex:
                logger.debug(f"[{PLUGIN_NAME}] 抓取正文失败 {link}: {ex}")

        body_images = extract_images_from_html(content_html, link)
        for u in body_images:
            if u not in images:
                images.append(u)

        # category
        cats = []
        for c in item.findall("category") + item.findall("{http://www.w3.org/2005/Atom}category"):
            term = c.get("term") or c.text or ""
            if term:
                cats.append(term)

        entries.append({
            "id": _text(item, "guid", "id", "{http://www.w3.org/2005/Atom}id") or link or _safe_name(title),
            "title": title,
            "link": link,
            "author": author,
            "published": _parse_date(pub_struct),
            "summary": _strip_tags(summary)[:300],
            "content": content_html,
            "images": images,
            "thumbnail": images[0] if images else "",
            "category": cats,
        })
    return {"title": feed_title, "entries": entries}


# ----------------------------------------------------------------------
# 插件主类
# ----------------------------------------------------------------------
class RsshubReader(_PluginBase):
    """RSSHub 资讯源阅读器插件。"""

    # ---- 插件元信息（MP 后台“插件市场”展示用）----
    plugin_name = PLUGIN_NAME
    plugin_desc = "RSSHub 资讯源阅读器：订阅管理（OPML导入导出）、阅读文章、完整图片、已读标记、规则通知（含后端图片代理）"
    version = "1.2.0"
    author = "your-name"

    # ---- 持久化 ----
    # 数据目录由 MP 提供，位于插件数据根下，重启不丢失
    _data_dir: str = None
    _feeds_file: str = None
    _cache_file: str = None
    _read_file: str = None  # 已读标记文件

    # 运行时内存态（刷新后重建，无需落盘）
    _articles: dict = {}  # feed_url -> [entries...]
    # 已读状态（内存缓存，结构：{entry_key: {"read": True, "read_at": "..."}}）
    # entry_key 用 "feed_url::entry_id" 拼接，id 缺失时回退到 link
    _read_status: dict = {}

    # ================= 生命周期 =================
    def init(self, **kwargs):
        """
        插件加载时调用：初始化数据目录与文件。
        幂等：MP 重载插件时可能多次调用，用 _initialized 守护，避免状态被清空。
        """
        if getattr(self, "_initialized", False):
            return
        super().init(**kwargs)
        self._data_dir = StorageHelper.get_data_path(self.__class__.__name__)
        os.makedirs(self._data_dir, exist_ok=True)
        self._feeds_file = os.path.join(self._data_dir, "feeds.json")
        self._cache_file = os.path.join(self._data_dir, "articles.json")
        self._read_file = os.path.join(self._data_dir, "read_status.json")
        self._rules_file = os.path.join(self._data_dir, "notify_rules.json")
        self._notified_file = os.path.join(self._data_dir, "notified_entries.json")
        # OPML 导入暂存目录（存放用户上传的 .opml 文件）
        os.makedirs(os.path.join(self._data_dir, "opml_imports"), exist_ok=True)
        # 内存状态（首次启动时为空；已在 refresh_all 中惰性恢复缓存）
        self._articles = getattr(self, "_articles", {})
        self._read_status = self._load_read_status()
        self._rules = self._load_rules()
        self._notified = self._load_notified()
        self._initialized = True
        logger.info(f"[{PLUGIN_NAME}] 数据目录: {self._data_dir}")

    def destroy(self):
        """插件卸载/重载时调用：落盘状态，避免丢失。"""
        try:
            self._save_read_status()
            self._save_notified()
            self._save_rules()
        except Exception:
            pass
        logger.info(f"[{PLUGIN_NAME}] 已销毁")

    # ================= 配置表单 =================
    def get_form(self) -> dict:
        """
        后台“设置”页的表单。这里只放真正需要用户改的项，
        源列表管理放到前端页面（增删更友好）。
        """
        return {
            "schema": {
                "type": "object",
                "properties": {
                    "rsshub_base_url": {
                        "type": "string",
                        "title": "RSSHub 地址",
                        "description": "局域网 RSSHub 访问地址，如 http://192.168.1.100:1200",
                        "default": "http://127.0.0.1:1200",
                    },
                    "poll_interval": {
                        "type": "integer",
                        "title": "刷新间隔（分钟）",
                        "description": "定时拉取所有订阅源的周期，建议 15~60",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 1440,
                    },
                    "fetch_full": {
                        "type": "boolean",
                        "title": "抓取正文提取完整图片",
                        "description": "开启后会对文章页抓取以提取全部图片，较慢；关闭则只用 RSS 内嵌图片",
                        "default": True,
                    },
                    "proxy_images": {
                        "type": "boolean",
                        "title": "启用后端图片代理",
                        "description": "通过本插件转发图片，绕开豆瓣/B站等防盗链与跨域，建议开启",
                        "default": True,
                    },
                    "max_entries": {
                        "type": "integer",
                        "title": "每个源保留条数",
                        "description": "每个订阅源最多保留的文章数，避免内存膨胀",
                        "default": 50,
                        "minimum": 10,
                        "maximum": 500,
                    },
                    "opml_group": {
                        "type": "string",
                        "title": "OPML 默认分组",
                        "description": "OPML 导入时若源未指定分组，使用此名称；留空则不分组",
                        "default": "导入",
                    },
                    "mark_read_on_open": {
                        "type": "boolean",
                        "title": "打开文章自动标为已读",
                        "description": "开启后，点开文章详情即标记为已读",
                        "default": True,
                    },
                    "notify_channel": {
                        "type": "string",
                        "title": "规则通知渠道",
                        "description": "命中规则时使用的通知渠道；单条规则可单独指定，留空则使用此默认值",
                        "default": "MessageCenter",
                        "enum": [
                            "MessageCenter",
                            "Telegram",
                            "ServerChan",
                            "PushPlus",
                            "WeChatWork",
                            "Webhook",
                        ],
                    },
                    "notify_enabled": {
                        "type": "boolean",
                        "title": "启用规则通知",
                        "description": "关闭后，刷新不再触发规则匹配与通知（保留规则配置）",
                        "default": True,
                    },
                    "notify_template": {
                        "type": "string",
                        "title": "通知内容模板",
                        "description": "支持变量：{title} 标题、{feed} 源名、{link} 原文链接、{rule} 命中规则名",
                        "default": "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
                    },
                    "max_notify_log": {
                        "type": "integer",
                        "title": "通知记录保留条数",
                        "description": "『最近通知记录』最多保留条数，避免文件膨胀",
                        "default": 200,
                        "minimum": 10,
                        "maximum": 2000,
                    },
                },
                "required": ["rsshub_base_url", "poll_interval"],
            },
            "ui": {
                "rsshub_base_url": {"placeholder": "http://127.0.0.1:1200"},
            },
        }

    # ================= 定时任务 =================
    def get_service(self) -> dict:
        """
        注册定时刷新任务。
        MP 调度器按配置的 poll_interval 周期性调用 self.refresh_all。
        """
        interval = int(self.get_config("poll_interval", 30))
        return {
            "name": "rsshub_reader.refresh",
            "func": self.refresh_all,
            "interval": interval,  # 分钟
        }

    # ---- 对外：供 API / 前端触发手动刷新 ----
    def refresh_all(self, *_args, **_kwargs):
        """遍历所有订阅源并拉取，结果同时写内存与磁盘缓存。"""
        feeds = self._load_feeds()
        if not feeds:
            logger.debug(f"[{PLUGIN_NAME}] 暂无订阅源，跳过刷新")
            return

        max_entries = int(self.get_config("max_entries", 50))
        fetch_full = bool(self.get_config("fetch_full", True))

        articles = {}
        for feed in feeds:
            url = feed.get("url", "").strip()
            if not url:
                continue
            try:
                data = parse_feed(url, fetch_full=fetch_full)
                # 截断条数
                data["entries"] = data["entries"][:max_entries]
                articles[url] = data
                logger.info(
                    f"[{PLUGIN_NAME}] 拉取成功 [{data['title'] or url}] "
                    f"{len(data['entries'])} 条"
                )
            except Exception as e:
                logger.error(f"[{PLUGIN_NAME}] 拉取失败 {url}: {e}")
                # 保留上次缓存，避免一次失败就清空
                if url in self._articles:
                    articles[url] = self._articles[url]

        self._articles = articles
        self._save_cache(articles)
        # 刷新后清理失效的已读记录（惰性，仅在记录量大时真正执行）
        self._maybe_gc_read_status()
        # 规则通知：仅对新出现的条目进行匹配（去重 + 已读联动在 match 内部处理）
        if bool(self.get_config("notify_enabled", True)):
            self._process_notify(articles)

    # ================= 自定义 API =================
    def get_api(self) -> list:
        """
        暴露给前端的 HTTP 接口（由 MP 统一挂载在 /api/v1/plugin/{plugin_name}/...）。
        前端通过 window.PluginAPI 调用。
        """
        return [
            {
                "path": "feeds",
                "methods": ["GET", "POST", "DELETE"],
                "func": self.api_feeds,
                "summary": "订阅源管理（列表/添加/删除）",
            },
            {
                "path": "articles",
                "methods": ["GET"],
                "func": self.api_articles,
                "summary": "获取所有/指定源的文章",
            },
            {
                "path": "refresh",
                "methods": ["POST"],
                "func": self.api_refresh,
                "summary": "手动触发刷新",
            },
            {
                "path": "proxy",
                "methods": ["GET"],
                "func": self.api_proxy,
                "summary": "图片代理（绕开防盗链/跨域）",
            },
            # ---- OPML 导入/导出 ----
            {
                "path": "opml/export",
                "methods": ["GET"],
                "func": self.api_opml_export,
                "summary": "导出 OPML（订阅源备份/迁移）",
            },
            {
                "path": "opml/import",
                "methods": ["POST"],
                "func": self.api_opml_import,
                "summary": "导入 OPML（从其它阅读器迁移订阅源）",
            },
            # ---- 已读/未读标记 ----
            {
                "path": "read",
                "methods": ["POST", "DELETE"],
                "func": self.api_read,
                "summary": "标记单条已读/未读",
            },
            {
                "path": "read/all",
                "methods": ["POST"],
                "func": self.api_read_all,
                "summary": "将指定源（或全部）标记为已读",
            },
            # ---- 规则通知 ----
            {
                "path": "rules",
                "methods": ["GET", "POST", "DELETE"],
                "func": self.api_rules,
                "summary": "通知规则管理（列表/添加/删除）",
            },
            {
                "path": "rules/test",
                "methods": ["POST"],
                "func": self.api_rules_test,
                "summary": "测试规则匹配（对当前缓存文章试运行，不发送通知）",
            },
            {
                "path": "notify/log",
                "methods": ["GET", "DELETE"],
                "func": self.api_notify_log,
                "summary": "通知记录（查询/清空）",
            },
        ]

    # 路由表便于自查（非正式 API）
    def api_routes(self, **_):
        """返回当前注册的 API 路由清单，供前端/调试使用。"""
        return {
            "ok": True,
            "routes": [
                {"path": a["path"], "methods": a["methods"], "summary": a["summary"]}
                for a in self.get_api()
            ],
        }

    # ---- API 实现 ----
    def api_feeds(self, url: str = None, method: str = "GET", payload: dict = None, **_):
        """
        GET 列表（附分组、未读数）/ POST 添加 / DELETE 删除。
        添加时支持 group 字段，便于 OPML 导入与前端分组管理。
        """
        feeds = self._load_feeds()
        if method == "POST":
            url = (payload or {}).get("url", "").strip()
            name = (payload or {}).get("name", "").strip()
            group = (payload or {}).get("group", "").strip()
            site_url = (payload or {}).get("site_url", "").strip()
            if not url:
                return {"ok": False, "msg": "url 不能为空"}
            if any(f["url"] == url for f in feeds):
                return {"ok": False, "msg": "该源已存在"}
            feeds.append({
                "url": url,
                "name": name or url,
                "site_url": site_url,
                "group": group,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            self._save_feeds(feeds)
            # 添加后立刻拉一次
            self._refresh_one(url)
            return {"ok": True, "feeds": self._feeds_with_unread(feeds)}
        if method == "DELETE":
            feeds = [f for f in feeds if f.get("url") != url]
            self._save_feeds(feeds)
            self._articles.pop(url, None)
            return {"ok": True, "feeds": self._feeds_with_unread(feeds)}
        return {"ok": True, "feeds": self._feeds_with_unread(feeds)}

    def _feeds_with_unread(self, feeds: list) -> list:
        """给源列表附加 group 与 unread 字段。"""
        self._maybe_load_cache()
        out = []
        for f in feeds:
            u = f["url"]
            d = self._articles.get(u, {"entries": []})
            unread = sum(1 for e in d.get("entries", []) if not self._is_read(u, e))
            item = dict(f)
            item.setdefault("group", "")
            item["unread"] = unread
            out.append(item)
        return out

    def api_articles(self, url: str = None, **_):
        """
        GET ?url=xxx 返回单源（每条文章附 is_read）；
        不带参数返回全部源的概览（含未读数）。
        """
        self._maybe_load_cache()
        if url:
            data = self._articles.get(url, {"title": "", "entries": []})
            # 为每条文章附加已读标记
            entries = []
            for e in data.get("entries", []):
                d = dict(e)
                d["is_read"] = self._is_read(url, e)
                entries.append(d)
            return {"ok": True, "data": {**data, "entries": entries}}
        # 按源聚合，附带未读数
        feeds = self._load_feeds()
        result = []
        for f in feeds:
            u = f["url"]
            d = self._articles.get(u, {"title": "", "entries": []})
            entries = d.get("entries", [])
            unread = sum(1 for e in entries if not self._is_read(u, e))
            result.append({
                "url": u,
                "name": f.get("name", u),
                "group": f.get("group", ""),
                "title": d.get("title", ""),
                "count": len(entries),
                "unread": unread,
            })
        return {"ok": True, "feeds": result}

    def api_refresh(self, **_):
        try:
            self.refresh_all()
            return {"ok": True, "msg": "刷新完成"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def api_proxy(self, url: str = None, **_):
        """
        图片代理：前端 <img src="/api/v1/plugin/rsshub_reader/proxy?url=...">
        由后端请求目标图片并流式返回，绕过防盗链与跨域。
        """
        if not url:
            return {"ok": False, "msg": "缺少 url 参数"}
        try:
            r = _http_get(
                url,
                {"Referer": url},  # 部分站点靠 Referer 防盗链
            )
            r.raise_for_status()
            ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ctype not in ALLOWED_IMAGE_TYPES:
                # 不认识的也放行（有些 CDN 返回 application/octet-stream），前端自行处理
                ctype = "image/jpeg"
            # 返回二进制响应；MP 会把 Response 透传给前端
            from fastapi.responses import Response
            return Response(
                content=r.content,
                media_type=ctype,
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 图片代理失败 {url}: {e}")
            # 返回 1x1 透明图，避免前端破图影响布局
            return self._blank_pixel()

    # ========== OPML 导出 ==========
    def api_opml_export(self, **_):
        """
        将所有订阅源导出为 OPML 2.0 格式（text/xml）。
        兼容 Feedly / Inoreader / Miniflux / FreshRSS 等主流阅读器，
        导入时通过 <outline> 的 type="rss" xmlUrl 属性识别。
        返回 FastAPI Response（附件下载）。
        """
        feeds = self._load_feeds()
        root = ET.Element("opml", version="2.0")
        head = ET.SubElement(root, "head")
        ET.SubElement(head, "title").text = "MoviePilot RSSHubReader Subscriptions"
        ET.SubElement(head, "dateCreated").text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = ET.SubElement(root, "body")

        # 先按分组组织（未分组的放在根下）
        grouped = {}
        ungrouped = []
        for f in feeds:
            grp = f.get("group") or ""
            if grp:
                grouped.setdefault(grp, []).append(f)
            else:
                ungrouped.append(f)

        def add_outline(parent, feed):
            attrs = {
                "type": "rss",
                "text": feed.get("name", feed["url"]),
                "title": feed.get("name", feed["url"]),
                "xmlUrl": feed["url"],
            }
            if feed.get("site_url"):
                attrs["htmlUrl"] = feed["site_url"]
            return ET.SubElement(parent, "outline", **attrs)

        for f in ungrouped:
            add_outline(body, f)
        for grp, items in grouped.items():
            folder = ET.SubElement(body, "outline", text=grp, title=grp)
            for f in items:
                add_outline(folder, f)

        # 序列化（声明 + 缩进）
        xml_bytes = io.BytesIO()
        xml_bytes.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree = ET.ElementTree(root)
        # 手动缩进美化（Python 3.9+ 可用 indent）
        try:
            ET.indent(tree, space="  ")
        except Exception:
            pass
        tree.write(xml_bytes, encoding="UTF-8", xml_declaration=False)
        content = xml_bytes.getvalue()

        filename = f"rsshub_reader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.opml"
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="text/xml; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    # ========== OPML 导入 ==========
    def api_opml_import(self, payload: dict = None, **_):
        """
        解析 OPML（支持 1.0/1.1/2.0），提取所有 type="rss"/"atom" 的 outline，
        追加到本地订阅源（自动去重）。可选参数：
          - content: OPML 文本字符串（优先）
          - url: 远程 OPML 文件地址（备用）
          - group: 强制归到指定分组（覆盖 OPML 内的 folder 结构）
        """
        if not payload:
            return {"ok": False, "msg": "缺少 payload"}
        content = (payload or {}).get("content", "").strip()
        remote_url = (payload or {}).get("url", "").strip()
        force_group = (payload or {}).get("group", "").strip()

        if not content:
            if not remote_url:
                return {"ok": False, "msg": "请提供 OPML 内容（content）或远程地址（url）"}
            try:
                r = _http_get(remote_url)
                r.raise_for_status()
                content = r.text
            except Exception as e:
                return {"ok": False, "msg": f"下载远程 OPML 失败: {e}"}

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            return {"ok": False, "msg": f"OPML 解析失败（不是合法 XML）: {e}"}

        # OPML: 订阅源在 root/body 下任意层级的 <outline type="rss|atom">
        feeds = self._load_feeds()
        existing_urls = {f["url"] for f in feeds}
        default_group = force_group or self.get_config("opml_group", "导入")

        imported = []
        skipped = []

        def walk(parent):
            for outline in parent.findall("outline"):
                otype = (outline.get("type", "") or "").lower()
                xml_url = (outline.get("xmlUrl") or outline.get("xmlurl") or "").strip()
                if otype in ("rss", "atom", "feed") and xml_url:
                    # 叶子节点：一个订阅源
                    name = outline.get("title") or outline.get("text") or xml_url
                    site_url = outline.get("htmlUrl", "").strip()
                    if xml_url in existing_urls:
                        skipped.append(name)
                    else:
                        grp = force_group or outline.get("group", "").strip() or default_group
                        feeds.append({
                            "url": xml_url,
                            "name": name,
                            "site_url": site_url,
                            "group": grp,
                            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        existing_urls.add(xml_url)
                        imported.append(name)
                else:
                    # 文件夹节点：递归，并以其 text/title 作为分组（除非强制分组）
                    folder_name = outline.get("title") or outline.get("text", "")
                    if not force_group and folder_name:
                        # 进入分组上下文：子节点归到该 folder
                        walk_folder(outline, folder_name)
                    else:
                        walk(outline)

        def walk_folder(parent, folder):
            for outline in parent.findall("outline"):
                otype = (outline.get("type", "") or "").lower()
                xml_url = (outline.get("xmlUrl") or "").strip()
                if otype in ("rss", "atom", "feed") and xml_url:
                    name = outline.get("title") or outline.get("text") or xml_url
                    site_url = outline.get("htmlUrl", "").strip()
                    if xml_url in existing_urls:
                        skipped.append(name)
                    else:
                        feeds.append({
                            "url": xml_url,
                            "name": name,
                            "site_url": site_url,
                            "group": force_group or folder or default_group,
                            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        existing_urls.add(xml_url)
                        imported.append(name)
                else:
                    walk_folder(outline, folder)

        body = root.find("body")
        if body is None:
            return {"ok": False, "msg": "OPML 缺少 <body> 节点"}
        walk(body)

        self._save_feeds(feeds)
        # 导入后立刻拉取新源，让前端马上看到内容
        for f in feeds[-len(imported):]:
            self._refresh_one(f["url"])

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "msg": f"成功导入 {len(imported)} 个，跳过 {len(skipped)} 个已存在源",
        }

    # ========== 已读标记：单条 ==========
    def api_read(self, payload: dict = None, method: str = "POST", **_):
        """
        POST：标记已读  {feed_url, entry_id, read: true}
        DELETE：标记未读（改 status 参数或 DELETE 方法）  {feed_url, entry_id}
        若不传 entry_id 而只传 feed_url，则对该源全部文章生效。
        """
        body = payload or {}
        feed_url = (body.get("feed_url") or body.get("feedUrl") or "").strip()
        entry_id = (body.get("entry_id") or body.get("entryId") or "").strip()
        is_read = body.get("read", True)
        # DELETE 方法一律视为「标为未读」
        if method == "DELETE":
            is_read = False

        if not feed_url:
            return {"ok": False, "msg": "缺少 feed_url"}
        if entry_id:
            key = self._read_key(feed_url, entry_id)
            if is_read:
                self._read_status[key] = {
                    "read": True,
                    "read_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            else:
                self._read_status.pop(key, None)
            self._save_read_status()
            return {"ok": True, "read": is_read}
        else:
            # 对该源全部文章标记
            return self._mark_feed_read(feed_url, read=is_read)

    # ========== 已读标记：全部 ==========
    def api_read_all(self, payload: dict = None, **_):
        """
        POST {feed_url?: "..."}
        - 提供 feed_url：将该源所有文章标为已读
        - 不提供：将所有源标为已读
        """
        feed_url = ((payload or {}).get("feed_url") or "").strip()
        if feed_url:
            return self._mark_feed_read(feed_url, read=True)
        # 全部源
        self._maybe_load_cache()
        count = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for furl, data in self._articles.items():
            for entry in data.get("entries", []):
                key = self._read_key(furl, entry.get("id") or entry.get("link"))
                if key not in self._read_status:
                    self._read_status[key] = {"read": True, "read_at": now}
                    count += 1
        self._save_read_status()
        return {"ok": True, "marked": count, "msg": f"已将全部 {count} 篇未读文章标为已读"}

    # ---- 已读标记辅助 ----
    def _mark_feed_read(self, feed_url: str, read: bool):
        """将单个源的文章全部标记为 read / 未读。"""
        self._maybe_load_cache()
        data = self._articles.get(feed_url, {})
        entries = data.get("entries", [])
        count = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for entry in entries:
            key = self._read_key(feed_url, entry.get("id") or entry.get("link"))
            if read:
                if key not in self._read_status:
                    self._read_status[key] = {"read": True, "read_at": now}
                    count += 1
            else:
                if key in self._read_status:
                    self._read_status.pop(key)
                    count += 1
        self._save_read_status()
        return {
            "ok": True,
            "marked": count,
            "msg": f"{'已读' if read else '未读'}: {count} 篇",
        }

    @staticmethod
    def _read_key(feed_url: str, entry_id) -> str:
        """已读状态的键：源地址 + 文章 id（缺失时回退 link）。"""
        eid = str(entry_id or "").strip()
        if not eid:
            eid = "unknown"
        # 归一化：去掉尾部斜杠差异
        base = feed_url.rstrip("/")
        return f"{base}::{eid}"

    def _is_read(self, feed_url: str, entry) -> bool:
        key = self._read_key(feed_url, entry.get("id") or entry.get("link"))
        return bool(self._read_status.get(key, {}).get("read"))

    def _load_read_status(self) -> dict:
        try:
            with open(self._read_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_read_status(self):
        try:
            with open(self._read_file, "w", encoding="utf-8") as f:
                json.dump(self._read_status, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 已读状态写入失败: {e}")

    def _maybe_gc_read_status(self):
        """
        已读记录可能随文章过期而堆积。当记录数超过文章总数一定倍数时，
        清理那些在当前缓存里已找不到对应文章的状态（惰性 GC，避免频繁 IO）。
        """
        if len(self._read_status) < 2000:
            return
        self._maybe_load_cache()
        valid = set()
        for furl, data in self._articles.items():
            for entry in data.get("entries", []):
                valid.add(self._read_key(furl, entry.get("id") or entry.get("link")))
        for key in list(self._read_status.keys()):
            if key not in valid:
                self._read_status.pop(key, None)
        self._save_read_status()

    # ==================================================================
    # 规则通知模块
    # ==================================================================
    # 规则数据结构：
    # {
    #   "id": "r_xxx",              # 唯一标识
    #   "name": "重要科技新闻",
    #   "fields": ["title"],         # 匹配字段：title/description/author/category/link（多选）
    #   "match_type": "contains",    # contains（关键词，大小写不敏感）/ contains_case / regex / exact
    #   "keywords": ["AI", "GPT"],   # 正向关键词列表（OR 逻辑，任一命中即触发）
    #   "feed_urls": ["全部" 或 [url,...]],  # 适用订阅源；["__all__"] 或空 = 全部
    #   "channel": "MessageCenter",  # 单条规则的通知渠道（覆盖全局默认）
    #   "enabled": True,
    #   "created_at": "..."
    # }
    VALID_FIELDS = ("title", "description", "author", "category", "link")
    VALID_MATCH_TYPES = ("contains", "contains_case", "regex", "exact")

    # ---- 字段提取：从 entry 中取出各字段的文本列表 ----
    def _entry_field_values(self, entry: dict, field: str) -> list:
        """返回该字段对应的文本值列表（category 可能多个）。"""
        if field == "title":
            return [entry.get("title", "") or ""]
        if field == "description":
            # 摘要优先纯文本，其次 HTML（strip 后）
            summary = entry.get("summary", "") or ""
            content = entry.get("content", "") or ""
            return [summary or _strip_tags(content)]
        if field == "author":
            return [entry.get("author", "") or ""]
        if field == "link":
            return [entry.get("link", "") or ""]
        if field == "category":
            cats = entry.get("category", []) or entry.get("categories", []) or []
            if isinstance(cats, str):
                cats = [cats]
            return [str(c) for c in cats]
        return []

    # ---- 单条规则对单条 entry 的匹配 ----
    def _rule_matches_entry(self, rule: dict, entry: dict, feed_url: str) -> bool:
        """判断某 entry 是否命中某条规则（正向规则，OR 逻辑）。"""
        fields = [f for f in rule.get("fields", []) if f in self.VALID_FIELDS]
        if not fields:
            return False
        keywords = [str(k).strip() for k in rule.get("keywords", []) if str(k).strip()]
        if not keywords:
            return False
        match_type = rule.get("match_type", "contains")

        # 适用范围：feed_urls 为空 / 含 "__all__" / 含当前源 → 生效
        feed_urls = rule.get("feed_urls") or ["__all__"]
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
        if "__all__" not in feed_urls and feed_url not in feed_urls:
            return False

        # 已读条目不通知（需求 #7：与已读状态联动）
        if self._is_read(feed_url, entry):
            return False

        # 遍历字段 × 关键词：任一 (field, keyword) 命中即返回 True（OR）
        for field in fields:
            values = self._entry_field_values(entry, field)
            for value in values:
                value = str(value or "")
                for kw in keywords:
                    if self._single_match(value, kw, match_type):
                        return True
        return False

    @staticmethod
    def _single_match(text: str, keyword: str, match_type: str) -> bool:
        """单个文本 vs 单个关键词的匹配（按 match_type）。"""
        if not text or not keyword:
            return False
        if match_type == "regex":
            try:
                return re.search(keyword, text) is not None
            except re.error:
                # 正则非法时退化为普通包含（大小写不敏感）
                return keyword.lower() in text.lower()
        if match_type == "exact":
            return text == keyword
        if match_type == "contains_case":
            return keyword in text
        # 默认 contains：大小写不敏感
        return keyword.lower() in text.lower()

    # ---- 收集该 entry 命中的所有规则（用于通知 + 日志）----
    def _matched_rules(self, entry: dict, feed_url: str) -> list:
        """返回命中的规则列表（按优先级/顺序）。"""
        result = []
        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            if self._rule_matches_entry(rule, entry, feed_url):
                result.append(rule)
        return result

    # ---- 核心：刷新后对新条目执行匹配与通知 ----
    def _process_notify(self, articles: dict):
        """
        遍历所有源的新条目（已在 refresh_all 中更新到 self._articles），
        对每条未通知过的条目匹配规则，命中即发送通知并标记为已通知。
        去重：以 "feed_url::entry_id" 为键记录到 notified_entries.json。
        通知后自动标记该条目为已读（需求 #7）。
        """
        if not self._rules:
            return
        # 上一次缓存（用于判断"新条目"）；首次运行时 _articles 已是全量，仅首条不重复通知
        for feed_url, data in articles.items():
            feed_name = data.get("title", "") or feed_url
            for entry in data.get("entries", []):
                entry_id = entry.get("id") or entry.get("link") or ""
                if not entry_id:
                    continue
                key = self._notified_key(feed_url, entry_id)
                # 去重：已通知过的不再发（需求 #6）
                if key in self._notified:
                    continue
                # 已读条目跳过（联动）
                if self._is_read(feed_url, entry):
                    # 已读但从未通知：补登记，避免下次重复判断
                    self._notified[key] = {"at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    continue

                matched = self._matched_rules(entry, feed_url)
                if not matched:
                    continue

                # 命中：发送通知（逐条即时，需求 #5）
                for rule in matched:
                    self._send_notification(rule, entry, feed_name, feed_url)
                    self._notified[key] = {
                        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "rule": rule.get("name", ""),
                        "title": entry.get("title", ""),
                    }
                    # 通知成功后标记已读（需求 #7）
                    self._mark_read(feed_url, entry)
                    # 逐条即停：一条 entry 只对应一次通知，避免多规则重复骚扰
                    break

        self._save_notified()

    def _notified_key(self, feed_url: str, entry_id) -> str:
        return f"{feed_url.rstrip('/')}::{str(entry_id).strip()}"

    def _mark_read(self, feed_url: str, entry):
        """通知后标记已读（不触发额外 IO，仅更新内存 + 落盘）。"""
        key = self._read_key(feed_url, entry.get("id") or entry.get("link"))
        if key not in self._read_status:
            self._read_status[key] = {
                "read": True,
                "read_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_read_status()

    # ---- 发送通知：优先 MP MessageCenter，其次各渠道 ----
    def _send_notification(self, rule: dict, entry: dict, feed_name: str, feed_url: str):
        title = entry.get("title", "") or "(无标题)"
        link = entry.get("link", "") or ""
        rule_name = rule.get("name", "")
        channel = rule.get("channel") or self.get_config("notify_channel", "MessageCenter")
        template = self.get_config(
            "notify_template",
            "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
        )
        text = template.format(
            feed=feed_name, title=title, link=link, rule=rule_name,
            published=entry.get("published", ""),
        )
        try:
            # 1) 统一写入 MP 站内消息中心（任何渠道都会同时落一条）
            self._push_message_center(title=f"[RSS阅读器] {rule_name}", text=text)
        except Exception as e:
            logger.warning(f"[{PLUGIN_NAME}] 站内消息写入失败: {e}")

        # 2) 按渠道调用 MP 已配置的通知方式
        try:
            if channel == "MessageCenter":
                pass  # 已写入站内消息中心
            elif channel == "Telegram":
                self._push_via_mp("telegram", title=title, text=text)
            elif channel == "ServerChan":
                self._push_via_mp("serverchan", title=title, text=text)
            elif channel == "PushPlus":
                self._push_via_mp("pushplus", title=title, text=text)
            elif channel == "WeChatWork":
                self._push_via_mp("wechatwork", title=title, text=text)
            elif channel == "Webhook":
                self._push_webhook(text=text, entry=entry, rule=rule, feed=feed_name)
            logger.info(
                f"[{PLUGIN_NAME}] 规则通知 ✓ [{channel}] {rule_name}: {title}"
            )
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 通知发送失败 [{channel}]: {e}")

        # 3) 追加到通知记录（前端"最近通知记录"）
        self._append_notify_log({
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rule": rule_name,
            "channel": channel,
            "feed": feed_name,
            "title": title,
            "link": link,
        })

    def _push_message_center(self, title: str, text: str):
        """
        写入 MP 站内消息中心。
        优先使用 MessageCenterHelper（MP 推荐），失败时降级为 schemas.Notification。
        """
        try:
            from app.helper import MessageCenterHelper
            MessageCenterHelper.put(msg=text, title=title, role="plugin")
        except Exception:
            # 降级：通过 Notification 表
            try:
                from app.schemas import NotificationType
                from app.db import db
                from app.models import Notification
                with db.context() as session:
                    session.add(Notification(
                        title=title,
                        text=text,
                        type=NotificationType.Info,
                    ))
            except Exception as e:
                logger.debug(f"[{PLUGIN_NAME}] 降级通知也失败: {e}")

    def _push_via_mp(self, channel_key: str, title: str, text: str):
        """
        调用 MP 已配置的通知渠道。
        MP 通过 SystemConfig 管理各渠道，插件不直接持有客户端；
        这里通过 MessageCenterHelper 的统一入口发送（其内部会按启用渠道分发）。
        若运行环境版本不支持，则仅记录日志（不影响站内消息）。
        """
        try:
            from app.helper import MessageCenterHelper
            # send_message 会按 MP 全局配置的实际渠道（Telegram/ServerChan 等）分发
            if hasattr(MessageCenterHelper, "send_message"):
                MessageCenterHelper.send_message(
                    title=title, text=text, channel=channel_key,
                )
            else:
                # 无 send_message 时退化为 put（仅站内）
                MessageCenterHelper.put(msg=text, title=title, role="plugin")
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] {channel_key} 分发跳过: {e}")

    def _push_webhook(self, text: str, entry: dict, rule: dict, feed: str):
        """Webhook 渠道：POST JSON 到配置的地址。"""
        webhook_url = self.get_config("webhook_url", "") or ""
        if not webhook_url:
            logger.debug(f"[{PLUGIN_NAME}] Webhook 未配置 webhook_url，跳过")
            return
        payload = {
            "plugin": PLUGIN_NAME,
            "rule": rule.get("name"),
            "feed": feed,
            "title": entry.get("title"),
            "link": entry.get("link"),
            "author": entry.get("author"),
            "published": entry.get("published"),
            "text": text,
        }
        _http_post_json(webhook_url, payload)

    def _append_notify_log(self, record: dict):
        max_log = int(self.get_config("max_notify_log", 200))
        log = self._load_notify_log()
        log.insert(0, record)
        if len(log) > max_log:
            log = log[:max_log]
        self._save_notify_log(log)

    # ================= 规则 API =================
    def api_rules(self, url: str = None, method: str = "GET", payload: dict = None, **_):
        """
        GET：规则列表（附命中预览统计）
        POST：新建规则
        DELETE ?id=xxx：删除规则
        """
        if method == "POST":
            rule, err = self._validate_rule(payload or {})
            if err:
                return {"ok": False, "msg": err}
            rule["id"] = rule.get("id") or f"r_{int(time.time()*1000)}"
            rule.setdefault("enabled", True)
            rule.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self._rules.append(rule)
            self._save_rules()
            return {"ok": True, "rules": self._rules_with_stats()}
        if method == "DELETE":
            rule_id = (url or "").strip() or ((payload or {}).get("id") or "").strip()
            if not rule_id:
                return {"ok": False, "msg": "缺少规则 id"}
            before = len(self._rules)
            self._rules = [r for r in self._rules if r.get("id") != rule_id]
            self._save_rules()
            return {
                "ok": len(self._rules) < before,
                "rules": self._rules_with_stats(),
                "msg": "已删除" if len(self._rules) < before else "未找到该规则",
            }
        return {"ok": True, "rules": self._rules_with_stats()}

    def _validate_rule(self, payload: dict) -> tuple:
        """校验并返回 (rule_dict, error_msg)。"""
        name = (payload.get("name") or "").strip()
        if not name:
            return None, "规则名称不能为空"
        fields = [f for f in (payload.get("fields") or []) if f in self.VALID_FIELDS]
        if not fields:
            return None, f"至少选择一个匹配字段（{', '.join(self.VALID_FIELDS)}）"
        match_type = payload.get("match_type", "contains")
        if match_type not in self.VALID_MATCH_TYPES:
            return None, f"不支持的匹配方式：{match_type}"
        keywords = [str(k).strip() for k in (payload.get("keywords") or []) if str(k).strip()]
        if not keywords:
            return None, "至少需要一个正向关键词"
        if match_type == "regex":
            for kw in keywords:
                try:
                    re.compile(kw)
                except re.error as e:
                    return None, f"正则无效「{kw}」: {e}"
        feed_urls = payload.get("feed_urls") or ["__all__"]
        if isinstance(feed_urls, str):
            feed_urls = [feed_urls]
        return {
            "name": name,
            "fields": fields,
            "match_type": match_type,
            "keywords": keywords,
            "feed_urls": feed_urls,
            "channel": (payload.get("channel") or "").strip(),
            "enabled": bool(payload.get("enabled", True)),
        }, None

    def _rules_with_stats(self) -> list:
        """给规则列表附加上次命中时间（来自通知记录）。"""
        log = self._load_notify_log()
        last_hit = {}
        for rec in log:
            name = rec.get("rule")
            if name and name not in last_hit:
                last_hit[name] = rec.get("at")
        out = []
        for r in self._rules:
            item = dict(r)
            item["last_hit"] = last_hit.get(r.get("name"), "")
            out.append(item)
        return out

    # ---- 规则测试（不发送通知，仅返回匹配结果）----
    def api_rules_test(self, payload: dict = None, **_):
        """
        对当前缓存的所有文章试运行规则，返回命中的条目（不发送通知、不写记录）。
        用法：前端"测试规则"按钮 → POST { fields, match_type, keywords, feed_urls }
        """
        draft, err = self._validate_rule(payload or {})
        if err:
            return {"ok": False, "msg": err}
        self._maybe_load_cache()
        hits = []
        for feed_url, data in self._articles.items():
            feed_name = data.get("title", "") or feed_url
            for entry in data.get("entries", []):
                # 测试时不过滤已读/已通知，方便用户看到全量命中
                if self._rule_matches_entry(draft, entry, feed_url):
                    hits.append({
                        "feed": feed_name,
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })
        return {
            "ok": True,
            "matched": len(hits),
            "hits": hits[:50],  # 最多返回 50 条预览
            "msg": f"试运行完成，共命中 {len(hits)} 条（仅展示前 50 条）",
        }

    # ================= 通知记录 API =================
    def api_notify_log(self, method: str = "GET", **_):
        """GET：最近通知记录；DELETE：清空记录。"""
        if method == "DELETE":
            self._save_notify_log([])
            return {"ok": True, "msg": "已清空通知记录"}
        log = self._load_notify_log()
        return {"ok": True, "log": log}

    # ================= 规则持久化 =================
    def _load_rules(self) -> list:
        try:
            with open(self._rules_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_rules(self):
        with open(self._rules_file, "w", encoding="utf-8") as f:
            json.dump(self._rules, f, ensure_ascii=False, indent=2)

    def _load_notified(self) -> dict:
        try:
            with open(self._notified_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_notified(self):
        try:
            with open(self._notified_file, "w", encoding="utf-8") as f:
                json.dump(self._notified, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 通知去重记录写入失败: {e}")

    def _load_notify_log(self) -> list:
        notify_log_file = os.path.join(self._data_dir or "", "notify_log.json")
        if not self._data_dir:
            return []
        try:
            with open(notify_log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_notify_log(self, log: list):
        if not self._data_dir:
            return
        notify_log_file = os.path.join(self._data_dir, "notify_log.json")
        try:
            with open(notify_log_file, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 通知记录写入失败: {e}")

    # ================= 前端页面（Vuetify JSON） =================
    def get_page(self) -> dict:
        """
        在 MP 导航中注册一个页面。Vue SFC 源码放在同目录 page.vue，
        运行时由 MP 挂载到主界面（通过 PluginAPI 调用上面注册的 API）。

        页面包含：
          - 订阅源管理（添加/删除/OPML 导入导出）
          - 文章列表（已读/未读状态、未读数角标）
          - 图片画廊（点开文章看全部图片，走代理）
          - 已读标记（打开自动标已读、单条切换、全部标已读）
          - 通知规则（CRUD、字段/匹配方式/关键词/渠道配置、测试、最近通知记录）
        """
        return {
            "name": "RSS 阅读器",
            "icon": "mdi-rss",
            "path": "/rsshub-reader",
            "component": self._load_vue(),
        }

    def _load_vue(self) -> str:
        """读取同目录 page.vue，避免 Python 字符串里花括号/引号冲突。"""
        vue_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.vue")
        try:
            with open(vue_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 读取 page.vue 失败: {e}")
            return "<template><div>页面加载失败</div></template>"

    # ================= 内部：数据存取 =================
    def _load_feeds(self) -> list:
        try:
            with open(self._feeds_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_feeds(self, feeds: list):
        with open(self._feeds_file, "w", encoding="utf-8") as f:
            json.dump(feeds, f, ensure_ascii=False, indent=2)

    def _save_cache(self, articles: dict):
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 缓存写入失败: {e}")

    def _maybe_load_cache(self):
        """启动时若内存为空，先从磁盘缓存恢复（避免重启后页面空白）。"""
        if self._articles:
            return
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                self._articles = json.load(f)
        except Exception:
            self._articles = {}

    def _refresh_one(self, feed_url: str):
        try:
            fetch_full = bool(self.get_config("fetch_full", True))
            max_entries = int(self.get_config("max_entries", 50))
            data = parse_feed(feed_url, fetch_full=fetch_full)
            data["entries"] = data["entries"][:max_entries]
            self._articles[feed_url] = data
            self._save_cache(self._articles)
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 单源刷新失败 {feed_url}: {e}")

    def _blank_pixel(self):
        import base64
        from fastapi.responses import Response
        # 1x1 透明 GIF
        gif = base64.b64decode(
            "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        )
        return Response(content=gif, media_type="image/gif")

    def get_config(self, key: str, default=None):
        """读取当前插件配置（由 MP 配置表单持久化）。"""
        try:
            config = self.config or {}
            return config.get(key, default)
        except Exception:
            return default


# 让 MP 能 import 到类（兼容部分加载方式）
__all__ = ["RsshubReader"]
