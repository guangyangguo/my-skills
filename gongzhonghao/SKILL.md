---
name: wechat-article-monitor
description: Fetch recent WeChat public account articles from wewe-rss, generate per-article summaries via LLM, and deliver the digest via WeChat. Triggered daily at 17:57 by cron.
metadata: {"nanobot":{"emoji":"📚"}}
---

# WeChat Article Monitor

Fetch today's articles from subscribed WeChat public accounts via the local wewe-rss Docker service, summarize each article, and send the digest to the user's WeChat.

## When to use

- `/skill wechat-article-monitor` (triggered by cron at 17:57 daily)
- User asks "今日公众号", "公众号更新", "公众号摘要" in WeChat

## Execution

Run the bundled script. It handles everything: fetching from wewe-rss, filtering past 24h, LLM summarization, and WeChat delivery.

```bash
cd <skills_dir>/wechat-article-monitor/scripts
python fetch_and_summarize.py --weixin-user "YOUR_WEIXIN_USER_ID"
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--wewe-rss-base` | `http://localhost:4000` | wewe-rss service URL |
| `--weixin-user` | (env `WECHAT_ARTICLE_MONITOR_WEIXIN_USER`) | WeChat user ID for delivery |
| `--accounts` | `小林coding,代码随想录` | Comma-separated account names |
| `--hours` | `24` | How many hours back to fetch |

## Error handling

- If wewe-rss is unreachable, the script exits with an error message delivered via WeChat
- If a single account fails, the other still produces results
- If there are no new articles within the window, a "今日无更新" message is sent
- If LLM summarization fails, it falls back to content preview

## Prerequisites

1. Docker running wewe-rss at `localhost:4000`
2. WeChat Read account logged in via wewe-rss web UI
3. Target public accounts subscribed in wewe-rss
4. nanobot with weixin channel configured
