# Email Monitor

Monitor daily emails and send a digest via WeChat. Supports both scheduled automatic digests and on-demand WeChat queries.

## Dependencies

- nanobot with email channel and weixin channel configured
- IMAP access to the target email account

## File Structure

```
skills/email/
├── README.md                  # This file
├── email_monitor.py           # Core skill
├── setup.py                   # Interactive setup wizard
├── email_monitor_setup.md     # Full setup guide
├── weixin_email_commands.md   # WeChat command reference
└── examples/
    └── cron.json              # Daily 21:00 cron trigger
```

## Installation

1. Place `email_monitor.py` in nanobot's `skills/` directory
2. Run `python setup.py` for interactive configuration, or manually edit `~/.nanobot/config.yaml`
3. Merge `examples/cron.json` job into `workspace/cron/jobs.json`, replace `YOUR_WEIXIN_USER_ID`
4. Run `nanobot channels login weixin` to authenticate WeChat
5. Restart nanobot

## Usage

- **Scheduled**: Daily at 21:00 auto-push email digest
- **WeChat commands**:
  - `今日邮件` / `查看邮件` / `邮件摘要` — View today's emails
  - `/emails` / `/email` — Quick commands
  - `📧` / `📬` — Emoji triggers

## WeChat Command Integration

The following needs to be added to `channels/commands.py`.

### 1. Email commands dictionary (in CommandHandler.handle_command)

```python
email_commands = {
    "今日邮件": self._handle_today_emails,
    "查看邮件": self._handle_today_emails,
    "邮件摘要": self._handle_today_emails,
    "今天邮件": self._handle_today_emails,
    "今天的邮件": self._handle_today_emails,
    "today's emails": self._handle_today_emails,
    "emails today": self._handle_today_emails,
    "email digest": self._handle_today_emails,
    "check emails": self._handle_today_emails,
    "/emails": self._handle_today_emails,
    "/email": self._handle_today_emails,
}
```

### 2. Command match loop in handle_command

```python
for cmd, handler in email_commands.items():
    if content.lower() == cmd.lower() or content.lower().startswith(cmd.lower()):
        try:
            response = await handler(sender_id, chat_id)
            return response
        except Exception as e:
            ...
```

### 3. Fuzzy keyword match (after the exact match loop)

```python
if any(keyword in content.lower() for keyword in ["邮件", "email", "信箱"]):
    if any(word in content for word in ["今天", "今日", "today", "看看", "查看", "check", "show"]):
        ...
```

### 4. EmailCommandHandler class (extends CommandHandler)

```python
class EmailCommandHandler(CommandHandler):
    """Specific handler for email-related commands in WeChat."""

    async def handle_command(self, content, sender_id, chat_id):
        # Check WeChat-specific patterns first
        weixin_patterns = {
            "📧": self._handle_today_emails,
            "📬": self._handle_today_emails,
            "📨": self._handle_today_emails,
            "看看邮件": self._handle_today_emails,
            "邮件呢": self._handle_today_emails,
            "今天有邮件吗": self._handle_today_emails,
            "有新邮件吗": self._handle_today_emails,
        }
        ...

        # Fall back to parent
        return await super().handle_command(content, sender_id, chat_id)
```

### 5. Factory function

```python
def create_command_handler(channel, bus):
    if channel.name == "weixin":
        return EmailCommandHandler(channel, bus)
    return CommandHandler(channel, bus)
```

## Configuration Reference

In `~/.nanobot/config.yaml`:

```yaml
channels:
  email:
    enabled: true
    consent_granted: true
    imap_host: "imap.gmail.com"
    imap_port: 993
    imap_username: "YOUR_EMAIL_ADDRESS"
    imap_password: "YOUR_APP_PASSWORD"
    imap_mailbox: "INBOX"
    imap_use_ssl: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "YOUR_EMAIL_ADDRESS"
    smtp_password: "YOUR_APP_PASSWORD"
    smtp_use_tls: true
    poll_interval_seconds: 300
    mark_seen: true
    max_body_chars: 5000

  weixin:
    enabled: true
    base_url: "https://ilinkai.weixin.qq.com"

# Environment variable
# export EMAIL_MONITOR_WEIXIN_USER=YOUR_WEIXIN_USER_ID
```

## Customization

- Edit `identify_important_emails` method to adjust important email keywords
- Adjust `limit` parameter in `execute` method to change max email count
- Modify cron expression in `examples/cron.json` to change schedule
