#!/usr/bin/env python3
"""
Setup script for email monitoring functionality.
This script helps users configure email monitoring quickly.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

def prompt_user(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default value."""
    if default:
        suffix = f" [{default}]: "
    else:
        suffix = ": "

    value = input(prompt + suffix).strip()
    return value if value else default

def get_config_dir() -> Path:
    """Get nanobot configuration directory."""
    home = Path.home()
    config_dir = home / ".nanobot"
    return config_dir

def ensure_config_dir() -> Path:
    """Ensure nanobot config directory exists."""
    config_dir = get_config_dir()
    config_dir.mkdir(exist_ok=True)
    return config_dir

def load_config() -> Dict[str, Any]:
    """Load existing config if available."""
    config_path = get_config_dir() / "config.yaml"
    if config_path.exists():
        import yaml
        return yaml.safe_load(config_path.read_text()) or {}
    return {}

def save_config(config: Dict[str, Any]) -> None:
    """Save config to file."""
    import yaml
    config_path = get_config_dir() / "config.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

def setup_email_config() -> None:
    """Setup email channel configuration."""
    print("\n=== 邮件渠道配置 ===")
    print("请输入您的邮箱配置信息：\n")

    config = load_config()

    # Ensure channels section exists
    if "channels" not in config:
        config["channels"] = {}

    email_config = {}

    # Email provider presets
    print("选择您的邮箱提供商：")
    print("1. Gmail")
    print("2. Outlook/Hotmail")
    print("3. QQ邮箱")
    print("4. 163邮箱")
    print("5. 自定义")

    provider = prompt_user("选择 (1-5)", "1")

    presets = {
        "1": {
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587
        },
        "2": {
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "smtp_host": "smtp-mail.outlook.com",
            "smtp_port": 587
        },
        "3": {
            "imap_host": "imap.qq.com",
            "imap_port": 993,
            "smtp_host": "smtp.qq.com",
            "smtp_port": 587
        },
        "4": {
            "imap_host": "imap.163.com",
            "imap_port": 993,
            "smtp_host": "smtp.163.com",
            "smtp_port": 25
        }
    }

    if provider in presets:
        email_config.update(presets[provider])
        print(f"\n已应用预设配置。")

    # Get email credentials
    email_config.update({
        "enabled": True,
        "consent_granted": True,
        "imap_username": prompt_user("邮箱地址"),
        "imap_password": prompt_user("邮箱密码或应用专用密码"),
        "imap_mailbox": prompt_user("邮箱文件夹", "INBOX"),
        "imap_use_ssl": True,
        "smtp_username": email_config.get("imap_username"),
        "smtp_password": email_config.get("imap_password"),
        "smtp_use_tls": True,
        "poll_interval_seconds": 300,
        "mark_seen": True,
        "max_body_chars": 5000
    })

    # Check for Gmail specific instructions
    if "gmail.com" in email_config.get("imap_username", ""):
        print("\n⚠️ Gmail 用户请注意：")
        print("1. 请确保已开启两步验证")
        print("2. 请使用应用专用密码，不是登录密码")
        print("3. 访问 https://myaccount.google.com/apppasswords 生成密码")
        input("\n按回车键继续...")

    config["channels"]["email"] = email_config
    save_config(config)
    print("\n✅ 邮件配置已保存")

def setup_weixin_config() -> None:
    """Setup WeChat channel configuration."""
    print("\n=== 微信渠道配置 ===")
    print("微信渠道需要首次运行时扫码登录。\n")
    print("配置完成后，您可以在微信中发送以下命令查看邮件：")
    print("- '今日邮件' 或 '/emails'")
    print("- '📧' 表情符号")
    print("- 更多命令请参考文档\n")

    config = load_config()

    # Ensure channels section exists
    if "channels" not in config:
        config["channels"] = {}

    config["channels"]["weixin"] = {
        "enabled": True,
        "base_url": "https://ilinkai.weixin.qq.com",
        "cdn_base_url": "https://novac2c.cdn.weixin.qq.com/c2c",
        "token": "",
        "poll_timeout": 35
    }

    save_config(config)
    print("✅ 微信配置已保存")
    print("\n请运行以下命令完成微信登录：")
    print("nanobot channels login weixin")

def setup_cron_job() -> None:
    """Setup cron job for email monitoring."""
    print("\n=== 定时任务配置 ===")

    print("选择执行时间：")
    print("1. 每天 21:00")
    print("2. 每天 20:00")
    print("3. 工作日 22:00")
    print("4. 自定义时间")

    time_choice = prompt_user("选择 (1-4)", "1")

    cron_exprs = {
        "1": "0 21 * * *",
        "2": "0 20 * * *",
        "3": "0 22 * 1-5",
        "4": prompt_user("输入 cron 表达式 (如: 0 21 * * *)", "0 21 * * *")
    }

    cron_expr = cron_exprs.get(time_choice, cron_exprs["1"])

    # WeChat user ID
    weixin_user = prompt_user("\n输入您的微信用户 ID")
    if not weixin_user:
        print("警告：未设置微信用户 ID，请稍后在 jobs.json 中手动配置")

    # Create jobs.json
    jobs_config = {
        "version": 1,
        "jobs": [
            {
                "id": "daily-email-digest",
                "name": "每日邮件摘要",
                "enabled": True,
                "schedule": {
                    "kind": "cron",
                    "expr": cron_expr,
                    "tz": "Asia/Shanghai"
                },
                "payload": {
                    "kind": "agent_turn",
                    "message": "/skill email_monitor",
                    "deliver": True,
                    "channel": "weixin",
                    "to": weixin_user
                },
                "state": {
                    "nextRunAtMs": None,
                    "lastRunAtMs": None,
                    "lastStatus": None,
                    "lastError": None,
                    "runHistory": []
                },
                "createdAtMs": 0,
                "updatedAtMs": 0,
                "deleteAfterRun": False
            }
        ]
    }

    jobs_path = get_config_dir() / "jobs.json"
    jobs_path.write_text(json.dumps(jobs_config, indent=2, ensure_ascii=False))

    print(f"\n✅ 定时任务已配置：{cron_expr}")
    print(f"配置文件：{jobs_path}")

def main() -> None:
    """Main setup process."""
    print("=" * 50)
    print("邮件监控功能安装向导")
    print("=" * 50)

    try:
        # Check if nanobot is installed
        import nanobot
        print(f"\n✅ 检测到 nanobot 已安装: {nanobot.__version__}")
    except ImportError:
        print("\n❌ 未检测到 nanobot，请先安装：")
        print("pip install nanobot")
        sys.exit(1)

    # Ensure config directory
    ensure_config_dir()

    print("\n本向导将帮助您配置：")
    print("1. 邮件渠道（用于读取邮件）")
    print("2. 微信渠道（用于发送摘要）")
    print("3. 定时任务（每天自动执行）")

    if input("\n是否继续？(y/n): ").lower() != 'y':
        print("安装已取消")
        return

    # Setup configurations
    setup_email_config()
    setup_weixin_config()
    setup_cron_job()

    # Final instructions
    print("\n" + "=" * 50)
    print("安装完成！")
    print("=" * 50)
    print("\n接下来的步骤：")
    print("1. 运行 'nanobot channels login weixin' 扫码登录微信")
    print("2. 启动服务 'nanobot start'")
    print("3. 检查状态 'nanobot cron list'")
    print("\n🆕 测试方法：")
    print("- 手动测试: nanobot skill email_monitor")
    print("- 微信测试: 发送 '今日邮件' 给您的微信 Bot")
    print("- 快捷测试: 发送 '📧' 或 '/emails' 试试看")

    print("\n配置文件位置：")
    print(f"- 配置文件: {get_config_dir() / 'config.yaml'}")
    print(f"- 定时任务: {get_config_dir() / 'jobs.json'}")

    print("\n文档：")
    print("- 功能配置: docs/email_monitor_setup.md")
    print("- 微信命令: docs/weixin_email_commands.md")

if __name__ == "__main__":
    main()