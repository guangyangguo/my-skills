# NanoBot Skills

基于 [NanoBot](https://github.com/HKUDS/nanobot) 的个人 skill 集合，通过 LLM + 定时任务实现每日邮件摘要和公众号文章监控，结果通过微信推送。

## 已有 Skills

| Skill | 说明 | 触发方式 |
|-------|------|----------|
| **email-monitor** | 每日读取邮箱，按发件人分组生成摘要，标注重要邮件，微信推送 | 定时 21:00 / 微信命令 |
| **wechat-article-monitor** | 从 wewe-rss 抓取公众号文章，LLM 逐篇生成摘要，微信推送 | 定时 17:57 / 微信命令 |

## 前置条件

- Python 3.10+
- [NanoBot](https://github.com/HKUDS/nanobot) 已安装且 weixin channel 已配置
- LLM API key（DeepSeek / OpenAI / Anthropic 等，在 `~/.nanobot/config.json` 中配置）
- **email-monitor**：邮箱需开启 IMAP（Gmail 需使用应用专用密码）
- **wechat-article-monitor**：Docker 运行 [wewe-rss](https://github.com/cooderl/wewe-rss) 服务（`localhost:4000`）

## 快速开始

```bash
# 1. 克隆到 nanobot 的 skills 目录
git clone https://github.com/YOUR_USER/nanobot-skills.git
cp -r nanobot-skills/email ~/.nanobot/skills/email-monitor
cp -r nanobot-skills/gongzhonghao ~/.nanobot/skills/wechat-article-monitor

# 2. 合并定时任务（替换 YOUR_WEIXIN_USER_ID）
# 将 email/examples/cron.json 和 gongzhonghao/examples/cron.json 中的 job
# 合并到 ~/.nanobot/workspace/cron/jobs.json

# 3. email-monitor 一键配置向导（可选）
python ~/.nanobot/skills/email-monitor/setup.py

# 4. 扫码登录微信
nanobot channels login weixin

# 5. 启动
nanobot start
```

## 目录结构

```
├── email/                              # 邮件监控 skill
│   ├── README.md                       # 功能文档
│   ├── email_monitor.py                # 核心 skill（NanoBot Skill 类）
│   ├── setup.py                        # 交互式安装向导
│   ├── email_monitor_setup.md          # 详细配置指南
│   ├── weixin_email_commands.md        # 微信命令参考
│   └── examples/
│       └── cron.json                   # 每日 21:00 定时任务
│
├── gongzhonghao/                       # 公众号监控 skill
│   ├── SKILL.md                        # NanoBot skill 定义
│   ├── README.md                       # 功能文档
│   ├── scripts/
│   │   └── fetch_and_summarize.py      # 核心抓取+摘要脚本
│   └── examples/
│       └── cron.json                   # 每日 17:57 定时任务
│
└── README.md                           # 本文件
```

## email-monitor

定时读取当天邮件，按发件人分组，LLM 生成摘要，标注重要邮件（关键词：紧急、urgent、会议、审批等），微信推送。

**微信命令**：`今日邮件` `查看邮件` `邮件摘要` `📧` `/emails`

## wechat-article-monitor

从 wewe-rss 抓取指定公众号近 24 小时文章，通过 LLM（DeepSeek / Anthropic 等）为每篇生成约 200 字中文摘要，微信推送带链接的摘要列表。

**微信命令**：`今日公众号` `公众号更新` `公众号摘要` `查找小林coding过去一天的内容`

## 自定义

- **邮箱**：编辑 `email_monitor.py` 中的 `identify_important_emails` 方法修改重要邮件关键词
- **公众号**：编辑 `fetch_and_summarize.py` 中的 `ACCOUNT_FEED_IDS` 字典添加/更换公众号
- **摘要风格**：修改 `fetch_and_summarize.py` 中的 `SUMMARY_PROMPT`
- **推送时间**：修改对应 `examples/cron.json` 中的 cron 表达式

