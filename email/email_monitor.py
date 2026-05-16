"""Email monitoring skill for daily email digest."""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger

from nanobot.agent.skills import Skill, skill
from nanobot.bus.events import OutboundMessage
from nanobot.channels.manager import ChannelManager
from nanobot.bus.queue import MessageBus


@skill
class EmailMonitorSkill(Skill):
    """
    Email monitoring skill that reads today's emails and sends a digest via WeChat.

    This skill:
    1. Reads all emails received today
    2. Groups them by sender
    3. Summarizes the content
    4. Sends the digest via WeChat
    """

    name = "email_monitor"
    description = "Monitor daily emails and send digest via WeChat"

    async def execute(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Execute the email monitoring task."""
        # Get email and WeChat channels
        email_channel = self._get_email_channel()
        weixin_channel = self._get_weixin_channel()

        if not email_channel:
            return "Error: Email channel not configured"

        if not weixin_channel:
            return "Error: WeChat channel not configured"

        # Get today's emails
        today = date.today()
        start_date = today
        end_date = today + timedelta(days=1)

        logger.info(f"Fetching emails from {start_date} to {end_date}")

        try:
            # Temporarily disable DKIM/SPF verification to fetch all emails
            original_verify_dkim = getattr(email_channel.config, 'verify_dkim', True)
            original_verify_spf = getattr(email_channel.config, 'verify_spf', True)

            try:
                # Temporarily disable verification
                email_channel.config.verify_dkim = False
                email_channel.config.verify_spf = False

                # Fetch emails for today
                emails = email_channel.fetch_messages_between_dates(
                    start_date=start_date,
                    end_date=end_date,
                    limit=100  # Adjust as needed
                )
            finally:
                # Restore original settings
                email_channel.config.verify_dkim = original_verify_dkim
                email_channel.config.verify_spf = original_verify_spf

            if not emails:
                digest = "📧 今日无新邮件"
            else:
                # Process and summarize emails
                digest = await self._create_email_digest(emails)

            # Send digest via WeChat
            # You need to configure the recipient WeChat ID
            weixin_user_id = context.get("weixin_user_id") if context else None
            if not weixin_user_id:
                # Get default WeChat user from config or use first available
                weixin_user_id = self._get_default_weixin_user()

            if weixin_user_id:
                await weixin_channel.send(OutboundMessage(
                    chat_id=weixin_user_id,
                    content=digest
                ))
                logger.info(f"Email digest sent to WeChat user {weixin_user_id}")
                # Count emails that failed DKIM/SPF if verification was originally enabled
                if original_verify_dkim or original_verify_spf:
                    return f"✅ 邮件摘要已发送 ({len(emails)} 封邮件)"
                else:
                    return f"✅ 邮件摘要已发送 ({len(emails)} 封邮件，已包含未通过验证的邮件)"
            else:
                return "Error: No WeChat recipient configured"

        except Exception as e:
            logger.error(f"Error in email monitoring: {e}")
            return f"Error: {str(e)}"

    def _get_email_channel(self):
        """Get email channel using multiple approaches."""
        # Try agent channel manager first
        if hasattr(self.agent, 'channel_manager'):
            try:
                return self.agent.channel_manager.get_channel("email")
            except:
                pass

        # Try through registry
        try:
            from nanobot.channels.registry import get_active_channel
            return get_active_channel("email")
        except:
            pass

        return None

    def _get_weixin_channel(self):
        """Get WeChat channel."""
        if hasattr(self.agent, 'channel_manager'):
            try:
                return self.agent.channel_manager.get_channel("weixin")
            except:
                pass

        try:
            from nanobot.channels.registry import get_active_channel
            return get_active_channel("weixin")
        except:
            pass

        return None

    async def _create_email_digest(self, emails: list[dict[str, Any]]) -> str:
        """Create a digest summary of today's emails."""
        # Group emails by sender
        sender_emails = {}
        for email in emails:
            sender = email.get("sender", "Unknown")
            if sender not in sender_emails:
                sender_emails[sender] = []
            sender_emails[sender].append(email)

        # Create digest
        digest_parts = [
            "📧 **今日邮件摘要**",
            f"📅 {date.today().strftime('%Y年%m月%d日')}",
            f"📊 共收到 {len(emails)} 封邮件\n"
        ]

        # Add summary by sender
        for sender, sender_email_list in sender_emails.items():
            count = len(sender_email_list)
            digest_parts.append(f"👤 **{sender}** ({count}封)")

            for email in sender_email_list[:3]:  # Show max 3 emails per sender
                subject = email.get("subject", "(无主题)")
                # Extract first line of content as preview
                content = email.get("content", "")
                preview = content.split('\n')[0] if content else ""
                preview = preview[:50] + "..." if len(preview) > 50 else preview

                digest_parts.append(f"  • {subject}")
                if preview:
                    digest_parts.append(f"    {preview}")

            if len(sender_email_list) > 3:
                digest_parts.append(f"  • ...还有 {len(sender_email_list) - 3} 封邮件")

            digest_parts.append("")

        # Add important emails section if any
        important_emails = self._identify_important_emails(emails)
        if important_emails:
            digest_parts.append("\n⭐ **重要邮件**")
            for email in important_emails:
                sender = email.get("sender", "Unknown")
                subject = email.get("subject", "(无主题)")
                digest_parts.append(f"• {sender}: {subject}")

        return "\n".join(digest_parts)

    def _identify_important_emails(self, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify potentially important emails."""
        important_keywords = [
            "高危","预警", "urgent", "紧急", "重要", "important", "action", "需要处理",
            "meeting", "会议", "deadline", "截止", "approval", "审批"
        ]

        important = []
        for email in emails:
            subject = email.get("subject", "").lower()
            content = email.get("content", "").lower()

            for keyword in important_keywords:
                if keyword in subject or keyword in content:
                    important.append(email)
                    break

        return important[:5]  # Return top 5 important emails

    def _get_default_weixin_user(self) -> str | None:
        """Get default WeChat user ID from configuration."""
        # Try to get from environment or config
        import os

        # Check if default WeChat user is configured
        default_user = os.getenv("EMAIL_MONITOR_WEIXIN_USER")
        if default_user:
            return default_user

        # You could also add configuration in your config file
        # For now, return None to require explicit configuration
        return None