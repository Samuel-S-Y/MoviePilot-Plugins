# -*- coding: utf-8 -*-
"""
RSSHubReader - MoviePilot 资讯源阅读器插件

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
  - Vue 全页前端（模块联邦构建产物 dist/assets）：订阅源管理 + 文章列表 + 图片画廊 + 通知规则管理

技术栈：feedparser（RSS/Atom）+ requests（正文抓取）+ BeautifulSoup（提取图片）
前端需先在插件目录执行 npm install && npm run build，产物提交到 dist/assets。
"""

import os
import io
import re
import json
import time
import hashlib
from datetime import datetime
from urllib.parse import urljoin
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
    from app.log import logger
    from app.plugins import _PluginBase
    from app.schemas import MessageChannel, NotificationType
except ImportError:  # pragma: no cover - 本地测试桩
    import logging

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    class MessageChannel:
        Telegram = "Telegram"
        Feishu = "Feishu"
        Slack = "Slack"
        Discord = "Discord"
        WebPush = "WebPush"

    class NotificationType:
        Plugin = "plugin"
        Info = "info"

    class _PluginBase:
        def init_plugin(self, config: dict = None):
            pass

        def get_state(self) -> bool:
            return True

        def get_api(self):
            return []

        def get_form(self):
            return [], {}

        def get_page(self):
            return None

        def get_service(self):
            return []

        def stop_service(self):
            pass

        def get_config(self, plugin_id: str = None):
            return {}

        def get_data_path(self, plugin_id: str = None):
            path = os.path.join(os.path.dirname(__file__), "_test_data", self.__class__.__name__)
            os.makedirs(path, exist_ok=True)
            return path

        def post_message(self, channel=None, mtype=None, title=None, text=None,
                         image=None, link=None, **kwargs):
            logger.info(f"[插件桩] post_message: {title} | {text}")


# FastAPI 类型：仅在 MP 运行时存在；本地测试桩下为 None（接口由 MP 的 add_api_route 调用）
try:
    from fastapi import Request
    from fastapi.responses import Response
except ImportError:  # pragma: no cover - 本地测试桩
    Request = None
    Response = None


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
            # 保留完整 URL（含 query）：部分 CDN 图片地址带签名参数，截断会导致 403
            abs_url = _absolutize(base_url, c)
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
                # 保留完整 URL（含 query）：部分 CDN 图片地址带签名参数，截断会导致 403
                u = _absolutize(base_url, c)
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
        return _parse_feed_feedparser(resp.content, fetch_full)
    return _parse_feed_stdlib(resp.content, fetch_full)


def _parse_feed_feedparser(content: bytes, fetch_full: bool) -> dict:
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


def _parse_feed_stdlib(content: bytes, fetch_full: bool) -> dict:
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
    plugin_version = "1.3.0"
    plugin_author = "your-name"

    # ---- 通知渠道映射：规则 channel → MP 消息渠道（None 表示走 MP 默认分发）----
    _CHANNEL_MAP = {
        "MessageCenter": None,
        "Telegram": MessageChannel.Telegram,
        "Feishu": MessageChannel.Feishu,
        "Slack": MessageChannel.Slack,
        "Discord": MessageChannel.Discord,
        "WebPush": MessageChannel.WebPush,
    }

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
    def init_plugin(self, config: dict = None):
        """
        MP V2 生命周期入口：插件加载/配置变更时调用。
        幂等：重载时不重复初始化内存状态（_initialized 守护）。
        """
        self._config = config or {}
        if getattr(self, "_initialized", False):
            return
        # 数据目录由 MP 基类提供（插件数据根目录下）
        self._data_dir = str(self.get_data_path())
        os.makedirs(self._data_dir, exist_ok=True)
        self._feeds_file = os.path.join(self._data_dir, "feeds.json")
        self._cache_file = os.path.join(self._data_dir, "articles.json")
        self._read_file = os.path.join(self._data_dir, "read_status.json")
        self._rules_file = os.path.join(self._data_dir, "notify_rules.json")
        self._notified_file = os.path.join(self._data_dir, "notified_entries.json")
        # 内存状态（首次启动时为空；已在 refresh_all 中惰性恢复缓存）
        self._articles = getattr(self, "_articles", {})
        self._read_status = self._load_read_status()
        self._rules = self._load_rules()
        self._notified = self._load_notified()
        self._initialized = True
        logger.info(f"[{PLUGIN_NAME}] 数据目录: {self._data_dir}")

    def get_state(self) -> bool:
        """插件启用状态（配置表单 enabled 开关）。"""
        return bool(self._cfg("enabled", True))

    def stop_service(self):
        """插件停止/卸载时调用：落盘内存状态，避免丢失。"""
        try:
            self._save_read_status()
            self._save_notified()
            self._save_rules()
        except Exception:
            pass
        logger.info(f"[{PLUGIN_NAME}] 服务已停止")

    # ================= 配置表单 =================
    def get_form(self) -> tuple:
        """
        后台“设置”页的表单（Vuetify JSON + 默认值字典）。
        源列表管理放到前端页面（增删更友好）。
        """
        fields = [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {"component": "VSwitch", "props": {"model": "enabled", "label": "启用插件"}}
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 8},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "rsshub_base_url",
                                            "label": "RSSHub 地址",
                                            "hint": "局域网 RSSHub 访问地址，如 http://192.168.1.100:1200",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "poll_interval",
                                            "label": "刷新间隔（分钟）",
                                            "type": "number",
                                            "hint": "定时拉取所有订阅源的周期，建议 15~60",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "max_entries",
                                            "label": "每个源保留条数",
                                            "type": "number",
                                            "hint": "最多保留的文章数，避免内存膨胀",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "max_notify_log",
                                            "label": "通知记录保留条数",
                                            "type": "number",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "fetch_full", "label": "抓取正文提取完整图片"},
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "proxy_images", "label": "启用后端图片代理"},
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "mark_read_on_open", "label": "打开文章自动标为已读"},
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "notify_enabled", "label": "启用规则通知"},
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "opml_group",
                                            "label": "OPML 默认分组",
                                            "hint": "OPML 导入时未指定分组的源归入此分组",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 8},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "notify_template",
                                            "label": "通知内容模板",
                                            "hint": "支持变量：{title} {feed} {link} {rule} {published}",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "notify_channel",
                                            "label": "默认通知渠道",
                                            "items": [
                                                {"title": "MessageCenter（默认分发）", "value": "MessageCenter"},
                                                {"title": "Telegram", "value": "Telegram"},
                                                {"title": "飞书", "value": "Feishu"},
                                                {"title": "Slack", "value": "Slack"},
                                                {"title": "Discord", "value": "Discord"},
                                                {"title": "WebPush", "value": "WebPush"},
                                                {"title": "Webhook", "value": "Webhook"},
                                            ],
                                            "hint": "命中规则时的默认通知渠道；单条规则可单独指定",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "webhook_url",
                                            "label": "Webhook 地址",
                                            "hint": "渠道选择 Webhook 时，命中规则将 POST JSON 到此地址",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ]
        defaults = {
            "enabled": True,
            "rsshub_base_url": "http://127.0.0.1:1200",
            "poll_interval": 30,
            "max_entries": 50,
            "max_notify_log": 200,
            "fetch_full": True,
            "proxy_images": True,
            "mark_read_on_open": True,
            "notify_enabled": True,
            "opml_group": "导入",
            "notify_template": "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
            "notify_channel": "MessageCenter",
            "webhook_url": "",
        }
        return fields, defaults

    # ================= 定时任务 =================
    def get_service(self) -> list:
        """
        注册定时刷新任务（MP V2：返回服务列表，按配置的 poll_interval 周期调用 refresh_all）。
        """
        if not self.get_state():
            return []
        interval = max(5, int(self._cfg("poll_interval", 30)))
        return [{
            "id": "rsshub_reader_refresh",
            "name": "RSS 源定时刷新",
            "trigger": "interval",
            "func": self.refresh_all,
            "kwargs": {"minutes": interval},
        }]

    # ---- 对外：供 API / 前端触发手动刷新 ----
    def refresh_all(self, *_args, **_kwargs):
        """遍历所有订阅源并拉取，结果同时写内存与磁盘缓存。"""
        # 先恢复磁盘缓存：重启后首次刷新时，失败的源可以从旧缓存兜底，不会被清空
        self._maybe_load_cache()
        feeds = self._load_feeds()
        if not feeds:
            logger.debug(f"[{PLUGIN_NAME}] 暂无订阅源，跳过刷新")
            return

        max_entries = int(self._cfg("max_entries", 50))
        fetch_full = bool(self._cfg("fetch_full", True))

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
        # 刷新后清理失效的已读/已通知记录（惰性，仅在记录量大时真正执行）
        self._maybe_gc_read_status()
        self._maybe_gc_notified()
        # 规则通知：仅对新出现的条目进行匹配（去重 + 已读联动在 match 内部处理）
        if bool(self._cfg("notify_enabled", True)):
            self._process_notify(articles)

    # ================= 自定义 API =================
    def get_api(self) -> list:
        """
        暴露给前端的 HTTP 接口（由 MP 统一挂载在 /api/v1/plugin/{plugin_name}/...）。
        MP 会将该字典直接展开传给 app.add_api_route，因此：
          - path 必须以 / 开头；
          - endpoint 使用框架要求的字段名（不能是 func）；
          - 前端页面调用的接口使用 auth=bear（与前端 pluginApi 的 token 配套）；
          - proxy 为 <img> 直链，标记 allow_anonymous，服务端做白名单校验防 SSRF。
        """
        return [
            {
                "path": "/feeds",
                "endpoint": self.api_feeds,
                "methods": ["GET", "POST", "DELETE"],
                "auth": "bear",
                "summary": "订阅源管理（列表/添加/删除）",
            },
            {
                "path": "/articles",
                "endpoint": self.api_articles,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取所有/指定源的文章",
            },
            {
                "path": "/refresh",
                "endpoint": self.api_refresh,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "手动触发刷新",
            },
            {
                "path": "/proxy",
                "endpoint": self.api_proxy,
                "methods": ["GET"],
                "allow_anonymous": True,
                "summary": "图片代理（仅允许缓存中的图片地址，防 SSRF）",
            },
            # ---- OPML 导入/导出 ----
            {
                "path": "/opml/export",
                "endpoint": self.api_opml_export,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "导出 OPML（订阅源备份/迁移，返回文本由前端生成下载）",
            },
            {
                "path": "/opml/import",
                "endpoint": self.api_opml_import,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "导入 OPML（从其它阅读器迁移订阅源）",
            },
            # ---- 已读/未读标记 ----
            {
                "path": "/read",
                "endpoint": self.api_read,
                "methods": ["POST", "DELETE"],
                "auth": "bear",
                "summary": "标记单条已读/未读",
            },
            {
                "path": "/read/all",
                "endpoint": self.api_read_all,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "将指定源（或全部）标记为已读",
            },
            # ---- 规则通知 ----
            {
                "path": "/rules",
                "endpoint": self.api_rules,
                "methods": ["GET", "POST", "DELETE"],
                "auth": "bear",
                "summary": "通知规则管理（列表/添加/删除）",
            },
            {
                "path": "/rules/test",
                "endpoint": self.api_rules_test,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "测试规则匹配（对当前缓存文章试运行，不发送通知）",
            },
            {
                "path": "/notify/log",
                "endpoint": self.api_notify_log,
                "methods": ["GET", "DELETE"],
                "auth": "bear",
                "summary": "通知记录（查询/清空）",
            },
        ]

    @staticmethod
    async def _read_json_body(request) -> dict:
        """
        读取请求体 JSON（FastAPI Request 注入）。
        无 body / 非 JSON 时返回空字典，避免接口因缺 body 直接 422。
        """
        try:
            return await request.json() or {}
        except Exception:
            return {}

    # ---- API 实现 ----
    async def api_feeds(self, request) -> dict:
        """
        GET 列表（附分组、未读数）/ POST 添加 / DELETE 删除。
        添加时支持 group 字段，便于 OPML 导入与前端分组管理。
        """
        method = request.method
        params = dict(request.query_params)
        body = await self._read_json_body(request)
        feeds = self._load_feeds()
        if method == "POST":
            url = str(body.get("url") or "").strip()
            name = str(body.get("name") or "").strip()
            group = str(body.get("group") or "").strip()
            site_url = str(body.get("site_url") or "").strip()
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
            # 删除：url 从请求体或 query 参数读取（DELETE 请求体可能被某些客户端丢弃）
            del_url = str(body.get("url") or params.get("url") or "").strip()
            if not del_url:
                return {"ok": False, "msg": "缺少 url 参数"}
            feeds = [f for f in feeds if f.get("url") != del_url]
            self._save_feeds(feeds)
            self._articles.pop(del_url, None)
            self._save_cache(self._articles)
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

    def api_articles(self, url: str = None) -> dict:
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

    def api_refresh(self) -> dict:
        """手动触发全量刷新（POST /refresh）。"""
        try:
            self.refresh_all()
            return {"ok": True, "msg": "刷新完成"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def _is_allowed_proxy_url(self, url: str) -> bool:
        """
        图片代理白名单：仅允许当前文章缓存中出现过的图片地址。
        防止 /proxy 被当作任意 URL 代理（SSRF/内网探测）。
        """
        self._maybe_load_cache()
        allowed = set()
        for data in self._articles.values():
            for entry in data.get("entries", []):
                thumb = entry.get("thumbnail") or ""
                if thumb:
                    allowed.add(thumb)
                for img in (entry.get("images") or []):
                    allowed.add(img)
        return url in allowed

    def api_proxy(self, url: str = None) -> "Response":
        """
        图片代理：前端 <img src="/api/v1/plugin/rsshub_reader/proxy?url=...">
        由后端请求目标图片并返回，绕过防盗链与跨域。
        仅代理缓存中出现过的图片地址（防 SSRF）；匿名可访问（供 <img> 直连）。
        """
        if not url:
            return self._blank_pixel()
        # 仅允许 http/https，且必须在缓存图片白名单内
        if not url.lower().startswith(("http://", "https://")):
            return self._blank_pixel()
        if not self._is_allowed_proxy_url(url):
            logger.warning(f"[{PLUGIN_NAME}] 代理请求被拒绝（不在缓存白名单内）: {url}")
            return self._blank_pixel()
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
    def api_opml_export(self) -> dict:
        """
        将所有订阅源导出为 OPML 2.0 格式（text/xml）。
        兼容 Feedly / Inoreader / Miniflux / FreshRSS 等主流阅读器，
        导入时通过 <outline> 的 type="rss" xmlUrl 属性识别。
        返回 JSON {filename, content}，由前端在浏览器侧生成下载文件
        （避免二进制 Response 经鉴权/包装后无法触发下载）。
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
        content = xml_bytes.getvalue().decode("utf-8")

        filename = f"rsshub_reader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.opml"
        return {"ok": True, "filename": filename, "content": content}

    # ========== OPML 导入 ==========
    async def api_opml_import(self, request: Request) -> dict:
        """
        解析 OPML（支持 1.0/1.1/2.0），提取所有 type="rss"/"atom" 的 outline，
        追加到本地订阅源（自动去重）。可选参数：
          - content: OPML 文本字符串（优先）
          - url: 远程 OPML 文件地址（备用）
          - group: 强制归到指定分组（覆盖 OPML 内的 folder 结构）
        """
        payload = await self._read_json_body(request)
        content = str(payload.get("content") or "").strip()
        remote_url = str(payload.get("url") or "").strip()
        force_group = str(payload.get("group") or "").strip()

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
        default_group = force_group or self._cfg("opml_group", "导入")

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
        # 导入后立刻拉取新源，让前端马上看到内容（无新增时跳过，避免误刷新全部）
        if imported:
            for f in feeds[-len(imported):]:
                self._refresh_one(f["url"])

        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "msg": f"成功导入 {len(imported)} 个，跳过 {len(skipped)} 个已存在源",
        }

    # ========== 已读标记：单条 ==========
    async def api_read(self, request: Request) -> dict:
        """
        POST：标记已读  {feed_url, entry_id, read: true}
        DELETE：标记未读  {feed_url, entry_id}
        若不传 entry_id 而只传 feed_url，则对该源全部文章生效。
        """
        body = await self._read_json_body(request)
        # 兼容前端 props.api.delete 不带 body 的情况：参数同时接受 query 兜底
        params = dict(request.query_params)
        feed_url = str(body.get("feed_url") or body.get("feedUrl")
                       or params.get("feed_url") or params.get("feedUrl") or "").strip()
        entry_id = str(body.get("entry_id") or body.get("entryId")
                       or params.get("entry_id") or params.get("entryId") or "").strip()
        is_read = body.get("read", True)
        # DELETE 方法一律视为「标为未读」
        if request.method == "DELETE":
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
    async def api_read_all(self, request: Request) -> dict:
        """
        POST {feed_url?: "..."}
        - 提供 feed_url：将该源所有文章标为已读
        - 不提供：将所有源标为已读
        """
        payload = await self._read_json_body(request)
        feed_url = str(payload.get("feed_url") or "").strip()
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

    def _maybe_gc_notified(self):
        """
        通知去重记录（notified_entries.json）与已读记录一样会随文章过期而堆积：
        清理那些当前缓存中已不存在的条目标记，防止文件无限增长。
        """
        if len(self._notified) < 2000:
            return
        self._maybe_load_cache()
        valid = set()
        for furl, data in self._articles.items():
            for entry in data.get("entries", []):
                valid.add(self._notified_key(furl, entry.get("id") or entry.get("link") or ""))
        for key in list(self._notified.keys()):
            if key not in valid:
                self._notified.pop(key, None)
        self._save_notified()

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
    def _rule_matches_entry(self, rule: dict, entry: dict, feed_url: str,
                            ignore_read: bool = False) -> bool:
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

        # 已读条目不通知（需求 #7：与已读状态联动）；规则测试时可通过 ignore_read 跳过
        if not ignore_read and self._is_read(feed_url, entry):
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
                    self._send_notification(rule, entry, feed_name)
                    self._notified[key] = {
                        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "rule": rule.get("name", ""),
                        "title": entry.get("title", ""),
                    }
                    # 通知成功后标记已读（需求 #7）
                    self._mark_read(feed_url, entry)
                    # 逐条即停：一条 entry 只对应一次通知，避免多规则重复骚扰
                    break

        # 批量落盘：通知去重记录 + 已读状态（避免每条命中都触发一次磁盘 IO）
        self._save_notified()
        self._save_read_status()

    def _notified_key(self, feed_url: str, entry_id) -> str:
        return f"{feed_url.rstrip('/')}::{str(entry_id).strip()}"

    def _mark_read(self, feed_url: str, entry):
        """通知后标记已读（仅更新内存；落盘由调用方批量完成，避免频繁 IO）。"""
        key = self._read_key(feed_url, entry.get("id") or entry.get("link"))
        if key not in self._read_status:
            self._read_status[key] = {
                "read": True,
                "read_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

    # ---- 发送通知：统一走 MP 通知组件（含站内消息中心），Webhook 走自定义通道 ----
    def _send_notification(self, rule: dict, entry: dict, feed_name: str):
        title = entry.get("title", "") or "(无标题)"
        link = entry.get("link", "") or ""
        rule_name = rule.get("name", "")
        channel = rule.get("channel") or self._cfg("notify_channel", "MessageCenter")
        template = self._cfg(
            "notify_template",
            "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
        )
        text = template.format(
            feed=feed_name, title=title, link=link, rule=rule_name,
            published=entry.get("published", ""),
        )
        try:
            self._push_notification(channel, title, text, link, entry, rule, feed_name)
            logger.info(
                f"[{PLUGIN_NAME}] 规则通知 ✓ [{channel}] {rule_name}: {title}"
            )
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 通知发送失败 [{channel}]: {e}")

        # 追加到通知记录（前端"最近通知记录"）
        self._append_notify_log({
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rule": rule_name,
            "channel": channel,
            "feed": feed_name,
            "title": title,
            "link": link,
        })

    def _push_notification(self, channel: str, title: str, text: str, link: str,
                           entry: dict, rule: dict, feed_name: str):
        """
        按渠道发送通知。
        Webhook 走自定义 POST；其余渠道映射到 MP 的 MessageChannel，
        通过基类 post_message 发送（channel=None 表示 MP 默认分发，含站内消息中心）。
        """
        if channel == "Webhook":
            self._push_webhook(text=text, entry=entry, rule=rule, feed=feed_name)
            return
        self.post_message(
            channel=self._CHANNEL_MAP.get(channel),
            mtype=NotificationType.Plugin,
            title=title,
            text=text,
            link=link or None,
        )

    def _push_webhook(self, text: str, entry: dict, rule: dict, feed: str):
        """Webhook 渠道：POST JSON 到配置的地址。"""
        webhook_url = self._cfg("webhook_url", "") or ""
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
        max_log = int(self._cfg("max_notify_log", 200))
        log = self._load_notify_log()
        log.insert(0, record)
        if len(log) > max_log:
            log = log[:max_log]
        self._save_notify_log(log)

    # ================= 规则 API =================
    async def api_rules(self, request: Request) -> dict:
        """
        GET：规则列表（附命中预览统计）
        POST：新建规则
        DELETE ?id=xxx：删除规则
        """
        method = request.method
        params = dict(request.query_params)
        body = await self._read_json_body(request)
        if method == "POST":
            rule, err = self._validate_rule(body)
            if err:
                return {"ok": False, "msg": err}
            rule["id"] = rule.get("id") or f"r_{int(time.time()*1000)}"
            rule.setdefault("enabled", True)
            rule.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self._rules.append(rule)
            self._save_rules()
            return {"ok": True, "rules": self._rules_with_stats()}
        if method == "DELETE":
            rule_id = str(params.get("id") or body.get("id") or "").strip()
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
    async def api_rules_test(self, request: Request) -> dict:
        """
        对当前缓存的所有文章试运行规则，返回命中的条目（不发送通知、不写记录）。
        用法：前端"测试规则"按钮 → POST { fields, match_type, keywords, feed_urls }
        """
        body = await self._read_json_body(request)
        draft, err = self._validate_rule(body)
        if err:
            return {"ok": False, "msg": err}
        self._maybe_load_cache()
        hits = []
        for feed_url, data in self._articles.items():
            feed_name = data.get("title", "") or feed_url
            for entry in data.get("entries", []):
                # 测试时不过滤已读/已通知，方便用户看到全量命中
                if self._rule_matches_entry(draft, entry, feed_url, ignore_read=True):
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
    async def api_notify_log(self, request: Request) -> dict:
        """GET：最近通知记录；DELETE：清空记录。"""
        if request.method == "DELETE":
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

    # ================= 前端页面（Vue 全页，模块联邦） =================
    @staticmethod
    def get_render_mode() -> tuple:
        """
        渲染模式：vue 全页。
        第二项为构建产物目录（相对插件目录），前端由 MP 远程组件机制加载 dist/assets/remoteEntry.js。
        """
        return "vue", "dist/assets"

    def get_sidebar_nav(self) -> list:
        """在 MP 侧边栏注册页面入口（nav_key 固定 main，前端只暴露 ./AppPage 即可匹配）。"""
        return [
            {
                "nav_key": "main",
                "name": "RSS 阅读器",
                "icon": "mdi-rss",
            }
        ]

    def get_page(self):
        """vue 全页模式：不返回 vuetify 详情页配置。"""
        return None

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
            fetch_full = bool(self._cfg("fetch_full", True))
            max_entries = int(self._cfg("max_entries", 50))
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

    def _cfg(self, key: str, default=None):
        """
        读取当前插件配置。
        优先取 init_plugin 最近一次生效的运行态配置（self._config），
        再回退到基类 get_config()（MP 持久化的配置），避免首次加载未落盘时读到空。
        """
        try:
            config = getattr(self, "_config", None) or self.get_config() or {}
            return config.get(key, default)
        except Exception:
            return default


# 让 MP 能 import 到类（兼容部分加载方式）
__all__ = ["RsshubReader"]
