#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
猫咪 VIP 爬虫脚本 & SDK

- 登录：实现 encode_sign + AES-CBC 加密流程。
- 分类：自动解密 category/base-2.js，列出所有标签。
- 数据：按分类 jump_name + 页数抓取多页视频。
- 既可命令行调用，也可被 Web 服务引用。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from Crypto.Cipher import AES  # type: ignore[import-untyped]
from Crypto.Util.Padding import pad, unpad  # type: ignore[import-untyped]

LOGIN_URL = "https://bmapi.jxychy.com/api/user/loginByUsername"
CATEGORY_API = "https://bbmjs.pki.net.cn/data/category/base-2.js"
LIST_API_TEMPLATE = "https://bbmjs.pki.net.cn/data/list/base-{channel}-{slug}-{page}.js"
TOPIC_DETAILS_API = "https://bbmjs.pki.net.cn/data/topic/details-{topic_id}-0.js"
STREAM_HOST = "https://www.mmxzxl1.com"
THUMB_HOST = "https://jpg.tlxxw.cc"
DETAIL_TEMPLATE = "https://www.a3k3c.com/play/{id}.html"
SUPPORTED_CHANNELS = {
    "vip",
    "remen",
    "remen2",
    "remen3",
    "shipin",
    "yousheng",
    "news",
}
DEFAULT_PAGE_SIZE = 50

KEY_B64 = "SWRUSnEwSGtscHVJNm11OGlCJU9PQCF2ZF40SyZ1WFc="
IV_B64 = "JDB2QGtySDdWMg=="
SIGN_KEY_B64 = "JkI2OG1AJXpnMzJfJXUqdkhVbEU0V2tTJjFKNiUleG1VQGZO"
DEFAULT_SUFFIX = "123456"


def b64decode_str(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


KEY_BYTES = base64.b64decode(KEY_B64)
IV_BASE = b64decode_str(IV_B64)
SIGN_KEY = b64decode_str(SIGN_KEY_B64)


def derive_iv(suffix: Optional[str]) -> bytes:
    seq = (IV_BASE + (suffix or DEFAULT_SUFFIX))[:16]
    return seq.encode("utf-8")


def aes_encrypt(plaintext: str, suffix: Optional[str]) -> str:
    cipher = AES.new(KEY_BYTES, AES.MODE_CBC, derive_iv(suffix))
    encrypted = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def aes_decrypt(cipher_b64: str, suffix: Optional[str]) -> str:
    cipher = AES.new(KEY_BYTES, AES.MODE_CBC, derive_iv(suffix))
    decrypted = cipher.decrypt(base64.b64decode(cipher_b64))
    return unpad(decrypted, AES.block_size).decode("utf-8")


def obj_key_sort(payload: Dict[str, Any]) -> List[tuple[str, Any]]:
    return sorted(((k, payload[k]) for k in payload), key=lambda kv: kv[0])


def base64_sign(payload: Dict[str, Any]) -> str:
    sign_str = "".join(f"{k}={_normalize_val(v)}&" for k, v in obj_key_sort(payload))
    sign_str += SIGN_KEY
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


def _normalize_val(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def urljoin_like(host: str, path: str) -> str:
    if not path:
        return host
    if path.startswith("http"):
        return path
    return f"{host.rstrip('/')}/{path.lstrip('/')}"


def normalize_thumb(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    url = urljoin_like(THUMB_HOST, path)
    if ".jpg" in url and ".jpg.txt" not in url:
        url = f"{url}.txt"
    if ".jpg.txt" in url and "size=" not in url:
        delimiter = "&" if "?" in url else "?"
        url = f"{url}{delimiter}size=500x281"
    return url


@dataclass
class LoginResult:
    token: str
    raw: Dict[str, Any]


@dataclass
class Category:
    section: str
    name: str
    channel: str
    slug: str
    topic_id: Optional[int] = None


class MaomiClient:
    def __init__(self, username: str, password: str, suffix: str = DEFAULT_SUFFIX):
        self.username = username
        self.password = password
        self.suffix = suffix
        self.session = requests.Session()

    def login(self) -> LoginResult:
        payload: Dict[str, Any] = {
            "system": 1,
            "timestamp": int(time.time() * 1000),
            "device": "pc",
            "username": self.username,
            "password": self.password,
            "phone_code": "+86",
            "phone": 0,
        }
        payload["encode_sign"] = base64_sign(payload)
        body = {"post-data": aes_encrypt(json.dumps(payload, separators=(",", ":")), self.suffix)}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.a3k3c.com/",
            "suffix": self.suffix,
        }
        resp = self.session.post(LOGIN_URL, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"登录失败：{data.get('msg')}")
        plain = aes_decrypt(data["data"], data.get("suffix"))
        parsed = json.loads(plain)["data"]
        token = parsed.get("token")
        if not token:
            raise RuntimeError("登录响应缺少 token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return LoginResult(token=token, raw=parsed)

    def fetch_categories(self) -> List[Category]:
        resp = self.session.get(
            CATEGORY_API,
            params={"nocache": int(time.time() * 1000)},
            headers={"Referer": "https://www.a3k3c.com/"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        plain = aes_decrypt(payload["data"], payload.get("suffix"))
        data = json.loads(plain)
        categories: List[Category] = []
        for menu in (data.get("menus") or {}).values():
            section = menu.get("name", "")
            for item in menu.get("data") or []:
                slug = item.get("jump_name")
                channel = item.get("channel")
                name = item.get("name")
                if slug and channel and name:
                    topic_id = item.get("topic_id") or (item.get("topic") or {}).get("id")
                    categories.append(
                        Category(
                            section=section,
                            name=name,
                            channel=channel,
                            slug=slug,
                            topic_id=topic_id,
                        )
                    )
        return categories

    def fetch_videos_for_category(
        self, category: Category, pages: int
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if category.channel == "topic":
            return self._fetch_topic_videos(category, pages)
        return self._fetch_channel_videos(category.channel, category.slug, pages), None

    def _fetch_channel_videos(self, channel: str, slug: str, pages: int) -> List[Dict[str, Any]]:
        channel_normalized = (channel or "").strip()
        if channel_normalized not in SUPPORTED_CHANNELS:
            raise ValueError(f"当前频道暂未开放采集，channel={channel_normalized}")
        items: List[Dict[str, Any]] = []
        for page in range(1, pages + 1):
            encoded_slug = quote(slug, safe="")
            url = LIST_API_TEMPLATE.format(channel=channel_normalized, slug=encoded_slug, page=page)
            resp = self.session.get(
                url,
                params={"nocache": int(time.time() * 1000)},
                headers={"Referer": "https://www.a3k3c.com/"},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            plain = aes_decrypt(payload["data"], payload.get("suffix"))
            parsed = json.loads(plain)
            page_items = (parsed.get("list") or {}).get("data") or []
            if not page_items:
                break
            items.extend(self._format_video(item) for item in page_items)
            last_page = (parsed.get("list") or {}).get("last_page") or 1
            if page >= last_page:
                break
        return items

    def _fetch_topic_videos(
        self, category: Category, pages: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not category.topic_id:
            raise ValueError(f"未检测到 {category.name} 的 topic_id，无法采集")
        resp = self.session.get(
            TOPIC_DETAILS_API.format(topic_id=category.topic_id),
            params={"nocache": int(time.time() * 1000)},
            headers={"Referer": "https://www.a3k3c.com/"},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        plain = aes_decrypt(payload["data"], payload.get("suffix"))
        data = json.loads(plain)
        topic_info = data.get("list") or {}
        raw_items = topic_info.get("list") or []
        limit = min(len(raw_items), pages * DEFAULT_PAGE_SIZE)
        videos = [self._format_video(item) for item in raw_items[:limit]]
        meta = {
            "title": topic_info.get("title"),
            "desc": topic_info.get("desc"),
            "price": topic_info.get("price"),
            "vip_price": topic_info.get("vip_price"),
            "gif_images": topic_info.get("gif_images"),
            "cover": topic_info.get("cover"),
            "phone_cover": topic_info.get("phone_cover"),
            "file": topic_info.get("file"),
            "free_videos_id": topic_info.get("free_videos_id"),
        }
        return videos, meta

    def _format_video(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "title": item.get("title"),
            "description": item.get("description"),
            "tags": item.get("tags"),
            "duration_seconds": item.get("duration"),
            "duration_hms": seconds_to_hms(item.get("duration")),
            "insert_time": item.get("insert_time"),
            "update_time": item.get("update_time"),
            "detail_url": DETAIL_TEMPLATE.format(id=item.get("id")),
            "video_hls": urljoin_like(STREAM_HOST, item.get("video_url", "")),
            "video_mp4": urljoin_like(STREAM_HOST, item.get("down_url", "")),
            "thumb_url": normalize_thumb(item.get("thumb")),
            "preview_url": urljoin_like(STREAM_HOST, item.get("preview", "")),
        }


def seconds_to_hms(value: Any) -> str:
    total = int(value or 0)
    if total < 0:
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="猫咪 VIP 视频爬虫（含登录逆向逻辑）")
    parser.add_argument("-u", "--username", default=os.environ.get("MAOMI_USERNAME"), help="登录用户名（默认读取环境变量 MAOMI_USERNAME）")
    parser.add_argument("-p", "--password", default=os.environ.get("MAOMI_PASSWORD"), help="登录密码（默认读取环境变量 MAOMI_PASSWORD）")
    parser.add_argument("-c", "--category", help="要抓取的分类名称或 jump_name（如 猫咪推荐 或 mmtj）")
    parser.add_argument("-P", "--pages", type=int, default=1, help="抓取页数（>=1，默认 1）")
    parser.add_argument("--list-categories", action="store_true", help="仅列出可用分类，不执行抓取")
    parser.add_argument("-o", "--output", help="结果写入指定文件（UTF-8 JSON），不指定则输出到控制台")
    args = parser.parse_args()
    if not args.username or not args.password:
        parser.error("必须提供用户名与密码（参数或环境变量）")
    if args.pages < 1:
        parser.error("--pages 必须 >= 1")
    if not args.list_categories and not args.category:
        parser.error("请使用 --category 指定分类，或先用 --list-categories 查看可选项")
    return args


def write_output(data: Any, output_path: Optional[str]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(text)
        print(f"结果已写入 {output_path}")
    else:
        print(text)


def main() -> None:
    args = parse_args()
    client = MaomiClient(args.username, args.password)
    login_res = client.login()
    categories = client.fetch_categories()

    if args.list_categories:
        catalog = [
            {
                "section": cat.section,
                "name": cat.name,
                "jump_name": cat.slug,
                "channel": cat.channel,
                "topic_id": cat.topic_id,
                "supported": cat.channel in SUPPORTED_CHANNELS or cat.channel == "topic",
            }
            for cat in categories
        ]
        write_output(catalog, args.output)
        return

    identifier = args.category.strip().lower()
    matched = [
        cat
        for cat in categories
        if cat.slug.lower() == identifier or cat.name.lower() == identifier
    ]
    if not matched:
        raise RuntimeError(f"未找到分类：{args.category}。可运行 --list-categories 查看可选项。")
    if len(matched) > 1:
        names = ", ".join(f"{cat.section}/{cat.name}" for cat in matched)
        raise RuntimeError(f"匹配到多个分类：{names}，请改用 jump_name 精确指定")
    target = matched[0]

    videos, topic_meta = client.fetch_videos_for_category(target, args.pages)
    result = {
        "account": {
            "username": args.username,
            "vip_level": login_res.raw.get("vip_level"),
            "is_vip": login_res.raw.get("is_vip"),
            "token": login_res.token,
        },
        "category": {
            "section": target.section,
            "name": target.name,
            "jump_name": target.slug,
            "channel": target.channel,
            "pages_requested": args.pages,
            "videos_found": len(videos),
            "topic_meta": topic_meta,
        },
        "videos": videos,
    }
    write_output(result, args.output)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"执行失败：{exc}", file=sys.stderr)
        sys.exit(1)