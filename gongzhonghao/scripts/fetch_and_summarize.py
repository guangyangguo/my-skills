#!/usr/bin/env python3
"""Fetch WeChat articles from wewe-rss, summarize, and deliver via WeChat.

Usage:
  python fetch_and_summarize.py --weixin-user "USER_ID"
  python fetch_and_summarize.py --accounts "小林coding,代码随想录" --hours 24
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError

BEIJING_TZ = timezone(timedelta(hours=8))

SUMMARY_PROMPT = (
    "你是一个技术文章摘要助手。请用约200字的中文总结以下微信公众号文章的主要内容，"
    "提炼核心观点和关键信息。只输出摘要本身，不要包含'这篇文章'、'作者'等引导语。"
    "\n\n标题：{title}\n\n正文前段：\n{preview}"
)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _find_config_json() -> dict:
    """Try to load nanobot config.json from home dir."""
    cfg_path = Path.home() / ".nanobot" / "config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _get_llm_credentials() -> tuple[str, str]:
    """Return (api_key, api_base) from nanobot config or env vars."""
    cfg = _find_config_json()
    providers = cfg.get("providers", {})
    agents = cfg.get("agents", {})
    defaults = agents.get("defaults", {})
    model = defaults.get("model", "deepseek/deepseek-chat")
    provider_name = defaults.get("provider", "auto")

    # Resolve provider
    chosen = None
    if provider_name != "auto":
        chosen = providers.get(provider_name)
    else:
        prefix = model.split("/")[0] if "/" in model else ""
        if prefix:
            for name, p in providers.items():
                if name.lower().replace("-", "_") == prefix.lower().replace("-", "_"):
                    chosen = p
                    break
    if not chosen:
        for name in ("deepseek", "openrouter", "anthropic", "openai", "siliconflow", "custom", "zhipu", "moonshot"):
            p = providers.get(name, {})
            if p.get("api_key") or p.get("apiKey"):
                chosen = p
                break

    api_key = ""
    api_base = ""
    if chosen:
        api_key = chosen.get("api_key", chosen.get("apiKey", ""))
        api_base = chosen.get("api_base", chosen.get("apiBase", "")) or ""

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")

    return api_key, api_base


# ---------------------------------------------------------------------------
# wewe-rss
# ---------------------------------------------------------------------------

# Map account names to wewe-rss feed IDs
ACCOUNT_FEED_IDS = {
    "小林coding": "MP_WXS_3518034885",
    "代码随想录": "MP_WXS_3516695614",
}


def fetch_articles(wewe_rss_base: str, accounts: list[str]) -> list[dict] | None:
    """Fetch recent articles from wewe-rss, querying each account individually.

    Uses per-feed endpoint to avoid response-too-large issues from /feeds/all.json.
    Adds ?update=true to trigger a live sync from WeChat servers.
    Uses urllib (not httpx) because wewe-rss NestJS server rejects httpx with 502.
    """
    all_articles: list[dict] = []
    for acct in accounts:
        feed_id = ACCOUNT_FEED_IDS.get(acct)
        if not feed_id:
            print(f"[WARN] Unknown account: {acct}", file=sys.stderr)
            continue
        url = f"{wewe_rss_base}/feeds/{feed_id}.json?limit=10&update=true"
        try:
            req = Request(url)
            resp = urlopen(req, timeout=180)
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            items = data.get("items", []) if isinstance(data, dict) else []
            for item in items:
                item["_mp_name"] = acct
                all_articles.append(item)
            print(f"[INFO] {acct}: {len(items)} articles fetched", file=sys.stderr)
        except URLError as e:
            print(f"[ERROR] Cannot connect to wewe-rss: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[ERROR] {acct}: {e}", file=sys.stderr)
    return all_articles


# ---------------------------------------------------------------------------
# Filter & group
# ---------------------------------------------------------------------------

def filter_recent(articles: list[dict], cutoff: datetime) -> list[dict]:
    """Keep only articles published after `cutoff`."""
    recent = []
    for a in articles:
        pub = _parse_time(a.get("date_modified") or a.get("updated") or a.get("pubDate", ""))
        if pub and pub > cutoff:
            a["_parsed_time"] = pub
            recent.append(a)
    return recent


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 1e12 else value, tz=BEIJING_TZ)
    s = str(value).replace("Z", "").split("+")[0].split("T+")[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt[:19]).replace(tzinfo=BEIJING_TZ)
        except ValueError:
            continue
    try:
        ts = int(s)
        return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=BEIJING_TZ)
    except (ValueError, TypeError):
        return None


def group_by_account(articles: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for a in articles:
        name = a.get("_mp_name", "Unknown")
        grouped.setdefault(name, []).append(a)
    for name in grouped:
        grouped[name].sort(key=lambda a: a.get("_parsed_time", datetime.min), reverse=True)
    return dict(sorted(grouped.items()))


# ---------------------------------------------------------------------------
# LLM summarization
# ---------------------------------------------------------------------------

def summarize_via_llm(title: str, content: str) -> str | None:
    api_key, api_base = _get_llm_credentials()
    if not api_key:
        print("[WARN] No API key for LLM summarization", file=sys.stderr)
        return None

    model = os.getenv("NANOBOT_AGENTS__DEFAULTS__MODEL", "deepseek/deepseek-chat")
    if "/" in model:
        model = model.split("/", 1)[1]

    preview = content[:2000] if content else title
    prompt = SUMMARY_PROMPT.format(title=title, preview=preview)

    headers_dict = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    url = (api_base.rstrip("/") + "/v1/chat/completions") if api_base else "https://api.deepseek.com/v1/chat/completions"
    if "anthropic" in api_base.lower():
        url = api_base.rstrip("/") + "/v1/messages"
        headers_dict["anthropic-version"] = "2023-06-01"
    elif not api_base:
        if api_key.startswith("sk-ant"):
            url = "https://api.anthropic.com/v1/messages"
            headers_dict["anthropic-version"] = "2023-06-01"

    body: dict[str, Any]
    if "anthropic" in url:
        body = {
            "model": model,
            "max_tokens": 400,
            "system": "你是一个技术文章摘要助手。只输出摘要内容本身。",
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个技术文章摘要助手。只输出摘要内容本身。"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "temperature": 0.3,
        }

    try:
        req = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers_dict)
        resp = urlopen(req, timeout=120)
        data = json.loads(resp.read().decode("utf-8"))
        if "anthropic" in url:
            blocks = data.get("content", [{}])
            text = blocks[0].get("text", "") if blocks else ""
        else:
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return text.strip()[:300] if text else None
    except Exception as e:
        print(f"[WARN] LLM error: {e}", file=sys.stderr)
        return None


def fallback_summary(content: str, max_chars: int = 150) -> str:
    if not content:
        return "(无内容)"
    text = re.sub(r"<[^>]+>", "", content)
    text = text.replace("\n", " ").replace("\r", " ").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text or "(无内容)"


# ---------------------------------------------------------------------------
# WeChat delivery
# ---------------------------------------------------------------------------

def send_weixin(user_id: str, content: str) -> bool:
    """Output content to stdout for delivery by the nanobot agent.

    The agent (or cron job's deliver mechanism) handles actual WeChat delivery.
    If we need direct delivery, the fallback writes to stdout which the calling
    command handler relays to the user.
    """
    # Always print to stdout — the agent/cron deliver mechanism or
    # command handler will relay this to the WeChat user.
    # Use stderr for logging so stdout stays clean for delivery.
    print(content, flush=True)
    return True


# ---------------------------------------------------------------------------
# Digest builder
# ---------------------------------------------------------------------------

def build_digest(grouped: dict[str, list[dict]], now: datetime) -> str:
    total = sum(len(v) for v in grouped.values())
    lines = [
        f"📚 今日公众号更新 | {now.strftime('%Y-%m-%d')}",
        f"📊 共 {total} 篇新文章",
        "",
    ]
    for mp_name, articles in grouped.items():
        lines.append(f"🔹 **{mp_name}** ({len(articles)}篇)")
        for i, a in enumerate(articles, 1):
            title = a.get("title", "(无标题)")
            link = a.get("url", "")
            content = a.get("content_html", a.get("content", a.get("description", "")))

            summary = summarize_via_llm(title, content)
            if not summary:
                summary = fallback_summary(content)

            line = f"  {i}. [{title}]({link})" if link else f"  {i}. {title}"
            lines.append(line)
            lines.append(f"     {summary}")
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args: argparse.Namespace) -> int:
    # Fix Windows console encoding for emoji output
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    accounts = [a.strip() for a in args.accounts.split(",") if a.strip()]
    weixin_user = args.weixin_user or os.getenv("WECHAT_ARTICLE_MONITOR_WEIXIN_USER", "")

    articles = fetch_articles(args.wewe_rss_base, accounts)
    if articles is None:
        msg = "❌ 公众号抓取失败：无法连接 wewe-rss 服务，请检查 Docker 是否运行"
        send_weixin(weixin_user, msg)
        return 1

    now = datetime.now(BEIJING_TZ)
    cutoff = now - timedelta(hours=args.hours)
    recent = filter_recent(articles, cutoff)

    if not recent:
        msg = "📚 今日公众号无新文章更新"
        send_weixin(weixin_user, msg)
        return 0

    grouped = group_by_account(recent)
    digest = build_digest(grouped, now)

    send_weixin(weixin_user, digest)
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WeChat Article Monitor")
    p.add_argument("--wewe-rss-base", default="http://localhost:4000")
    p.add_argument("--weixin-user", default="")
    p.add_argument("--accounts", default="小林coding,代码随想录")
    p.add_argument("--hours", type=int, default=24)
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(main(_parse_args()))
