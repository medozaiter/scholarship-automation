"""
Unified Notification Service for ScholarPilot AI
Comprehensive multi-channel notification engine across scholarships, academic community,
newsroom, and system announcements.
Strict SaaS-grade architecture with anti-spam, intelligent grouping, and zero emojis.
"""

import os
import re
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from services.db import (
    create_unified_notification,
    get_user_notification_preferences,
    update_user_notification_preferences,
    record_notification_event,
    get_user_by_username,
    get_all_users
)

logger = logging.getLogger("scholarpilot.notifications")


class NotificationService:
    """
    Unified Notification Service singleton handling multi-channel dispatches
    with intelligent grouping, granular user preferences, and deduplication.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NotificationService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        pass

    def get_user_preferences(self, email: str) -> Dict[str, Any]:
        """Returns granular notification preferences for a student."""
        return get_user_notification_preferences(email)

    def update_user_preferences(self, email: str, new_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Updates granular notification preferences for a student."""
        return update_user_notification_preferences(email, new_prefs)

    def dispatch(
        self,
        recipient_email: str,
        category: str,
        action_type: str,
        title: str,
        message: str,
        actor_name: str = "",
        actor_username: str = "",
        actor_avatar: str = "",
        target_type: str = "",
        target_id: str = "",
        link: str = "",
        priority: str = "normal",
        group_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        send_email: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Main entry point for dispatching a notification.
        Enforces user preferences, anti-spam, and intelligent grouping.
        """
        clean_email = (recipient_email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            return None

        # Check user preferences
        prefs = self.get_user_preferences(clean_email)
        cat_key = (category or "").lower()

        # Category level checks
        if cat_key == "scholarship" and not prefs.get("scholarship_enabled", True):
            logger.debug(f"Scholarship notification suppressed for {clean_email} by category preference.")
            return None
        if cat_key == "community" and not prefs.get("community_enabled", True):
            logger.debug(f"Community notification suppressed for {clean_email} by category preference.")
            return None
        if cat_key == "news" and not (prefs.get("news_enabled", True) and prefs.get("news_breaking", True)):
            logger.debug(f"News notification suppressed for {clean_email} by category preference.")
            return None
        if cat_key == "system" and not (prefs.get("system_enabled", True) and prefs.get("system_announcements", True)):
            logger.debug(f"System notification suppressed for {clean_email} by category preference.")
            return None

        # Granular action-level preference checks
        if action_type == "post_like" and not prefs.get("community_likes", True):
            logger.debug(f"Post like notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "post_comment" and not prefs.get("community_comments", True):
            logger.debug(f"Post comment notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "comment_reply" and not prefs.get("community_replies", True):
            logger.debug(f"Comment reply notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "follow" and not prefs.get("community_follows", True):
            logger.debug(f"Follow notification suppressed for {clean_email} by preference.")
            return None
        if action_type in ("post_mention", "comment_mention", "mention") and not prefs.get("community_mentions", True):
            logger.debug(f"Mention notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "scholarship_match" and not prefs.get("scholarship_matches", True):
            logger.debug(f"Scholarship match notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "approaching_deadline" and not prefs.get("approaching_deadlines", True):
            logger.debug(f"Approaching deadline notification suppressed for {clean_email} by preference.")
            return None
        if action_type == "deadline_extension" and not prefs.get("deadline_extensions", True):
            logger.debug(f"Deadline extension notification suppressed for {clean_email} by preference.")
            return None

        # Construct notification payload
        notif_payload = {
            "recipient_email": clean_email,
            "category": cat_key,
            "action_type": action_type,
            "title": title,
            "message": message,
            "actor_name": actor_name,
            "actor_username": actor_username,
            "actor_avatar": actor_avatar,
            "target_type": target_type,
            "target_id": target_id,
            "link": link,
            "priority": priority,
            "group_key": group_key or "",
            "meta": meta or {}
        }

        # Persist with intelligent grouping
        saved = create_unified_notification(notif_payload)

        # Record notification lifecycle event
        record_notification_event(
            recipient=clean_email,
            notification_type=action_type,
            channel="in_app",
            target_id=str(saved.get("id")),
            status="delivered",
            meta={"category": cat_key, "priority": priority}
        )

        # Optional Email dispatch if requested and user has email_enabled
        if send_email and prefs.get("email_enabled", True) and prefs.get("email_notifications", True):
            try:
                self._dispatch_email_notice(clean_email, title, message, link, action_type)
            except Exception as ee:
                logger.warning(f"Email dispatch error for {clean_email}: {ee}")

        return saved

    def _dispatch_email_notice(self, email: str, title: str, message: str, link: str, action_type: str):
        """Asynchronously dispatches email copy of notification using notification_queue."""
        try:
            import asyncio
            from services.notification_queue import enqueue_notification
            html_body = f"""
            <div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; padding: 20px; color: #1e293b;">
                <h2 style="color: #2563eb;">{title}</h2>
                <p style="font-size: 14px; line-height: 1.6;">{message}</p>
                <div style="margin-top: 25px;">
                    <a href="{link}" style="background-color: #2563eb; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px;">عرض التفاصيل في المنصة</a>
                </div>
            </div>
            """
            asyncio.create_task(
                enqueue_notification(
                    channel="email",
                    recipient=email,
                    notification_type=action_type,
                    target_id=f"email_{action_type}_{int(datetime.now().timestamp())}",
                    payload={
                        "subject": title,
                        "html_content": html_body,
                        "text_content": f"{title}\n\n{message}\n\n{link}"
                    }
                )
            )
        except Exception as e:
            logger.debug(f"Email queue skipped: {e}")

    # =========================================================================
    # SCHOLARSHIP NOTIFICATIONS
    # =========================================================================

    def notify_scholarship_match(
        self,
        user_email: str,
        scholarship: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies a user when a newly verified scholarship matches their profile."""
        if not scholarship or not isinstance(scholarship, dict):
            scholarship = {
                "id": kwargs.get("scholarship_id") or "",
                "name": kwargs.get("scholarship_name") or "منحة دراسية جديدة",
                "country": kwargs.get("country") or "",
                "coverage": kwargs.get("coverage") or "تمويل دراسي كامل",
                "deadline": kwargs.get("deadline") or ""
            }

        s_name = scholarship.get("name") or "منحة دراسية جديدة"
        s_id = str(scholarship.get("id") or "")
        country = scholarship.get("country", "")
        coverage = scholarship.get("coverage", "تمويل دراسي")

        title = f"منحة دراسية جديدة متطابقة: {s_name}"
        message = f"رصد رادار ScholarPilot منحة {s_name} في {country} مع {coverage} المتوافقة مع مؤهلاتك المسجلة."

        return self.dispatch(
            recipient_email=user_email,
            category="scholarship",
            action_type="scholarship_match",
            title=title,
            message=message,
            actor_name="رادار المنح الذكي",
            actor_username="scholarpilot-radar",
            target_type="scholarship",
            target_id=s_id,
            link="/#radarSection",
            priority="high",
            group_key=f"match_{s_id}",
            meta={"country": country, "scholarship_id": s_id}
        )

    def notify_scholarship_deadline(
        self,
        user_email: str,
        scholarship: Any = None,
        days_left: int = 7,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies a user about an approaching deadline for a saved/matched scholarship."""
        if not isinstance(scholarship, dict):
            scholarship = {
                "id": str(kwargs.get("scholarship_id") or scholarship or ""),
                "name": kwargs.get("scholarship_name") or str(scholarship or "المنحة الدراسية"),
                "deadline": kwargs.get("deadline_date", "")
            }

        s_name = scholarship.get("name") or "المنحة الدراسية"
        s_id = str(scholarship.get("id") or "")
        priority = "urgent" if days_left <= 3 else "high"

        if days_left == 1:
            time_phrase = "بقي يوم واحد فقط"
        elif days_left <= 10:
            time_phrase = f"بقي {days_left} أيام فقط"
        else:
            time_phrase = f"بقي {days_left} يوماً"

        title = f"اقتراب الموعد النهائي: {s_name}"
        message = f"تنبيه هام: {time_phrase} على إغلاق التقديم لمنحة {s_name}. سارع باستكمال ملفك وتقديم طلبك."

        return self.dispatch(
            recipient_email=user_email,
            category="scholarship",
            action_type="approaching_deadline",
            title=title,
            message=message,
            actor_name="منبه المواعيد النهائية",
            actor_username="scholarpilot-deadline",
            target_type="scholarship",
            target_id=s_id,
            link="/#radarSection",
            priority=priority,
            group_key=f"deadline_{days_left}d_{s_id}",
            meta={"days_left": days_left, "scholarship_id": s_id},
            send_email=days_left in [7, 3, 1]
        )

    def notify_scholarship_extended(
        self,
        user_email: str,
        scholarship: Optional[Dict[str, Any]] = None,
        new_deadline: str = "",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies user when a scholarship application deadline is officially extended."""
        if not scholarship or not isinstance(scholarship, dict):
            scholarship = {
                "id": kwargs.get("scholarship_id") or "",
                "name": kwargs.get("scholarship_name") or "المنحة الدراسية"
            }

        s_name = scholarship.get("name") or "المنحة الدراسية"
        s_id = str(scholarship.get("id") or "")

        title = f"تمديد موعد التقديم: {s_name}"
        message = f"تم تمديد فترة التقديم لمنحة {s_name} حتى تاريخ {new_deadline}. فرصة إضافية لتجهيز مستنداتك."

        return self.dispatch(
            recipient_email=user_email,
            category="scholarship",
            action_type="deadline_extension",
            title=title,
            message=message,
            actor_name="محرر المنح",
            actor_username="scholarpilot-editor",
            target_type="scholarship",
            target_id=s_id,
            link="/#radarSection",
            priority="high",
            group_key=f"extended_{s_id}"
        )

    def notify_scholarship_updated(
        self,
        user_email: str,
        scholarship: Optional[Dict[str, Any]] = None,
        update_details: str = "",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies user when key details or requirements of a saved scholarship change."""
        if not scholarship or not isinstance(scholarship, dict):
            scholarship = {
                "id": kwargs.get("scholarship_id") or "",
                "name": kwargs.get("scholarship_name") or "المنحة الدراسية"
            }

        s_name = scholarship.get("name") or "المنحة الدراسية"
        s_id = str(scholarship.get("id") or "")

        title = f"تحديث في بيانات منحة: {s_name}"
        message = f"تم تحديث معلومات المنحة: {update_details}"

        return self.dispatch(
            recipient_email=user_email,
            category="scholarship",
            action_type="scholarship_updated",
            title=title,
            message=message,
            actor_name="محرر المنح",
            actor_username="scholarpilot-editor",
            target_type="scholarship",
            target_id=s_id,
            link="/#radarSection",
            priority="normal",
            group_key=f"updated_{s_id}"
        )

    # =========================================================================
    # COMMUNITY NOTIFICATIONS
    # =========================================================================

    def notify_post_like(
        self,
        recipient_email: str = "",
        actor: Optional[Dict[str, Any]] = None,
        post_id: str = "",
        post_title: str = "",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies post author about a like with intelligent grouping."""
        clean_recipient = recipient_email or kwargs.get("author_email") or ""
        clean_actor = actor or kwargs.get("actor_user") or {}
        clean_post_id = post_id or kwargs.get("post_id") or ""
        clean_post_title = post_title or kwargs.get("post_title") or ""

        actor_name = clean_actor.get("full_name") or "زميل أكاديمي"
        actor_uname = clean_actor.get("username") or ""
        actor_avatar = clean_actor.get("avatar_url") or ""

        if clean_actor.get("email", "").lower() == clean_recipient.lower():
            return None

        group_key = f"likes_post_{clean_post_id}"
        title = "إعجاب جديد على منشورك الأكاديمي"
        message = f"أعجب {actor_name} بمنشورك: «{clean_post_title[:60]}...»"

        return self.dispatch(
            recipient_email=clean_recipient,
            category="community",
            action_type="post_like",
            title=title,
            message=message,
            actor_name=actor_name,
            actor_username=actor_uname,
            actor_avatar=actor_avatar,
            target_type="post",
            target_id=clean_post_id,
            link="/community",
            priority="normal",
            group_key=group_key
        )

    def notify_post_comment(
        self,
        recipient_email: str = "",
        actor: Optional[Dict[str, Any]] = None,
        post_id: str = "",
        post_title: str = "",
        comment_content: str = "",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies post author about a new comment."""
        clean_recipient = recipient_email or kwargs.get("author_email") or kwargs.get("post_author_email") or ""
        clean_actor = actor or kwargs.get("actor_user") or {}
        clean_post_id = post_id or kwargs.get("post_id") or ""
        clean_post_title = post_title or kwargs.get("post_title") or ""
        clean_comment = comment_content or kwargs.get("comment_content") or ""

        actor_name = clean_actor.get("full_name") or "زميل أكاديمي"
        actor_uname = clean_actor.get("username") or ""
        actor_avatar = clean_actor.get("avatar_url") or ""

        if clean_actor.get("email", "").lower() == clean_recipient.lower():
            return None

        title = f"تعليق جديد من {actor_name}"
        message = f"علق {actor_name} على منشورك «{clean_post_title[:50]}...»: «{clean_comment[:80]}...»"

        return self.dispatch(
            recipient_email=clean_recipient,
            category="community",
            action_type="post_comment",
            title=title,
            message=message,
            actor_name=actor_name,
            actor_username=actor_uname,
            actor_avatar=actor_avatar,
            target_type="post",
            target_id=clean_post_id,
            link="/community",
            priority="high",
            group_key=f"comments_post_{clean_post_id}"
        )

    def notify_comment_reply(
        self,
        recipient_email: str = "",
        actor: Optional[Dict[str, Any]] = None,
        post_id: str = "",
        comment_id: str = "",
        reply_content: str = "",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies comment author about a direct nested reply."""
        clean_recipient = recipient_email or kwargs.get("parent_author_email") or kwargs.get("author_email") or ""
        clean_actor = actor or kwargs.get("actor_user") or {}
        clean_post_id = post_id or kwargs.get("post_id") or ""
        clean_comment_id = comment_id or kwargs.get("comment_id") or ""
        clean_reply = reply_content or kwargs.get("reply_content") or ""

        actor_name = clean_actor.get("full_name") or "زميل أكاديمي"
        actor_uname = clean_actor.get("username") or ""
        actor_avatar = clean_actor.get("avatar_url") or ""

        if clean_actor.get("email", "").lower() == clean_recipient.lower():
            return None

        title = f"رد جديد من {actor_name}"
        message = f"رد {actor_name} على تعليقك في المجتمع الأكاديمي: «{clean_reply[:80]}...»"

        return self.dispatch(
            recipient_email=clean_recipient,
            category="community",
            action_type="comment_reply",
            title=title,
            message=message,
            actor_name=actor_name,
            actor_username=actor_uname,
            actor_avatar=actor_avatar,
            target_type="comment",
            target_id=clean_comment_id,
            link="/community",
            priority="normal"
        )

    def notify_follow(
        self,
        recipient_email: str = "",
        actor: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Notifies student that another student started following them."""
        clean_recipient = recipient_email or kwargs.get("target_email") or ""
        clean_actor = actor or kwargs.get("follower_user") or {}

        actor_name = clean_actor.get("full_name") or "باحث أكاديمي"
        actor_uname = clean_actor.get("username") or ""
        actor_avatar = clean_actor.get("avatar_url") or ""

        if clean_actor.get("email", "").lower() == clean_recipient.lower():
            return None

        title = f"متابع جديد: {actor_name}"
        message = f"بدأ {actor_name} (@{actor_uname}) بمتابعة ملفك الأكاديمي ومنشوراتك."

        return self.dispatch(
            recipient_email=clean_recipient,
            category="community",
            action_type="follow",
            title=title,
            message=message,
            actor_name=actor_name,
            actor_username=actor_uname,
            actor_avatar=actor_avatar,
            target_type="profile",
            target_id=actor_uname,
            link=f"/profile/{actor_uname}" if actor_uname else "/community",
            priority="normal",
            group_key=f"follow_{actor_uname}"
        )

    def parse_and_notify_mentions(
        self,
        text: str = "",
        actor: Optional[Dict[str, Any]] = None,
        target_type: str = "post",
        target_id: str = "",
        context_title: str = "",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scans text for @username mentions, resolves target users, and sends mention notifications.
        Avoids notifying the actor themselves.
        """
        clean_text = text or kwargs.get("content") or ""
        clean_actor = actor or kwargs.get("author_user") or {}
        clean_type = target_type or kwargs.get("entity_type") or "post"
        clean_id = target_id or kwargs.get("entity_id") or ""
        clean_title = context_title or kwargs.get("entity_title") or ""

        if not clean_text:
            return []

        handles = set(re.findall(r"@([a-zA-Z0-9_-]{3,50})", clean_text))
        if not handles:
            return []

        actor_uname = (clean_actor.get("username") or "").lower()
        actor_name = clean_actor.get("full_name") or "زميل أكاديمي"
        results = []

        for h in handles:
            if h.lower() == actor_uname:
                continue
            target_user = get_user_by_username(h)
            if not target_user:
                continue

            target_email = target_user.get("email")
            if not target_email or target_email.lower() == clean_actor.get("email", "").lower():
                continue

            action_type = "post_mention" if clean_type == "post" else "comment_mention"
            title = f"تمت الإشارة إليك بواسطة {actor_name}"
            snippet = clean_text.strip()[:100]
            message = f"أشار إليك {actor_name} في {clean_title or 'محادثة أكاديمية'}: «{snippet}...»"

            res = self.dispatch(
                recipient_email=target_email,
                category="community",
                action_type=action_type,
                title=title,
                message=message,
                actor_name=actor_name,
                actor_username=clean_actor.get("username", ""),
                actor_avatar=clean_actor.get("avatar_url", ""),
                target_type=clean_type,
                target_id=clean_id,
                link="/community",
                priority="high"
            )
            if res:
                results.append(res)

        return results

    # =========================================================================
    # NEWS NOTIFICATIONS
    # =========================================================================

    def notify_important_news(
        self,
        article: Dict[str, Any],
        recipient_emails: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Broadcasts important/breaking scholarship news to interested students."""
        art_id = article.get("id")
        title = f"خبر عاجل: {article.get('title')}"
        summary = article.get("summary", "")
        country = article.get("country", "")

        users = get_all_users()
        if recipient_emails is not None:
            clean_recipients = {r.strip().lower() for r in recipient_emails}
            users = [u for u in users if u.get("email", "").strip().lower() in clean_recipients]
            # If specified user is not in users list, synthesize entry
            existing_emails = {u.get("email", "").strip().lower() for u in users}
            for re_mail in clean_recipients:
                if re_mail not in existing_emails:
                    users.append({"email": re_mail})

        created = []

        for u in users:
            u_email = u.get("email")
            if not u_email:
                continue

            prefs = self.get_user_preferences(u_email)
            if not prefs.get("news_enabled", True) or not prefs.get("news_breaking", True):
                continue

            sub_countries = prefs.get("subscribed_countries", [])
            if sub_countries and country and not any(sc in country or country in sc for sc in sub_countries):
                continue

            res = self.dispatch(
                recipient_email=u_email,
                category="news",
                action_type="news_published",
                title=title,
                message=summary[:160] + "...",
                actor_name="ScholarPilot Newsroom",
                actor_username="newsroom",
                target_type="news",
                target_id=str(art_id),
                link="/news",
                priority="high",
                group_key=f"news_{art_id}"
            )
            if res:
                created.append(res)

        return created

    # =========================================================================
    # SYSTEM NOTIFICATIONS
    # =========================================================================

    def notify_profile_completion(self, user_email: str, completeness_percentage: int) -> Optional[Dict[str, Any]]:
        """Notifies user of profile milestones (e.g. 80%, 100%)."""
        title = f"ملفك الأكاديمي مكتمل بنسبة {completeness_percentage}%!"
        if completeness_percentage >= 100:
            msg = "تهانينا! ملفك الأكاديمي مكتمل بنسبة 100%، مما يرفع دقة مطابقة المنح إلى أقصى كفاءة استشارية."
            priority = "high"
        else:
            msg = f"أحسنت! ملفك الأكاديمي مكتمل بنسبة {completeness_percentage}%. أكمل بقية المهارات واللغات لزيادة فرص قبولك."
            priority = "normal"

        return self.dispatch(
            recipient_email=user_email,
            category="system",
            action_type="profile_milestone",
            title=title,
            message=msg,
            actor_name="ScholarPilot Assistant",
            actor_username="scholarpilot-system",
            target_type="profile",
            target_id=user_email,
            link="/dashboard",
            priority=priority,
            group_key=f"profile_milestone_{completeness_percentage}"
        )

    def notify_account_verification(self, user_email: str) -> Optional[Dict[str, Any]]:
        """Notifies user upon successful email verification."""
        return self.dispatch(
            recipient_email=user_email,
            category="system",
            action_type="account_verified",
            title="تم تأكيد بريدك الإلكتروني بنجاح!",
            message="حسابك الأكاديمي مفعل وموثق بالكامل الآن. يمكنك استكشاف المنح المطابقة والتفاعل مع المجتمع الأكاديمي.",
            actor_name="ScholarPilot Security",
            actor_username="scholarpilot-security",
            target_type="account",
            target_id=user_email,
            link="/dashboard",
            priority="high",
            group_key="account_verified"
        )

    def notify_system_event(
        self,
        recipient_email: str,
        event_type: str,
        title: str,
        message: str,
        link: str = "/notifications",
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Generic system event notification dispatcher."""
        return self.dispatch(
            recipient_email=recipient_email,
            category="system",
            action_type=event_type,
            title=title,
            message=message,
            actor_name="ScholarPilot System",
            actor_username="scholarpilot-system",
            link=link,
            priority="normal",
            target_type="system",
            target_id=event_type
        )

    def notify_platform_announcement(self, title: str, message: str, link: str = "/") -> int:
        """Broadcasts a high-priority system announcement to all registered users."""
        users = get_all_users()
        count = 0
        for u in users:
            u_email = u.get("email")
            if not u_email:
                continue
            res = self.dispatch(
                recipient_email=u_email,
                category="system",
                action_type="platform_announcement",
                title=title,
                message=message,
                actor_name="إدارة ScholarPilot",
                actor_username="scholarpilot-admin",
                target_type="announcement",
                target_id=str(int(datetime.now().timestamp())),
                link=link,
                priority="high"
            )
            if res:
                count += 1
        return count

    # =========================================================================
    # FUTURE-READY ARCHITECTURAL HOOKS (Student Groups, Chat, Mentorship, Events)
    # =========================================================================

    def notify_group_activity(
        self,
        recipient_email: str,
        group_name: str,
        group_id: str,
        actor_name: str,
        activity_text: str
    ) -> Optional[Dict[str, Any]]:
        """Future hook: Notifies student about activity in an academic group or study circle."""
        return self.dispatch(
            recipient_email=recipient_email,
            category="group",
            action_type="group_activity",
            title=f"نشاط جديد في مجموعة «{group_name}»",
            message=f"{actor_name}: {activity_text}",
            actor_name=actor_name,
            target_type="group",
            target_id=group_id,
            link=f"/groups/{group_id}"
        )

    def notify_chat_message(
        self,
        recipient_email: str,
        sender_name: str,
        sender_username: str,
        chat_id: str,
        snippet: str
    ) -> Optional[Dict[str, Any]]:
        """Future hook: Notifies student about direct peer messages."""
        return self.dispatch(
            recipient_email=recipient_email,
            category="chat",
            action_type="chat_message",
            title=f"رسالة جديدة من {sender_name}",
            message=snippet[:100] + "...",
            actor_name=sender_name,
            actor_username=sender_username,
            target_type="chat",
            target_id=chat_id,
            link=f"/messages/{chat_id}",
            priority="high",
            group_key=f"chat_{chat_id}"
        )

    def notify_mentorship_event(
        self,
        recipient_email: str,
        title: str,
        message: str,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """Future hook: Notifies student about mentorship sessions or advisor feedback."""
        return self.dispatch(
            recipient_email=recipient_email,
            category="system",
            action_type="mentorship_session",
            title=title,
            message=message,
            target_type="mentorship",
            target_id=program_id,
            link="/assistant",
            priority="high"
        )

    def notify_event_reminder(
        self,
        recipient_email: str,
        event_title: str,
        event_id: str,
        time_str: str
    ) -> Optional[Dict[str, Any]]:
        """Future hook: Notifies student about upcoming academic webinars or conferences."""
        return self.dispatch(
            recipient_email=recipient_email,
            category="system",
            action_type="event_reminder",
            title=f"تذكير بفعالية: {event_title}",
            message=f"ستبدأ الفعالية الأكاديمية خلال {time_str}. لا تفوت الحضور والاستفادة.",
            target_type="event",
            target_id=event_id,
            link="/community",
            priority="high"
        )


# Global singleton instance
notification_service = NotificationService()
