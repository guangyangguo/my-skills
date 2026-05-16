# 微信公众号文章监控

每日抓取指定微信公众号的新文章，LLM 生成摘要，通过微信推送。

## 依赖

- [wewe-rss](https://github.com/cooderl/wewe-rss) Docker 服务（`localhost:4000`）
- nanobot（weixin channel 已配置）
- LLM API key（从 `~/.nanobot/config.json` 自动读取）

## 文件结构

```
skills/gongzhonghao/
├── SKILL.md                          # skill 定义
├── README.md                         # 本文件
├── scripts/
│   └── fetch_and_summarize.py        # 核心脚本
└── examples/
    └── cron.json                     # 每日 17:57 定时触发
```

## 安装

1. 将 `skills/gongzhonghao/` 放到 nanobot 的 skills 目录下，重命名为 `wechat-article-monitor`
2. 将 `examples/cron.json` 中的 job 合并到 `workspace/cron/jobs.json`，替换 `YOUR_WEIXIN_USER_ID`
3. 重启 nanobot

## 使用

- **定时推送**：每天 17:57 自动推送
- **微信命令**：
  - `今日公众号` / `公众号更新` / `公众号摘要` — 查看全部
  - `查找小林coding过去一天的内容` — 指定公众号
  - `/wx` / `/articles` — 快捷命令

## 微信命令集成

需要在 `channels/commands.py` 中添加以下内容。

### 1. 在 CommandHandler 类中添加属性

```python
KNOWN_ACCOUNTS = ["小林coding", "代码随想录"]
```

### 2. 在 CommandHandler.handle_command 中添加命令

```python
# WeChat article commands (添加到 email_commands 之后)
wechat_article_commands = {
    "今日公众号": self._handle_today_articles,
    "公众号更新": self._handle_today_articles,
    "公众号摘要": self._handle_today_articles,
    "/wechat": self._handle_today_articles,
    "/articles": self._handle_today_articles,
    "/wx": self._handle_today_articles,
}
```

### 3. 在 email 命令匹配循环之后添加匹配逻辑

```python
# Check for wechat article command match
for cmd, handler in wechat_article_commands.items():
    if content.lower() == cmd.lower():
        ...

# Check for specific account lookup
account_name = self._extract_account_from_content(content)
if account_name and any(kw in content for kw in ["查找", "查看", "看看", "最近", "过去", "今天", "更新了啥", "有什么"]):
    ...

# Check for article-related keywords (fuzzy match)
if any(keyword in content for keyword in ["公众号", "文章"]):
    if any(word in content for word in ["今天", "今日", "看看", "查看", "更新", "摘要"]):
        ...
```

### 4. 在 CommandHandler 类中添加方法

```python
async def _handle_today_articles(self, sender_id, chat_id):
    """Run fetch_and_summarize.py for all accounts."""
    ...

async def _handle_specific_account(self, sender_id, chat_id, account_name):
    """Run fetch_and_summarize.py --accounts <name>."""
    ...

def _extract_account_from_content(self, content):
    """Extract matching account name from message text."""
    found = [acct for acct in self.KNOWN_ACCOUNTS if acct in content]
    return ",".join(found) if found else None
```

### 5. 在 EmailCommandHandler 中添加 WeChat 快捷模式

```python
# 在 weixin_patterns 字典中添加
"看看公众号": self._handle_today_articles,
"公众号呢": self._handle_today_articles,
"今天有更新吗": self._handle_today_articles,
"有新文章吗": self._handle_today_articles,
"看看文章": self._handle_today_articles,
"小林coding": self._handle_maybe_specific,
"代码随想录": self._handle_maybe_specific,
```

以及在 `handle_command` 开头添加指定公众号查找逻辑。

## 自定义

- 修改 `ACCOUNT_FEED_IDS` 字典来添加/更换公众号
- 修改 `SUMMARY_PROMPT` 来调整摘要风格
- 修改 cron 表达式来调整推送时间
