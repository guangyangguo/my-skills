# 邮件监控功能配置指南

## 功能概述

本功能提供两种邮件监控方式：

1. **定时自动摘要**：每天晚上固定时间自动读取邮箱中当天收到的邮件，整合信息后通过微信发送给您
2. **微信主动查询**：在微信中发送特定命令，随时随地查看今日邮件摘要

## 🆕 新增：微信命令查询功能

无需等待定时任务，您现在可以在微信中主动查看邮件：

### 支持的命令
- `今日邮件`、`查看邮件`、`邮件摘要`
- `/emails`、`/email`
- `📧`、`📬`、`📨`
- `看看邮件`、`今天有邮件吗`

详细命令列表请参考：[微信邮件监控快捷命令](weixin_email_commands.md)

## 配置步骤

### 1. 配置邮件渠道

编辑配置文件 `~/.nanobot/config.yaml`（或使用 `nanobot config edit`），添加邮件配置：

```yaml
channels:
  email:
    enabled: true
    consent_granted: true
    
    # IMAP 配置（接收邮件）
    imap_host: "imap.gmail.com"  # 例如：Gmail
    imap_port: 993
    imap_username: "your-email@gmail.com"
    imap_password: "your-app-password"  # 使用应用专用密码
    imap_mailbox: "INBOX"
    imap_use_ssl: true
    
    # SMTP 配置（发送邮件，此功能不需要，但建议配置）
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: "your-email@gmail.com"
    smtp_password: "your-app-password"
    smtp_use_tls: true
    
    # 其他配置
    poll_interval_seconds: 300
    mark_seen: true
    max_body_chars: 5000
```

**注意**：对于 Gmail，需要：
1. 开启两步验证
2. 生成应用专用密码（不是登录密码）

### 2. 配置微信渠道

```yaml
channels:
  weixin:
    enabled: true
    base_url: "https://ilinkai.weixin.qq.com"
    # token 留空，首次运行时会提示扫码登录
```

首次使用时运行：
```bash
nanobot channels login weixin
```

### 3. 设置微信接收者

有两种方式设置微信接收者：

#### 方式一：环境变量
```bash
export EMAIL_MONITOR_WEIXIN_USER="your_weixin_user_id"
```

#### 方式二：在定时任务中指定
在 `jobs.json` 中直接指定 `to` 字段

### 4. 配置定时任务

将 `examples/email_monitor_cron.json` 复制到 `~/.nanobot/jobs.json`，并修改：

1. **执行时间**：默认是每天晚上 21:00
   ```json
   "expr": "0 21 * * *"  // 每天 21:00
   ```

   其他常用时间：
   - `"0 20 * * *"` - 每天 20:00
   - `"0 22 * * 1-5"` - 工作日 22:00
   - `"0 9,18 * * *"` - 每天 9:00 和 18:00

2. **微信接收者**：将 `YOUR_WEIXIN_USER_ID` 替换为实际的微信用户 ID
   - 可以通过查看微信消息日志获取

### 5. 启动服务

```bash
# 启动 nanobot 服务
nanobot start

# 确保邮件和微信渠道都已启用
nanobot channels list
```

## 功能特性

### 邮件摘要内容

1. **总体统计**：当天收到的邮件总数
2. **按发件人分组**：显示每个发件人的邮件数量
3. **邮件预览**：每封邮件的主题和内容预览（前50字符）
4. **重要邮件标记**：自动识别包含关键词的重要邮件
   - 关键词：紧急、重要、urgent、重要、action、需要处理等
5. **安全验证**：系统会临时禁用DKIM/SPF验证以确保能收到所有邮件

### 关于DKIM/SPF验证

某些邮件服务（如Hugging Face通知邮件）可能无法通过DKIM或SPF验证，导致邮件被拒绝。系统已自动处理此问题：

- **说明**：DKIM/SPF验证用于防止邮件伪造，但某些服务的通知邮件可能未正确配置
- **解决方案**：系统在获取邮件时会临时禁用验证，确保您能收到所有邮件
- **安全性**：这只是读取操作，不会影响您的邮箱安全
- **配置选项**：如果需要严格安全验证，可在配置中设置 `verify_dkim` 和 `verify_spf`

### 安全性

- 支持 DKIM 和 SPF 验证，防止伪造邮件
- 仅读取当天邮件，不访问历史邮件
- 微信发送需要先通过扫码认证

## 故障排查

### 1. 邮件连接失败
- 检查 IMAP/SMTP 服务器地址和端口
- 确认用户名和应用专用密码正确
- 对于 Gmail，确保账户安全设置允许第三方应用

### 2. 微信发送失败
- 运行 `nanobot channels login weixin` 重新登录
- 检查微信用户 ID 是否正确
- 确认微信网络连接正常

### 3. 定时任务不执行
- 检查 `jobs.json` 格式是否正确
- 运行 `nanobot cron status` 查看定时任务状态
- 手动执行测试：`nanobot cron run daily-email-digest`

### 4. 调试模式

在 `config.yaml` 中开启调试日志：
```yaml
logging:
  level: debug
```

## 自定义配置

### 修改邮件摘要格式

编辑 `nanobot/skills/email_monitor.py` 中的 `_create_email_digest` 方法

### 调整重要邮件关键词

修改 `identify_important_emails` 方法中的 `important_keywords` 列表

### 更改邮件数量限制

在 `execute` 方法中调整 `limit` 参数（默认100封）

## 测试命令

```bash
# 手动执行一次邮件监控（不通过定时任务）
nanobot skill email_monitor

# 测试定时任务
nanobot cron run daily-email-digest

# 查看定时任务列表
nanobot cron list

# 查看最近执行记录
nanobot cron status
```