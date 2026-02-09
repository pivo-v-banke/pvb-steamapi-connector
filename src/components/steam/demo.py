"""
GPT generated bullshit stuff for cs2 GC responses
Looks crazy but works fine =)
"""

import re
from typing import Any, Iterable

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

DEMO_URL_KEYS = ("demo_url", "demo_download_url", "download_url", "url")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
RE_FULL_DEMO_URL = re.compile(
    r"https?://replay\d+\.valve\.net/730/\d{1,30}_\d{1,15}\.dem(?:\.bz2)?",
    re.IGNORECASE,
)
RE_REPLAY_HOST = re.compile(r"(replay\d+\.valve\.net)", re.IGNORECASE)
RE_730_PREFIX = re.compile(r"https?://replay\d+\.valve\.net/730/?$", re.IGNORECASE)

def find_first_url(obj: Any) -> str | None:

    if obj is None:
        return None

    if hasattr(obj, "to_dict"):
        try:
            obj = obj.to_dict()
        except Exception:
            pass

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in DEMO_URL_KEYS:
                if isinstance(v, str) and URL_RE.match(v):
                    return v
            found = find_first_url(v)
            if found:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = find_first_url(item)
            if found:
                return found

    if isinstance(obj, str) and URL_RE.match(obj):
        return obj

    return None

def _demo_filename(match_id: int, token: int) -> str:
    return f"{match_id:021d}_{token:010d}.dem.bz2"

def _iter_strings(obj: Any) -> Iterable[str]:
    if obj is None:
        return

    if isinstance(obj, Message):
        try:
            obj = MessageToDict(obj, preserving_proto_field_name=True)
        except Exception:
            for field_desc, value in obj.ListFields():
                yield field_desc.name
                yield from _iter_strings(value)
            return

    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _iter_strings(v)
        return

    if isinstance(obj, (list, tuple)):
        for x in obj:
            yield from _iter_strings(x)
        return

    if isinstance(obj, str):
        yield obj
        return

    if isinstance(obj, (bytes, bytearray)):
        try:
            yield obj.decode("utf-8", errors="ignore")
        except Exception:
            pass
        return

    if hasattr(obj, "__dict__"):
        for k, v in vars(obj).items():
            if isinstance(k, str):
                yield k
            yield from _iter_strings(v)
        return


def extract_demo_url(msg: Any, match_id: int, token: int) -> str | None:
    strings = list(_iter_strings(msg))

    for s in strings:
        m = RE_FULL_DEMO_URL.search(s)
        if m:
            return m.group(0)

    filename = _demo_filename(match_id, token)

    for s in strings:
        s2 = s.strip()
        if RE_730_PREFIX.match(s2):
            base = s2.rstrip("/") + "/"
            return base + filename

    # 2b) Ищем просто host
    for s in strings:
        m = RE_REPLAY_HOST.search(s)
        if m:
            host = m.group(1)
            return f"http://{host}/730/{filename}"

    loose_path = f"/730/{match_id:021d}_{token:010d}.dem"
    for s in strings:
        if loose_path in s:
            m = RE_REPLAY_HOST.search(s)
            if m:
                host = m.group(1)
                tail = s[s.find("/730/"):]
                tail = tail.split()[0].strip('"\',')
                return f"http://{host}{tail}"

    return None