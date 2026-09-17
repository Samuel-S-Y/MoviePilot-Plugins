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
import ipaddress
import threading
from datetime import datetime
from urllib.parse import urljoin, unquote, urlparse
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

# 线程池执行器：async 端点里调用的抓取/通知都是同步阻塞 IO，
# 用 await run_in_threadpool(...) 执行可避免阻塞事件循环；无 fastapi 时降级为直接调用
try:
    from fastapi.concurrency import run_in_threadpool
except ImportError:  # pragma: no cover - 本地测试桩
    async def run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)


# ---------- 常量 ----------
PLUGIN_NAME = "rsshub_reader"
USER_AGENT = (
    "Mozilla/5.0 (compatible; RSSHubReader/1.0; +https://github.com/jxxghp/MoviePilot)"
)
REQUEST_TIMEOUT = 20
# 单次抓取正文时最多提取的图片数，避免超长页面拖慢
MAX_IMAGES_PER_ENTRY = 30
# 正文纯文本短于此长度即视为「RSS 摘要」，阅读时按需去抓原网页正文
SUMMARY_MAX_CHARS = 200
# 正文提取算法版本号：算法升级（如选择器/装饰图过滤变更）时 +1，
# 让缓存里的旧提取结果自动失效并重新抓取，避免用户升级后仍看到旧数据
CONTENT_VER = 2
# 通知测试（试运行并真实发送）时最多发送的样例条数，避免命中过多造成刷屏
NOTIFY_TEST_SAMPLE = 3
# 单次 OPML 导入的最大订阅源数：导入后会逐个抓取，条数过多会长时间占用线程池与事件循环
MAX_OPML_FEEDS = 200
# 额外的「不可路由」网段：ipaddress 已覆盖 RFC1918/回环/链路本地/保留地址，
# 但运营商级 NAT（100.64.0.0/10）与基准测试网段（198.18.0.0/15）不在 is_private 之内，
# 需单独判定，否则图片代理可被用来探测这类内网地址
EXTRA_PRIVATE_NETS = ("100.64.0.0/10", "198.18.0.0/15")
# 正文容器候选选择器（按优先级）：覆盖主流论坛与 CMS，命中后只保留正文部分，
# 避免抓不到正文容器时回退整页、把站点 logo/横幅等装饰图误当成文章图片
CONTENT_SELECTORS = (
    # 论坛：Flarum / Discuz / phpBB / vBulletin / XenForo
    ".Post-body", ".postbody", ".postmessage", ".post_message", ".t_f",
    ".bbWrapper", ".message-body", ".messageContent",
    # CMS / 博客 / 公众号
    "article", ".post-content", ".entry-content", ".article-content",
    ".rich_media_content", ".markdown-body",
    # 通用兜底
    "main", "[role=main]", ".content", "#content",
)
# 正文去噪：先删掉的标签级噪声
NOISE_TAGS = ("script", "style", "noscript", "nav", "header", "footer",
              "form", "iframe", "aside")
# 正文去噪：站点装饰区块（logo/导航/侧栏/广告等），其中的图片不属于文章内容；
# [aria-hidden=true] 是无障碍语义上的「纯装饰」，常被用于 IDE 皮肤、图标墙等视觉噪声
NOISE_SELECTORS = (
    ".Logo", ".logo", ".site-logo", ".App-header", ".site-header", ".site-footer",
    ".navbar", ".nav-bar", ".sidebar", ".breadcrumb", ".pagination",
    ".ad", ".ads", ".advertisement", ".banner", ".share", ".social",
    "[aria-hidden='true']",
)
# 图片 URL 命中这些关键词即视为站点图标/装饰图（logo、头像、徽章、表情等），不计入文章图片
SKIP_IMAGE_KEYWORDS = (
    "avatar", "placeholder", "pixel.", "1x1.", "blank.gif", "spacer",
    "logo", "sprite", "favicon", "emoji", "smiley", "banner", "watermark",
    "icon", "badge", "/static/image/common", "/static/image/smiley",
)
# 声明尺寸（width/height 属性或 CSS 尺寸类）不超过该像素值的图片，视为图标类装饰图
ICON_MAX_SIZE_PX = 64
# 无 BeautifulSoup 降级解析时，这些标签内的图片一律视为站点装饰图（页眉 logo/导航/页脚）
NOISE_CONTAINER_TAGS = ("header", "footer", "nav", "aside")
# 允许通过代理返回的 Content-Type 白名单（不含 svg：SVG 可携带脚本，代理场景直接拒绝）
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
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


def _best_from_srcset(srcset: str) -> str:
    """
    从 srcset 中取「分辨率最高」的候选地址（描述符 w/x 越大越清晰）。
    取第一个通常是缩略图，会导致正文配图模糊。
    """
    best, best_score = "", -1.0
    for part in (srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        score = 0.0
        if len(bits) > 1:
            try:
                score = float(bits[1].lower().rstrip("wx"))
            except ValueError:
                score = 0.0
        if score > best_score:
            best, best_score = bits[0], score
    return best


def _is_private_host(host: str) -> bool:
    """
    判断主机是否指向内网/保留地址，用于阻止图片代理被当成内网探测工具。
    只做字面量与常见保留名的判断，不做 DNS 解析（避免引入额外延迟与解析抖动）。
    """
    h = (host or "").strip().strip("[]").lower()
    if not h:
        return True
    if h == "localhost" or h.endswith(".local") or h.endswith(".internal"):
        return True
    # 交给标准库 ipaddress 解析：它同时覆盖 IPv6、IPv4-mapped IPv6（::ffff:127.0.0.1）
    # 与各种保留网段属性；此前只做点分十进制正则，下列形式都能绕过内网判断
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # 纯整数/十六进制形式（inet_aton 风格，如 2130706433、0x7f000001）ipaddress 不接受，
        # 用 int(h, 0) 再转一次；失败说明是域名等合法输入，交由上层域名白名单处理，不抛异常
        try:
            ip = ipaddress.ip_address(int(h, 0))
        except (ValueError, TypeError):
            return False
    # IPv4-mapped IPv6 需按内嵌的 IPv4 判断（旧版本 Python 的 is_private 不识别映射地址）
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_unspecified):
        return True
    # is_private 未覆盖的运营商级 NAT / 基准测试网段
    if ip.version == 4:
        for net in EXTRA_PRIVATE_NETS:
            try:
                if ip in ipaddress.ip_network(net):
                    return True
            except ValueError:
                continue
    return False


def _looks_like_site_icon(url: str, attrs: dict = None) -> bool:
    """
    判断一张图片是否属于「站点装饰图/图标」（logo、头像、徽章、表情、导航图标等）。

    依据两类信号（任一命中即判定为装饰图），两类都不依赖 BeautifulSoup，
    因此有/无 bs4 的解析路径都能生效：
      1) URL 关键词：logo、avatar、icon、badge、emoji、sprite 等；
         先做 URL 解码，兼容 Next.js 等站点的 /_next/image?url=%2Fbee%2F... 形式；
      2) 声明尺寸过小：width/height 属性或 CSS 尺寸类（如 h-8、max-w-[76px]）
         换算后不超过 ICON_MAX_SIZE_PX，这类基本是图标而非文章配图。
    """
    probe = unquote(url or "").lower()
    if any(k in probe for k in SKIP_IMAGE_KEYWORDS):
        return True
    if not attrs:
        return False
    # 显式的 width/height 属性
    try:
        w = int(str(attrs.get("width") or 0).strip() or 0)
        h = int(str(attrs.get("height") or 0).strip() or 0)
        if w and h and w <= ICON_MAX_SIZE_PX and h <= ICON_MAX_SIZE_PX:
            return True
    except (TypeError, ValueError):
        pass
    # CSS 尺寸类：Tailwind 的 1 单位 = 4px（h-8 → 32px），以及 max-w-[76px] 这类任意值
    cls = str(attrs.get("class") or "")
    for m in re.finditer(r"(?:^|\s)[hw]-(\d+(?:\.\d+)?)(?=\s|$)", cls):
        try:
            if float(m.group(1)) * 4 <= ICON_MAX_SIZE_PX:
                return True
        except ValueError:
            continue
    for m in re.finditer(r"max-(?:w|h)-\[(\d+)px\]", cls):
        if int(m.group(1)) <= ICON_MAX_SIZE_PX:
            return True
    return False


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
            # 取分辨率最高的候选，避免用了 srcset 里的缩略图
            best_src = _best_from_srcset(srcset)
            if best_src:
                candidates.append(best_src)
        src = img.get("src")
        if src:
            candidates.append(src)
        for c in candidates:
            # 保留完整 URL（含 query）：部分 CDN 图片地址带签名参数，截断会导致 403
            abs_url = _absolutize(base_url, c)
            if not abs_url or abs_url in seen:
                continue
            # 站点装饰图（logo/头像/徽章/表情/小图标）不计入文章图片
            # bs4 的 class 属性是 list，需先扁平化为字符串，
            # 否则尺寸类（如 h-8）的正则匹配失效，装饰图过滤会被削弱
            flat_attrs = {
                k: (" ".join(v) if isinstance(v, (list, tuple)) else v)
                for k, v in img.attrs.items()
            }
            if _looks_like_site_icon(abs_url, flat_attrs):
                continue
            seen.add(abs_url)
            result.append(abs_url)
            if len(result) >= MAX_IMAGES_PER_ENTRY:
                return result
    return result


def _extract_images_stdlib(html: str, base_url: str) -> list:
    """
    无 bs4 时的降级实现（标准库 HTMLParser）。
    会跳过 header/footer/nav/aside 内的图片，避免把站点页眉 logo、导航图标当成文章图片。
    """
    from html.parser import HTMLParser

    class ImgParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []
            self._noise_depth = 0  # >0 表示正处于站点装饰区块内部

        def handle_starttag(self, tag, attrs):
            if tag in NOISE_CONTAINER_TAGS:
                self._noise_depth += 1
                return
            if tag != "img" or self._noise_depth:
                # 也可处理 <source srcset>，这里聚焦 img
                return
            d = dict(attrs)
            cands = []
            for attr in ("data-src", "data-original", "data-url", "data-large"):
                if d.get(attr):
                    cands.append(d[attr])
            if d.get("srcset"):
                # 与 bs4 路径保持一致：取 srcset 中分辨率最高的候选
                best_src = _best_from_srcset(d["srcset"])
                if best_src:
                    cands.append(best_src)
            if d.get("src"):
                cands.append(d["src"])
            for c in cands:
                # 保留完整 URL（含 query）：部分 CDN 图片地址带签名参数，截断会导致 403
                u = _absolutize(base_url, c)
                if u and u not in self.urls:
                    # 站点装饰图（logo/头像/徽章/表情/小图标）不计入文章图片
                    if not _looks_like_site_icon(u, d):
                        self.urls.append(u)

        def handle_endtag(self, tag):
            if tag in NOISE_CONTAINER_TAGS and self._noise_depth:
                self._noise_depth -= 1

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


def _clean_article_html(html: str, base_url: str) -> str:
    """
    把抓取到的网页 HTML 清洗成可读的文章正文：
      1) 删除脚本、导航、页眉页脚、侧栏、广告等小区块（避免站点装饰图混入文章图片）；
      2) 按优先级定位正文容器（覆盖 Flarum/Discuz 等论坛与常见 CMS），只保留正文；
      3) 把 img 的相对地址转成绝对地址，避免前端 v-html 渲染时按主程序域名解析而 404。
    无 BeautifulSoup 时降级为「正则提取文本最长的候选容器 + 剔除页眉页脚」。
    """
    if not html:
        return html
    if not HAVE_BS4:
        # 降级（无 bs4）：先删脚本/样式——Next.js 等站点会把 RSC 数据内联在 <script> 里，
        # 不删会串进正文并干扰「最长容器」的判断；再取候选容器中文本最长的一段作为正文，
        # 最后剔除页眉/页脚/导航/侧栏等噪声区块
        body = html
        for tag in ("script", "style", "noscript"):
            body = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", body, flags=re.S | re.I)
        best, best_len = "", 0
        for tag in ("article", "main", "section"):
            for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", body, re.S | re.I):
                seg = m.group(1)
                length = len(re.sub(r"<[^>]+>", "", seg))
                if length > best_len:
                    best, best_len = seg, length
        body = best or body
        for tag in NOISE_CONTAINER_TAGS:
            body = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", body, flags=re.S | re.I)
        # 安全清洗（降级路径同样必须做）：去掉内联事件属性与 javascript: 协议，
        # 否则前端 v-html 渲染时会执行脚本
        body = re.sub(r'\son[a-z]+\s*=\s*"[^"]*"', "", body, flags=re.I)
        body = re.sub(r"\son[a-z]+\s*=\s*'[^']*'", "", body, flags=re.I)
        # 无引号的内联事件属性（onerror=alert(1)）：属性值一直延伸到空白或 > 为止，
        # 此前只清理带引号形式，无引号写法同样会在 v-html 渲染时执行脚本
        body = re.sub(r"\son[a-z]+\s*=\s*[^\s>]+", "", body, flags=re.I)
        # 原生懒加载（降级路径）：负向前瞻避免重复注入已有 loading 的标签
        body = re.sub(
            r"<img\b(?![^>]*\sloading=)",
            '<img loading="lazy" decoding="async"',
            body,
            flags=re.I,
        )
        body = re.sub(
            r"""\s(?:href|src|data-src|data-original|srcset)\s*=\s*(?:"\s*(?:javascript|vbscript|data:text/html)[^"]*"|'\s*(?:javascript|vbscript|data:text/html)[^']*'|(?:javascript|vbscript):[^\s>]*)""",
            "",
            body,
            flags=re.I,
        )
        # 相对地址绝对化：降级路径此前缺少这一步，会让相对路径的图片/链接
        # 被前端按宿主域名解析而 404
        body = re.sub(
            r'(src|href)="(/[^"]*)"',
            lambda m: f'{m.group(1)}="{urljoin(base_url, m.group(2))}"',
            body,
            flags=re.I,
        )
        return body
    try:
        soup = _BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.debug(f"[{PLUGIN_NAME}] 正文解析失败: {e}")
        return html
    # 标签级去噪
    for tag in soup(list(NOISE_TAGS)):
        tag.decompose()
    # 区块级去噪：站点 logo/导航/侧栏/广告等容器整体删除
    for selector in NOISE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()
    # 在候选容器中取「文本最长」的一个作为正文：正文内容最多，
    # 可自动排除 AI 助手气泡、相关推荐、侧栏等同样命中选择器的小块
    node = None
    best_len = 0
    for selector in CONTENT_SELECTORS:
        for candidate in soup.select(selector):
            length = len(candidate.get_text(strip=True))
            if length > best_len:
                node, best_len = candidate, length
    node = node or soup.body or soup
    # 图片地址绝对化（含懒加载属性），否则相对路径在前端无法加载
    for img in node.find_all("img"):
        src = img.get("src")
        if src:
            img["src"] = _absolutize(base_url, src)
        for attr in ("data-src", "data-original"):
            val = img.get(attr)
            if val:
                img[attr] = _absolutize(base_url, val)
        # srcset 同样要绝对化：浏览器会优先按 srcset 选图，
        # 保留相对路径会让正文配图按宿主域名解析而 404
        srcset = img.get("srcset")
        if srcset:
            img["srcset"] = ", ".join(
                " ".join([_absolutize(base_url, p.strip().split()[0])] + p.strip().split()[1:])
                for p in srcset.split(",")
                if p.strip()
            )
        # 原生懒加载：正文可能很长、图片很多，按需加载可显著降低首屏开销（移动端收益更明显）
        img["loading"] = "lazy"
        img["decoding"] = "async"
    # 正文内链接同样绝对化，避免点击后跳到主程序域名下的无效地址
    for a in node.find_all("a"):
        href = a.get("href")
        if href:
            a["href"] = _absolutize(base_url, href)
    # 安全清洗：前端用 v-html 渲染正文，必须去掉可执行内容——
    # 内联事件属性（onerror/onload/onclick…）与 javascript: 协议链接都会导致脚本执行
    for el in node.find_all(True):
        for attr in list(el.attrs):
            if attr.lower().startswith("on"):
                del el.attrs[attr]
        for attr in ("href", "src", "data-src", "data-original", "srcset"):
            val = el.get(attr)
            if isinstance(val, str) and val.strip().lower().startswith(
                ("javascript:", "vbscript:", "data:text/html")
            ):
                del el.attrs[attr]
    return str(node)


def _load_json_dict(path: str, label: str) -> dict:
    """
    读取「字典结构」的 JSON 状态文件（已读状态 / 通知去重记录）。
    文件被写坏成数组或字符串时，后续 self._x[key] = ... 会抛 TypeError 让接口 500、
    定时任务中断；这里统一做类型校验，异常时按空字典处理并告警。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"[{PLUGIN_NAME}] {label} 读取失败，按空处理: {e}")
        return {}
    if not isinstance(data, dict):
        logger.warning(f"[{PLUGIN_NAME}] {label} 结构异常（不是对象），已忽略")
        return {}
    return data


def _load_json_list(path: str, label: str) -> list:
    """
    读取「列表结构」的 JSON 状态文件（订阅源 / 规则 / 通知记录）。
    与 _load_json_dict 同样的类型校验目的。
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.warning(f"[{PLUGIN_NAME}] {label} 读取失败，按空处理: {e}")
        return []
    if not isinstance(data, list):
        logger.warning(f"[{PLUGIN_NAME}] {label} 结构异常（不是数组），已忽略")
        return []
    return data


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
        r = _requests.post(url, data=body, headers=headers, timeout=REQUEST_TIMEOUT)
        # requests 对 4xx/5xx 不抛异常，不校验会被当成发送成功：该条目随即登记去重记录、
        # 永久不再通知。这里显式抛错，让调用方走「失败不登记」的分支
        r.raise_for_status()
        return
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        resp = urlopen(req, timeout=REQUEST_TIMEOUT)
        resp.read()
        # 与 requests 分支语义保持一致：状态码 >=400 同样视为发送失败
        status = getattr(resp, "status", None) or 0
        if status >= 400:
            raise RuntimeError(f"Webhook 返回状态码 {status}")
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
                content_html = _clean_article_html(r.text, link)
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
                content_html = _clean_article_html(r.text, link)
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
    # plugin_name 是展示名，需与市场索引 package.v2.json 的 name 保持一致；
    # PLUGIN_NAME 常量仅作日志前缀，保持与插件目录一致的英文标识。
    plugin_name = "RSSHub 阅读器"
    plugin_desc = "RSSHub 资讯源阅读器：订阅管理（OPML导入导出）、阅读文章、完整图片、已读标记、规则通知（含后端图片代理）"
    plugin_version = "1.6.2"
    plugin_author = "Samuel"

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
    # 规则列表与通知去重记录：实际内容在 init_plugin 中从磁盘载入，
    # 这里给出类级默认值，保证实例尚未初始化时读取也不会 AttributeError
    _rules: list = None
    _notified: dict = None
    # 保护 _articles「写内存 + 落盘」的可重入锁（实例级，由 _get_cache_lock 惰性创建）
    _cache_lock = None

    # ================= 生命周期 =================
    def init_plugin(self, config: dict = None):
        """
        MP V2 生命周期入口：插件加载/配置变更时调用。
        幂等：重载时不重复初始化内存状态（_initialized 守护）。
        """
        self._config = config or {}
        # 并发写保护：定时刷新线程与 API 线程会并发改 _articles 并落盘，
        # 用同一把可重入锁串行化「写内存 + 落盘」；惰性创建保证 MP 多次调用 init_plugin
        # 时复用同一把锁（重建会让旧引用失去保护，等于没有加锁）
        self._get_cache_lock()
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
        # 内存状态（首次启动为空字典，内容由 _maybe_load_cache 从磁盘惰性恢复）。
        # 注意：必须绑定实例级字典，不能沿用类属性的 {}——类属性是可变对象，
        # 会被同一插件的多个实例（如插件分身）共享，导致订阅源数据互相污染。
        if "_articles" not in self.__dict__:
            self._articles = {}
        self._read_status = self._load_read_status()
        self._rules = self._load_rules()
        self._notified = self._load_notified()
        self._initialized = True
        logger.info(
            f"[{PLUGIN_NAME}] v{self.plugin_version} 已加载，数据目录: {self._data_dir}"
        )

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
        interval = max(5, self._cfg_int("poll_interval", 30))
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

        max_entries = self._cfg_int("max_entries", 50)
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

        # 只在「替换内存态 + 落盘」这一小段加锁：上面的 HTTP 抓取绝不能进锁，
        # 否则并发刷新/单源刷新会被串行化，抓取反而更慢
        with self._get_cache_lock():
            self._articles = articles
            self._save_cache(articles)
        # 刷新后清理失效的已读/已通知记录（惰性，仅在记录量大时真正执行）
        self._maybe_gc_read_status()
        self._maybe_gc_notified()
        # 规则通知：仅对新出现的条目进行匹配（去重 + 已读联动在 match 内部处理）
        if bool(self._cfg("notify_enabled", True)):
            # 通知属附加能力：其异常不应影响刷新主流程与已写入的缓存结果
            try:
                self._process_notify(articles)
            except Exception as e:
                logger.error(f"[{PLUGIN_NAME}] 规则通知流程异常: {e}")

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
            {
                "path": "/article/content",
                "endpoint": self.api_article_content,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "按需抓取单篇文章完整正文（列表刷新时不抓，避免拖慢）",
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
    async def _read_json_body(request: Request) -> dict:
        """
        读取请求体 JSON（FastAPI Request 注入）。
        无 body / 非 JSON 时返回空字典，避免接口因缺 body 直接 422。
        """
        try:
            return await request.json() or {}
        except Exception:
            return {}

    # ---- API 实现 ----
    async def api_feeds(self, request: Request) -> dict:
        """
        GET 列表（附分组、未读数）/ POST 添加 / DELETE 删除。
        添加时支持 group 字段，便于 OPML 导入与前端分组管理。

        注意：request 必须标注为 fastapi.Request，否则 FastAPI 会把它当成
        必填的 query 参数，导致 /feeds 全部请求在进入本方法前就返回 422。
        """
        method = request.method
        params = dict(request.query_params)
        body = await self._read_json_body(request)
        feeds = self._load_feeds()
        # 先恢复磁盘缓存：否则进程刚启动还没刷新过时，下面的 _save_cache 会把
        # 只有内存态的空字典写回磁盘，导致已缓存的文章数据被清空
        self._maybe_load_cache()
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
            # 添加后立刻拉一次（同步抓取放进线程池，避免阻塞事件循环）
            await run_in_threadpool(self._refresh_one, url)
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

    def api_article_content(self, feed_url: str = None, entry_id: str = None,
                            force: bool = False) -> dict:
        """
        按需抓取单篇文章的完整正文（GET ?feed_url=&entry_id=[&force=1]）。

        为什么放在阅读时抓、而不是刷新时抓：一个源动辄几十条，刷新时逐条抓网页
        会让刷新耗时被放大数十倍；改为点开文章时再抓，抓到的正文与图片回写缓存，
        同一篇再次打开直接命中缓存不再请求原站（force=1 可强制重抓）。

        图片以「正文容器内提取到的」为准：RSS 与整页 HTML 常混入站点 logo、横幅、
        表情等装饰图，此前合并旧图片会把它们一并展示出来。
        """
        feed_url = str(feed_url or "").strip()
        entry_id = str(entry_id or "").strip()
        if not feed_url or not entry_id:
            return {"ok": False, "msg": "缺少 feed_url 或 entry_id"}
        self._maybe_load_cache()
        data = self._articles.get(feed_url) or {}
        target = None
        for entry in data.get("entries", []):
            if str(entry.get("id") or entry.get("link")) == entry_id:
                target = entry
                break
        if not target:
            return {"ok": False, "msg": "未找到该文章（可先刷新订阅源）"}
        # 已抓取过且提取算法版本一致时直接返回缓存，避免每次打开都请求原站；
        # 提取逻辑升级（CONTENT_VER 变化）会让旧缓存自动失效并重新抓取
        if (
            target.get("content_fetched")
            and not force
            and target.get("content_ver") == CONTENT_VER
        ):
            return {
                "ok": True,
                "cached": True,
                "content": target.get("content", ""),
                "images": target.get("images") or [],
            }
        link = str(target.get("link") or "").strip()
        if not link:
            return {"ok": False, "msg": "该文章没有原文链接"}
        # 抓取原文并清洗为可读正文（去噪 + 图片绝对化）
        try:
            r = _http_get(link, {"Accept-Language": "zh-CN,zh;q=0.9"})
            r.raise_for_status()
            content_html = _clean_article_html(r.text, link)
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 按需抓取正文失败 {link}: {e}")
            return {"ok": False, "msg": f"抓取正文失败：{e}"}
        body_images = extract_images_from_html(content_html, link)[:MAX_IMAGES_PER_ENTRY]
        # 抓到的内容过于空（通常是反爬验证页或需登录页）时明确告知用户而不是显示空白，
        # 此时不写缓存、也不改动内存态，便于站点恢复后再次尝试
        if len(_strip_tags(content_html)) < 20 and not body_images:
            logger.warning(f"[{PLUGIN_NAME}] 未提取到有效正文（可能被反爬拦截或需登录）: {link}")
            return {
                "ok": False,
                "msg": "未能从原文提取到有效正文（该站点可能需要登录或存在反爬限制）",
            }
        # 抓取期间可能发生了整体刷新（refresh_all 会替换整个 _articles），
        # 因此「重新定位 + 回写 + 落盘」必须在缓存锁内一次完成：
        # 否则会写到已脱离字典的旧对象上，接口返回成功但缓存实际没生效
        with self._get_cache_lock():
            latest = self._articles.get(feed_url) or {}
            target = None
            for entry in latest.get("entries", []):
                if str(entry.get("id") or entry.get("link")) == entry_id:
                    target = entry
                    break
            if target is None:
                # 条目已被刷新移除：不写入、不落盘，明确告知用户重试（此前会假成功）
                logger.warning(
                    f"[{PLUGIN_NAME}] 正文回写失败：条目已不在缓存中 {feed_url}::{entry_id}"
                )
                return {"ok": False, "msg": "文章已被刷新或移除，请刷新订阅源后重试"}
            # 回写缓存：正文 + 以正文内图片为准重建列表（丢弃 RSS/整页里的装饰图）
            target["content"] = content_html
            target["content_fetched"] = True
            target["content_ver"] = CONTENT_VER
            target["images"] = body_images
            target["thumbnail"] = body_images[0] if body_images else ""
            self._save_cache(self._articles)
        logger.info(
            f"[{PLUGIN_NAME}] 按需抓取正文成功 [{target.get('title')}] "
            f"{len(content_html)} 字符 / {len(body_images)} 张图"
        )
        return {"ok": True, "content": content_html, "images": body_images}

    def _is_allowed_proxy_url(self, url: str) -> bool:
        """
        图片代理白名单：仅允许插件缓存中出现过的图片地址。
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
        if url in allowed:
            return True
        # 未命中时再检查正文 HTML：前端会把正文里的所有 <img> 都改写为代理地址，
        # 若只放行 images 列表，超出 30 张上限或被装饰图规则过滤掉的正文配图会变成空白像素
        for data in self._articles.values():
            for entry in data.get("entries", []):
                if url in (entry.get("content") or ""):
                    return True
        return False

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
        # 拒绝内网/保留地址：避免 /proxy 被当作内网探测工具（SSRF 面收敛）
        if _is_private_host(urlparse(url).hostname or ""):
            logger.warning(f"[{PLUGIN_NAME}] 代理请求被拒绝（内网/保留地址）: {url}")
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
            # SVG 可携带脚本，代理场景直接拒绝，避免 MIME 嗅探带来的脚本执行面
            if "svg" in ctype:
                logger.warning(f"[{PLUGIN_NAME}] 代理请求被拒绝（SVG 类型）: {url}")
                return self._blank_pixel()
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
                # 远程下载是同步阻塞 IO（最长 REQUEST_TIMEOUT），必须放进线程池，
                # 否则会阻塞事件循环、拖慢整个 MP 后端
                r = await run_in_threadpool(_http_get, remote_url)
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
        # 记录导入前的条数：超上限截断时据此回退 feeds，只保留前 MAX_OPML_FEEDS 个新增源
        base_count = len(feeds)
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

        # 单次导入条数上限：下面的逐源抓取是同步 IO，导入几百个源会长时间占用线程池
        # 并让本次请求迟迟不返回；超出部分直接截断（feeds 同步回退，不落盘多余数据）
        truncated = len(imported) > MAX_OPML_FEEDS
        if truncated:
            logger.warning(
                f"[{PLUGIN_NAME}] OPML 共解析出 {len(imported)} 个源，"
                f"超出单次导入上限 {MAX_OPML_FEEDS}，已截断"
            )
            feeds = feeds[:base_count + MAX_OPML_FEEDS]
            imported = imported[:MAX_OPML_FEEDS]

        self._save_feeds(feeds)
        # 导入后立刻拉取新源，让前端马上看到内容（无新增时跳过，避免误刷新全部）
        if imported:
            for f in feeds[-len(imported):]:
                # 逐个放进线程池执行，避免连续同步抓取阻塞事件循环
                await run_in_threadpool(self._refresh_one, f["url"])

        msg = f"成功导入 {len(imported)} 个，跳过 {len(skipped)} 个已存在源"
        if truncated:
            msg += f"（单次最多导入 {MAX_OPML_FEEDS} 个，超出部分已截断）"
        return {
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "msg": msg,
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
        return _load_json_dict(self._read_file, "已读状态")

    def _save_read_status(self):
        try:
            with open(self._read_file, "w", encoding="utf-8") as f:
                json.dump(self._read_status, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 已读状态写入失败: {e}")

    def _maybe_gc_read_status(self):
        """
        已读记录会随文章过期而不断堆积。
        记录数达到阈值（2000）后，清理当前缓存中已找不到对应文章的条目，
        采用惰性 GC 以避免每次刷新都做全量比对与磁盘写入。
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
        if not self._notified or len(self._notified) < 2000:
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
        # 兜底：_rules 类级默认值为 None，未初始化时遍历会 TypeError
        for rule in (self._rules or []):
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
        # 兜底：类级默认值是 None，未初始化时下面的成员判断与赋值会 TypeError
        if not isinstance(self._notified, dict):
            self._notified = self._load_notified() or {}
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
                    if not self._send_notification(rule, entry, feed_name):
                        # 发送失败（渠道不可用等）：不登记去重记录、不标已读，下次刷新会重试；
                        # 若还有其他规则命中则继续尝试下一个渠道
                        continue
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
    def _send_notification(self, rule: dict, entry: dict, feed_name: str) -> bool:
        """
        发送一条规则通知，返回是否发送成功。
        调用方据此决定要不要登记去重记录：发送失败绝不能登记，
        否则该条目会被永久跳过、之后再也不会重试。
        """
        title = entry.get("title", "") or "(无标题)"
        link = entry.get("link", "") or ""
        rule_name = rule.get("name", "")
        channel = rule.get("channel") or self._cfg("notify_channel", "MessageCenter")
        template = self._cfg(
            "notify_template",
            "📰 [{feed}] {title}\n命中规则：{rule}\n{link}",
        )
        try:
            text = template.format(
                feed=feed_name, title=title, link=link, rule=rule_name,
                published=entry.get("published", ""),
            )
        except (KeyError, IndexError, ValueError) as e:
            # 自定义模板可能写错占位符（未知变量或裸花括号），降级为默认模板，
            # 避免模板异常让通知乃至整个刷新流程中断
            logger.warning(f"[{PLUGIN_NAME}] 通知模板变量无效({e})，已回退默认模板")
            text = f"📰 [{feed_name}] {title}\n命中规则：{rule_name}\n{link}"
        try:
            self._push_notification(channel, title, text, link, entry, rule, feed_name)
            logger.info(
                f"[{PLUGIN_NAME}] 规则通知 ✓ [{channel}] {rule_name}: {title}"
            )
            sent = True
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 通知发送失败 [{channel}]: {e}")
            sent = False

        # 追加到通知记录（前端"最近通知记录"）
        self._append_notify_log({
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rule": rule_name,
            "channel": channel,
            "feed": feed_name,
            "title": title,
            "link": link,
            # 记录里区分成功/失败：失败的只是「尝试记录」，
            # 若前端不区分会把实际未发出的条目展示成已通知
            "sent": sent,
        })
        return sent

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
            # 抛错而非静默返回：否则调用方会当作发送成功并登记去重记录，
            # 该条目将永久不再通知（用户以为通知生效、实际从未发出）
            raise ValueError("Webhook 未配置 webhook_url")
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
        max_log = self._cfg_int("max_notify_log", 200)
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
        # 兜底：类级默认值是 None，若本方法在 init_plugin 之前被调用，
        # 下面的 len()/append() 会抛 TypeError 造成 500，这里惰性载入为列表
        if not isinstance(self._rules, list):
            self._rules = self._load_rules() or []
        if method == "POST":
            rule, err = self._validate_rule(body)
            if err:
                return {"ok": False, "msg": err}
            # _validate_rule 只产出业务字段，id 由前端在「编辑」「切换启用」时回传，
            # 必须从原始请求体取，否则会把编辑误判为新增、产生重复规则
            rule["id"] = str(body.get("id") or "").strip() or f"r_{int(time.time() * 1000)}"
            rule.setdefault("enabled", True)
            rule.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # 同 id 已存在则覆盖更新，否则追加为新建
            index = next(
                (i for i, r in enumerate(self._rules) if r.get("id") == rule["id"]),
                None,
            )
            if index is None:
                self._rules.append(rule)
            else:
                # 保留原创建时间，便于前端区分「新建」与「修改」
                rule["created_at"] = self._rules[index].get("created_at") or rule["created_at"]
                self._rules[index] = rule
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
            # 失败记录（sent=False）只是「尝试记录」，不算命中：
            # 否则前端会把实际未发出的条目展示成已通知
            if rec.get("sent") is False:
                continue
            name = rec.get("rule")
            if name and name not in last_hit:
                last_hit[name] = rec.get("at")
        out = []
        # 兜底：_rules 类级默认值为 None，未初始化时遍历会 TypeError
        for r in (self._rules or []):
            item = dict(r)
            item["last_hit"] = last_hit.get(r.get("name"), "")
            out.append(item)
        return out

    # ---- 规则测试：默认只预览；带 notify=true 时真实走一遍通知流程 ----
    async def api_rules_test(self, request: Request) -> dict:
        """
        对当前缓存的所有文章试运行规则。

        - 不带 notify：只返回命中条目，不发送通知、不写记录；
        - 带 notify=true（前端「通知测试」按钮）：命中条目中最多取前 NOTIFY_TEST_SAMPLE 条
          真实发送通知，用于验证通知渠道配置是否正确。为保证测试不污染正式流程，
          不写通知去重记录、也不标记已读。
        用法：POST { fields, match_type, keywords, feed_urls, [notify] }
        """
        body = await self._read_json_body(request)
        draft, err = self._validate_rule(body)
        if err:
            return {"ok": False, "msg": err}
        send_notify = bool(body.get("notify"))
        self._maybe_load_cache()
        hits = []
        sent = 0
        failed = 0
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
                    # 通知测试：只发前若干条样例，命中过多时不刷屏；
                    # 次数按「尝试数」而非「成功数」计，否则失败时会一直重试到超出样例上限
                    if send_notify and (sent + failed) < NOTIFY_TEST_SAMPLE:
                        # 发送是同步 IO，放进线程池避免阻塞事件循环
                        ok = await run_in_threadpool(
                            self._send_notification, draft, entry, feed_name
                        )
                        # 按返回值分别统计：此前忽略返回值直接累加 sent，
                        # 会把发送失败也算成「已发送 N 条」，掩盖渠道配置错误
                        if ok:
                            sent += 1
                        else:
                            failed += 1
        if send_notify:
            tail = (f"（仅发送前 {NOTIFY_TEST_SAMPLE} 条样例）"
                    if len(hits) > sent + failed else "")
            msg = f"通知测试完成：命中 {len(hits)} 条，发送成功 {sent} 条"
            if failed:
                msg += f"，发送失败 {failed} 条（请检查通知渠道与 Webhook 配置）"
            msg += tail
        else:
            msg = f"试运行完成，共命中 {len(hits)} 条（仅展示前 50 条）"
        return {
            "ok": True,
            "matched": len(hits),
            "sent": sent,
            "failed": failed,
            "hits": hits[:50],  # 最多返回 50 条预览
            "msg": msg,
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
        return _load_json_list(self._rules_file, "通知规则")

    def _save_rules(self):
        try:
            with open(self._rules_file, "w", encoding="utf-8") as f:
                json.dump(self._rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 同上：写入失败（磁盘满/权限）不应让规则相关接口 500 或中断调用方
            logger.error(f"[{PLUGIN_NAME}] 通知规则写入失败: {e}")

    def _load_notified(self) -> dict:
        return _load_json_dict(self._notified_file, "通知去重记录")

    def _save_notified(self):
        try:
            with open(self._notified_file, "w", encoding="utf-8") as f:
                json.dump(self._notified, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 通知去重记录写入失败: {e}")

    def _load_notify_log(self) -> list:
        if not self._data_dir:
            return []
        return _load_json_list(
            os.path.join(self._data_dir, "notify_log.json"), "通知记录"
        )

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
        """
        在 MP 侧边栏注册页面入口。
        - title：侧栏显示文案（字段名必须为 title，写成 name 会被忽略并回退成插件 ID）；
        - section=organize：归入「整理」分组，即内建「站点刷流」所在分组；
        - order=100：同组内靠后排序，展示在「站点刷流」下方；
        - nav_key 固定 main，前端暴露 ./AppPage 即可匹配。
        """
        return [
            {
                "nav_key": "main",
                # 侧栏文案单独取值（比市场展示名「RSSHub 阅读器」更短，与内建项长度协调）
                "title": "RSS阅读器",
                "icon": "mdi-rss",
                "section": "organize",
                "order": 100,
            }
        ]

    def get_page(self):
        """vue 全页模式：不返回 vuetify 详情页配置。"""
        return None

    # ================= 内部：数据存取 =================
    def _load_feeds(self) -> list:
        """
        读取订阅源列表。
        顺手过滤掉结构异常的条目（非字典、缺 url），避免后续取 url 时抛 KeyError 导致 500。
        """
        try:
            with open(self._feeds_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        if not isinstance(data, list):
            logger.warning(f"[{PLUGIN_NAME}] feeds.json 结构异常（不是数组），已忽略")
            return []
        feeds = []
        for item in data:
            if isinstance(item, dict) and str(item.get("url") or "").strip():
                feeds.append(item)
            else:
                logger.warning(f"[{PLUGIN_NAME}] 跳过结构异常的订阅源条目: {str(item)[:80]}")
        return feeds

    def _save_feeds(self, feeds: list):
        try:
            with open(self._feeds_file, "w", encoding="utf-8") as f:
                json.dump(feeds, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 磁盘满/权限不足时不能把异常抛给调用方：API 会 500、定时任务会中断，
            # 而内存态仍然有效，只记录错误即可
            logger.error(f"[{PLUGIN_NAME}] 订阅源写入失败: {e}")

    def _save_cache(self, articles: dict):
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[{PLUGIN_NAME}] 缓存写入失败: {e}")

    def _get_cache_lock(self) -> "threading.RLock":
        """
        取实例级缓存锁（惰性创建）。
        必须是每实例各自的锁：类级共享锁会让插件分身互相阻塞；
        惰性创建则兼容 init_plugin 尚未调用就触达内部方法的场景。
        """
        lock = getattr(self, "_cache_lock", None)
        if lock is None:
            lock = threading.RLock()
            self._cache_lock = lock
        return lock

    def _maybe_load_cache(self):
        """启动时若内存为空，先从磁盘缓存恢复（避免重启后页面空白）。"""
        if self._articles:
            return
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._articles = {}
            return
        # 类型校验：articles.json 被写坏（顶层成了数组、某个 value 不是 dict）时，
        # 后续 data.get(...) 会抛 AttributeError 让接口 500，这里直接判为无效缓存
        if not isinstance(data, dict):
            logger.warning(f"[{PLUGIN_NAME}] articles.json 结构异常（顶层不是对象），已忽略")
            self._articles = {}
            return
        cache = {}
        for url, value in data.items():
            if not isinstance(value, dict):
                logger.warning(f"[{PLUGIN_NAME}] 跳过结构异常的缓存项: {str(url)[:80]}")
                continue
            # entries 非列表时归一为空列表，避免遍历时抛 TypeError
            if not isinstance(value.get("entries"), list):
                value = dict(value, entries=[])
            cache[url] = value
        self._articles = cache

    def _refresh_one(self, feed_url: str):
        try:
            fetch_full = bool(self._cfg("fetch_full", True))
            max_entries = self._cfg_int("max_entries", 50)
            # 抓取放在锁外（同步 IO 耗时长，进锁会把并发抓取串行化）
            data = parse_feed(feed_url, fetch_full=fetch_full)
            data["entries"] = data["entries"][:max_entries]
            # 与 refresh_all 共用同一把锁：否则并发时后写会覆盖前者，磁盘缓存丢源
            with self._get_cache_lock():
                self._articles[feed_url] = data
                self._save_cache(self._articles)
            # 单源拉取成功日志：便于「添加订阅源」后确认链路是否走通
            logger.info(
                f"[{PLUGIN_NAME}] 单源拉取成功 [{data.get('title') or feed_url}] "
                f"{len(data.get('entries', []))} 条"
            )
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

    def _cfg_int(self, key: str, default: int) -> int:
        """
        读取整数配置项：值为空串、None 或非数字时回退默认值。
        配置被手工改成非法值时，int() 会抛 ValueError 并中断刷新/通知主流程，
        这里统一兜底，保证定时任务与通知不会因单个配置项异常而整体失败。
        """
        try:
            value = int(self._cfg(key, default))
        except (TypeError, ValueError):
            return default
        # 防御 0 与负数：max_entries=0 会把文章列表截断为空、
        # max_notify_log<=0 会清空通知记录，均非用户预期
        return value if value > 0 else default


# 让 MP 能 import 到类（兼容部分加载方式）
__all__ = ["RsshubReader"]
