"""
Database Service for ScholarPilot AI.
Supports Neon PostgreSQL in production, with fallback to SQLite or JSON data stores.
Provides automatic table creation and automatic data migration from JSON files on first boot.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager

logger = logging.getLogger("scholarpilot.db")

# Detect database configuration
raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url and raw_db_url.startswith("postgres://"):
    # SQLAlchemy requires postgresql:// instead of legacy postgres://
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
USERS_JSON = os.path.join(DATA_DIR, "users.json")
SUBSCRIBERS_JSON = os.path.join(DATA_DIR, "subscribers.json")
SCHOLARSHIPS_JSON = os.path.join(DATA_DIR, "live_scholarships.json")
IN_APP_NOTIFICATIONS_JSON = os.path.join(DATA_DIR, "in_app_notifications.json")
NOTIFICATION_EVENTS_JSON = os.path.join(DATA_DIR, "notification_events.json")
COMMUNITY_STORIES_JSON = os.path.join(DATA_DIR, "community_stories.json")
COMMUNITY_POSTS_JSON = os.path.join(DATA_DIR, "community_posts.json")
COMMUNITY_COMMENTS_JSON = os.path.join(DATA_DIR, "community_comments.json")
COMMUNITY_FOLLOWS_JSON = os.path.join(DATA_DIR, "community_follows.json")
COMMUNITY_REPORTS_JSON = os.path.join(DATA_DIR, "community_reports.json")
COMMUNITY_NOTIFICATIONS_JSON = os.path.join(DATA_DIR, "community_notifications.json")
NEWS_ARTICLES_JSON = os.path.join(DATA_DIR, "news_articles.json")
NEWS_COMMENTS_JSON = os.path.join(DATA_DIR, "news_comments.json")
UNIFIED_NOTIFICATIONS_JSON = os.path.join(DATA_DIR, "unified_notifications.json")
NOTIFICATION_PREFERENCES_JSON = os.path.join(DATA_DIR, "notification_preferences.json")

# Try importing SQLAlchemy
HAS_SQLALCHEMY = False
Base = None
engine = None
SessionLocal = None
UserDB = None
SubscriberDB = None
LiveScholarshipDB = None
NotificationHistoryDB = None
InAppNotificationDB = None
NotificationEventDB = None
CommunityStoryDB = None
CommunityPostDB = None
CommunityCommentDB = None
CommunityFollowDB = None
CommunityReportDB = None
CommunityNotificationDB = None
NewsArticleDB = None
NewsCommentDB = None
UnifiedNotificationDB = None

try:
    from sqlalchemy import (
        create_engine, Column, Integer, String, Text, Boolean, JSON, inspect, text
    )
    from sqlalchemy.orm import declarative_base, sessionmaker

    HAS_SQLALCHEMY = True
    Base = declarative_base()

    # Define PostgreSQL / SQLite models
    class UserDB(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, autoincrement=True)
        email = Column(String(120), unique=True, index=True, nullable=False)
        username = Column(String(80), unique=True, index=True, nullable=True)
        full_name = Column(String(120), default="Student")
        role = Column(String(50), default="student")
        salt = Column(String(64), nullable=False)
        password_hash = Column(String(256), nullable=False)

        # Profile & Academic Identity
        avatar_url = Column(String(500), nullable=True)
        cover_url = Column(String(500), nullable=True)
        city = Column(String(100), default="")
        university = Column(String(150), default="")
        degree = Column(String(100), default="Undergraduate (Bachelor's)")
        majors = Column(JSON, default=list)
        graduation_year = Column(String(50), default="")
        bio = Column(Text, default="")
        gpa = Column(String(50), default="85%")
        english_level = Column(String(100), default="Intermediate")
        country = Column(String(100), default="Palestine")
        talents_experience = Column(Text, default="")

        # Academic Skills, Languages & Interests
        languages = Column(JSON, default=list)
        skills = Column(JSON, default=list)
        interests = Column(JSON, default=list)
        target_countries = Column(JSON, default=list)
        scholarship_interests = Column(JSON, default=list)

        # Social & Portfolio Networks
        social_links = Column(JSON, default=dict)

        # Saved scholarships & Matching Preferences
        saved_scholarships = Column(JSON, default=list)
        preferred_countries = Column(JSON, default=list)
        funding_type = Column(String(50), default="Any")
        email_notifications = Column(Boolean, default=True)
        telegram_notifications = Column(Boolean, default=False)
        telegram_chat_id = Column(String(100), nullable=True)

        # Verification, Security & Privacy
        email_verified = Column(Boolean, default=False)
        verification_code = Column(String(50), nullable=True)
        reset_token = Column(String(100), nullable=True)
        reset_token_expires = Column(String(50), nullable=True)
        privacy_settings = Column(JSON, default=dict)

        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            uname = self.username
            if not uname:
                uname = (self.email or "").split("@")[0].lower()
            return {
                "id": self.id,
                "email": self.email,
                "username": uname,
                "full_name": self.full_name or "Student",
                "role": self.role or "student",
                "salt": self.salt,
                "password_hash": self.password_hash,
                "avatar_url": self.avatar_url or "",
                "cover_url": self.cover_url or "",
                "city": self.city or "",
                "university": self.university or "",
                "degree": self.degree or "Undergraduate (Bachelor's)",
                "majors": self.majors or [],
                "graduation_year": self.graduation_year or "",
                "bio": self.bio or "",
                "gpa": self.gpa or "85%",
                "english_level": self.english_level or "Intermediate",
                "country": self.country or "Palestine",
                "talents_experience": self.talents_experience or "",
                "languages": self.languages or [],
                "skills": self.skills or [],
                "interests": self.interests or [],
                "target_countries": self.target_countries or [],
                "scholarship_interests": self.scholarship_interests or [],
                "social_links": self.social_links or {
                    "whatsapp": "",
                    "linkedin": "",
                    "github": "",
                    "facebook": "",
                    "instagram": "",
                    "twitter": "",
                    "telegram": "",
                    "portfolio": "",
                    "website": ""
                },
                "saved_scholarships": self.saved_scholarships or [],
                "preferred_countries": self.preferred_countries or [],
                "funding_type": self.funding_type or "Any",
                "email_notifications": self.email_notifications if self.email_notifications is not None else True,
                "telegram_notifications": self.telegram_notifications if self.telegram_notifications is not None else False,
                "telegram_chat_id": self.telegram_chat_id or "",
                "email_verified": bool(self.email_verified),
                "verification_code": self.verification_code or "",
                "reset_token": self.reset_token or "",
                "reset_token_expires": self.reset_token_expires or "",
                "privacy_settings": self.privacy_settings or {
                    "public_profile": True,
                    "show_gpa": True,
                    "show_contact": True
                },
                "created_at": self.created_at,
                "updated_at": getattr(self, "updated_at", None) or self.created_at
            }

    class SubscriberDB(Base):
        __tablename__ = "subscribers"

        id = Column(Integer, primary_key=True, autoincrement=True)
        email = Column(String(120), unique=True, index=True, nullable=False)
        full_name = Column(String(120), default="Student")
        degree = Column(String(100), default="Undergraduate (Bachelor's)")
        majors = Column(JSON, default=list)
        gpa = Column(String(50), default="85%")
        english_level = Column(String(100), default="Intermediate")
        target_destinations = Column(JSON, default=list)
        country = Column(String(100), default="Palestine")
        talents_experience = Column(Text, default="")
        saved_scholarships = Column(JSON, default=list)
        # Notification & Matching Preferences
        preferred_countries = Column(JSON, default=list)
        funding_type = Column(String(50), default="Any")
        email_notifications = Column(Boolean, default=True)
        telegram_notifications = Column(Boolean, default=False)
        telegram_chat_id = Column(String(100), nullable=True)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        last_sent_at = Column(String(50), nullable=True)
        status = Column(String(50), default="active")

        def to_dict(self) -> Dict[str, Any]:
            return {
                "email": self.email,
                "full_name": self.full_name,
                "degree": self.degree,
                "majors": self.majors or [],
                "gpa": self.gpa,
                "english_level": self.english_level,
                "target_destinations": self.target_destinations or ["Any"],
                "country": self.country,
                "talents_experience": self.talents_experience or "",
                "saved_scholarships": self.saved_scholarships or [],
                "preferred_countries": self.preferred_countries or [],
                "funding_type": self.funding_type or "Any",
                "email_notifications": self.email_notifications if self.email_notifications is not None else True,
                "telegram_notifications": self.telegram_notifications if self.telegram_notifications is not None else False,
                "telegram_chat_id": self.telegram_chat_id,
                "created_at": self.created_at,
                "last_sent_at": self.last_sent_at,
                "status": self.status
            }

    class LiveScholarshipDB(Base):
        __tablename__ = "live_scholarships"

        id = Column(String(100), primary_key=True)
        name = Column(String(255), nullable=False)
        university = Column(String(255))
        country = Column(String(100))
        degree = Column(String(100))
        match_score = Column(String(50))
        match_label = Column(String(100))
        status = Column(String(100))
        status_class = Column(String(50))
        deadline = Column(String(50))
        deadline_display = Column(String(100))
        deadline_days = Column(String(100))
        coverage = Column(Text)
        requirements = Column(Text)
        link = Column(String(500))
        telegram_message_id = Column(String(50), nullable=True)
        telegram_published_at = Column(String(50), nullable=True)
        is_active = Column(Boolean, default=True)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "name": self.name,
                "university": self.university,
                "country": self.country,
                "degree": self.degree,
                "matchScore": self.match_score,
                "matchLabel": self.match_label,
                "status": self.status,
                "statusClass": self.status_class,
                "deadline": self.deadline,
                "deadline_display": self.deadline_display,
                "deadlineDays": self.deadline_days,
                "coverage": self.coverage,
                "requirements": self.requirements,
                "link": self.link,
                "telegram_message_id": self.telegram_message_id,
                "telegram_published_at": self.telegram_published_at,
                "is_active": self.is_active
            }

    class NotificationHistoryDB(Base):
        __tablename__ = "notification_history"

        id = Column(Integer, primary_key=True, autoincrement=True)
        recipient = Column(String(120), index=True, nullable=False)
        notification_type = Column(String(50), index=True, nullable=False)  # weekly_digest, new_scholarship_alert, deadline_reminder
        target_id = Column(String(200), index=True, nullable=False)        # unique key for idempotency e.g. "deadline_7d_hungaricum"
        subject = Column(String(255))
        sent_at = Column(String(50), default=lambda: datetime.now().isoformat())
        status = Column(String(50), default="sent")
        details = Column(JSON, default=dict)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "recipient": self.recipient,
                "notification_type": self.notification_type,
                "target_id": self.target_id,
                "subject": self.subject,
                "sent_at": self.sent_at,
                "status": self.status,
                "details": self.details or {}
            }

    class InAppNotificationDB(Base):
        __tablename__ = "in_app_notifications"

        id = Column(Integer, primary_key=True, autoincrement=True)
        recipient = Column(String(120), index=True, nullable=False)
        title = Column(String(255), nullable=False)
        message = Column(Text, nullable=False)
        type = Column(String(50), default="match")  # match, deadline, digest, system
        scholarship_id = Column(String(100), nullable=True)
        link = Column(String(500), nullable=True)
        is_read = Column(Boolean, default=False)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "recipient": self.recipient,
                "title": self.title,
                "message": self.message,
                "type": self.type,
                "scholarship_id": self.scholarship_id,
                "link": self.link,
                "is_read": self.is_read,
                "created_at": self.created_at
            }

    class NotificationEventDB(Base):
        __tablename__ = "notification_events"

        id = Column(Integer, primary_key=True, autoincrement=True)
        recipient = Column(String(120), index=True, nullable=False)
        notification_type = Column(String(50), nullable=False)
        channel = Column(String(30), default="email")  # email, in_app, telegram
        target_id = Column(String(200), index=True, nullable=False)
        status = Column(String(50), default="created")  # created, sent, delivered, opened, clicked
        timestamp = Column(String(50), default=lambda: datetime.now().isoformat())
        meta = Column(JSON, default=dict)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "recipient": self.recipient,
                "notification_type": self.notification_type,
                "channel": self.channel,
                "target_id": self.target_id,
                "status": self.status,
                "timestamp": self.timestamp,
                "meta": self.meta or {}
            }

    class CommunityStoryDB(Base):
        __tablename__ = "community_stories"

        id = Column(String(100), primary_key=True)
        author_name = Column(String(120), default="باحث أكاديمي")
        author_email = Column(String(120), index=True, nullable=True)
        author_country = Column(String(100), default="فلسطين")
        scholarship_id = Column(String(100), index=True, nullable=False)
        scholarship_name = Column(String(255), nullable=False)
        university = Column(String(255), nullable=True)
        degree = Column(String(100), default="ماجستير")
        field_of_study = Column(String(150), default="تخصص أكاديمي")
        acceptance_year = Column(String(50), default="2025/2026")
        title = Column(String(255), nullable=False)
        story_text = Column(Text, nullable=False)
        key_advice = Column(JSON, default=list)
        gpa = Column(String(50), default="85%+")
        is_verified = Column(Boolean, default=True)
        upvotes = Column(Integer, default=0)
        upvoted_by = Column(JSON, default=list)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        tags = Column(JSON, default=list)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "author_name": self.author_name,
                "author_country": self.author_country,
                "scholarship_id": self.scholarship_id,
                "scholarship_name": self.scholarship_name,
                "university": self.university or "",
                "degree": self.degree,
                "field_of_study": self.field_of_study,
                "acceptance_year": self.acceptance_year,
                "title": self.title,
                "story_text": self.story_text,
                "key_advice": self.key_advice or [],
                "gpa": self.gpa,
                "is_verified": bool(self.is_verified),
                "upvotes": self.upvotes or 0,
                "created_at": self.created_at,
                "tags": self.tags or []
            }

    class CommunityPostDB(Base):
        __tablename__ = "community_posts"

        id = Column(String(100), primary_key=True)
        author_id = Column(String(150), index=True, nullable=False)
        author_name = Column(String(150), nullable=False)
        author_username = Column(String(100), index=True, nullable=False)
        author_avatar = Column(Text, default="")
        author_university = Column(String(255), default="")
        author_degree = Column(String(100), default="")
        category = Column(String(80), index=True, default="general_discussion")
        title = Column(String(300), default="")
        content = Column(Text, nullable=False)
        post_type = Column(String(50), default="text")
        media_urls = Column(JSON, default=list)
        video_url = Column(Text, default="")
        link_url = Column(Text, default="")
        link_meta = Column(JSON, default=dict)
        scholarship_id = Column(String(100), index=True, nullable=True)
        scholarship_name = Column(String(255), nullable=True)
        country = Column(String(100), default="")
        university = Column(String(255), default="")
        major = Column(String(150), default="")
        likes_count = Column(Integer, default=0)
        liked_by = Column(JSON, default=list)
        saved_by = Column(JSON, default=list)
        shares_count = Column(Integer, default=0)
        comments_count = Column(Integer, default=0)
        is_success_story = Column(Boolean, default=False)
        success_details = Column(JSON, default=dict)
        is_pinned = Column(Boolean, default=False)
        is_hidden = Column(Boolean, default=False)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "author_id": self.author_id,
                "author_name": self.author_name,
                "author_username": self.author_username,
                "author_avatar": self.author_avatar or "",
                "author_university": self.author_university or "",
                "author_degree": self.author_degree or "",
                "category": self.category or "general_discussion",
                "title": self.title or "",
                "content": self.content or "",
                "post_type": self.post_type or "text",
                "media_urls": self.media_urls or [],
                "video_url": self.video_url or "",
                "link_url": self.link_url or "",
                "link_meta": self.link_meta or {},
                "scholarship_id": self.scholarship_id,
                "scholarship_name": self.scholarship_name,
                "country": self.country or "",
                "university": self.university or "",
                "major": self.major or "",
                "likes_count": self.likes_count or 0,
                "liked_by": self.liked_by or [],
                "saved_by": self.saved_by or [],
                "shares_count": self.shares_count or 0,
                "comments_count": self.comments_count or 0,
                "is_success_story": bool(self.is_success_story),
                "success_details": self.success_details or {},
                "is_pinned": bool(self.is_pinned),
                "is_hidden": bool(self.is_hidden),
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }

    class CommunityCommentDB(Base):
        __tablename__ = "community_comments"

        id = Column(String(100), primary_key=True)
        post_id = Column(String(100), index=True, nullable=False)
        parent_id = Column(String(100), index=True, nullable=True)
        author_id = Column(String(150), index=True, nullable=False)
        author_name = Column(String(150), nullable=False)
        author_username = Column(String(100), nullable=False)
        author_avatar = Column(Text, default="")
        author_university = Column(String(255), default="")
        content = Column(Text, nullable=False)
        likes_count = Column(Integer, default=0)
        liked_by = Column(JSON, default=list)
        is_edited = Column(Boolean, default=False)
        is_hidden = Column(Boolean, default=False)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "post_id": self.post_id,
                "parent_id": self.parent_id,
                "author_id": self.author_id,
                "author_name": self.author_name,
                "author_username": self.author_username,
                "author_avatar": self.author_avatar or "",
                "author_university": self.author_university or "",
                "content": self.content or "",
                "likes_count": self.likes_count or 0,
                "liked_by": self.liked_by or [],
                "is_edited": bool(self.is_edited),
                "is_hidden": bool(self.is_hidden),
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }

    class CommunityFollowDB(Base):
        __tablename__ = "community_follows"

        id = Column(String(100), primary_key=True)
        follower_email = Column(String(150), index=True, nullable=False)
        following_email = Column(String(150), index=True, nullable=False)
        following_username = Column(String(100), index=True, nullable=False)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "follower_email": self.follower_email,
                "following_email": self.following_email,
                "following_username": self.following_username,
                "created_at": self.created_at
            }

    class CommunityReportDB(Base):
        __tablename__ = "community_reports"

        id = Column(String(100), primary_key=True)
        reporter_email = Column(String(150), index=True, nullable=False)
        target_type = Column(String(50), nullable=False)
        target_id = Column(String(100), index=True, nullable=False)
        reason = Column(String(150), nullable=False)
        details = Column(Text, default="")
        status = Column(String(50), default="pending")
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "reporter_email": self.reporter_email,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "reason": self.reason,
                "details": self.details or "",
                "status": self.status,
                "created_at": self.created_at
            }

    class CommunityNotificationDB(Base):
        __tablename__ = "community_notifications"

        id = Column(String(100), primary_key=True)
        recipient_email = Column(String(150), index=True, nullable=False)
        actor_name = Column(String(150), default="")
        actor_username = Column(String(100), default="")
        actor_avatar = Column(Text, default="")
        action_type = Column(String(50), nullable=False)
        target_id = Column(String(100), default="")
        message = Column(Text, nullable=False)
        is_read = Column(Boolean, default=False)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "recipient_email": self.recipient_email,
                "actor_name": self.actor_name or "",
                "actor_username": self.actor_username or "",
                "actor_avatar": self.actor_avatar or "",
                "action_type": self.action_type,
                "target_id": self.target_id or "",
                "message": self.message,
                "is_read": bool(self.is_read),
                "created_at": self.created_at
            }

    class NewsArticleDB(Base):
        __tablename__ = "news_articles"

        id = Column(String(100), primary_key=True)
        title = Column(String(255), nullable=False)
        summary = Column(Text, nullable=False)
        content = Column(Text, nullable=False)
        category = Column(String(100), index=True, nullable=False)
        category_label = Column(String(100), default="منح دراسية")
        publish_date = Column(String(50), default=lambda: datetime.now().isoformat())
        source_name = Column(String(150), default="ScholarPilot Newsroom")
        source_url = Column(String(500), nullable=True)
        image_url = Column(String(500), nullable=True)
        country = Column(String(100), default="")
        degree_level = Column(String(100), default="")
        scholarship_id = Column(String(100), index=True, nullable=True)
        deadline = Column(String(50), nullable=True)
        is_expired = Column(Boolean, default=False, index=True)
        is_featured = Column(Boolean, default=False, index=True)
        is_trending = Column(Boolean, default=False, index=True)
        views_count = Column(Integer, default=0)
        shares_count = Column(Integer, default=0)
        comments_count = Column(Integer, default=0)
        saved_by = Column(JSON, default=list)
        telegram_message_id = Column(String(50), nullable=True)
        telegram_published_at = Column(String(50), nullable=True)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "title": self.title,
                "summary": self.summary,
                "content": self.content,
                "category": self.category,
                "category_label": self.category_label,
                "publish_date": self.publish_date,
                "source_name": self.source_name,
                "source_url": self.source_url or "",
                "image_url": self.image_url or "",
                "country": self.country or "",
                "degree_level": self.degree_level or "",
                "scholarship_id": self.scholarship_id,
                "deadline": self.deadline,
                "is_expired": bool(self.is_expired),
                "is_featured": bool(self.is_featured),
                "is_trending": bool(self.is_trending),
                "views_count": self.views_count or 0,
                "shares_count": self.shares_count or 0,
                "comments_count": self.comments_count or 0,
                "saved_by": self.saved_by or [],
                "telegram_message_id": self.telegram_message_id,
                "telegram_published_at": self.telegram_published_at,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }

    class NewsCommentDB(Base):
        __tablename__ = "news_comments"

        id = Column(String(100), primary_key=True)
        article_id = Column(String(100), index=True, nullable=False)
        parent_id = Column(String(100), index=True, nullable=True)
        author_id = Column(String(150), index=True, nullable=False)
        author_name = Column(String(150), nullable=False)
        author_username = Column(String(100), nullable=False)
        author_avatar = Column(Text, default="")
        author_university = Column(String(255), default="")
        content = Column(Text, nullable=False)
        likes_count = Column(Integer, default=0)
        liked_by = Column(JSON, default=list)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "article_id": self.article_id,
                "parent_id": self.parent_id,
                "author_id": self.author_id,
                "author_name": self.author_name,
                "author_username": self.author_username,
                "author_avatar": self.author_avatar or "",
                "author_university": self.author_university or "",
                "content": self.content,
                "likes_count": self.likes_count or 0,
                "liked_by": self.liked_by or [],
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }

    class UnifiedNotificationDB(Base):
        __tablename__ = "unified_notifications"

        id = Column(String(100), primary_key=True)
        recipient_email = Column(String(150), index=True, nullable=False)
        category = Column(String(50), index=True, nullable=False) # scholarship, community, news, system, group, chat, mentorship, event
        action_type = Column(String(80), index=True, nullable=False)
        title = Column(String(255), nullable=False)
        message = Column(Text, nullable=False)
        actor_name = Column(String(150), default="")
        actor_username = Column(String(100), default="")
        actor_avatar = Column(Text, default="")
        target_type = Column(String(50), default="")
        target_id = Column(String(100), default="")
        link = Column(String(500), default="")
        is_read = Column(Boolean, default=False, index=True)
        is_archived = Column(Boolean, default=False, index=True)
        priority = Column(String(30), default="normal") # low, normal, high, urgent
        group_key = Column(String(100), nullable=True, index=True)
        count = Column(Integer, default=1)
        meta = Column(JSON, default=dict)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())
        updated_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "recipient_email": self.recipient_email,
                "category": self.category,
                "action_type": self.action_type,
                "title": self.title,
                "message": self.message,
                "actor_name": self.actor_name or "",
                "actor_username": self.actor_username or "",
                "actor_avatar": self.actor_avatar or "",
                "target_type": self.target_type or "",
                "target_id": self.target_id or "",
                "link": self.link or "",
                "is_read": bool(self.is_read),
                "is_archived": bool(self.is_archived),
                "priority": self.priority or "normal",
                "group_key": self.group_key or "",
                "count": self.count or 1,
                "meta": self.meta or {},
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }

    # Connect to PostgreSQL (Neon) or fallback to SQLite
    active_url = raw_db_url
    if not active_url:
        os.makedirs(DATA_DIR, exist_ok=True)
        sqlite_path = os.path.join(DATA_DIR, "scholarpilot.db").replace("\\", "/")
        active_url = f"sqlite:///{sqlite_path}"

    connect_args = {}
    if active_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    elif "sslmode" not in active_url and "neon.tech" in active_url:
        connect_args = {"sslmode": "require"}

    try:
        engine = create_engine(
            active_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_recycle=300
        )
    except Exception as d_err:
        if "psycopg" in str(d_err).lower() and active_url.startswith("postgresql://") and not active_url.startswith("postgresql+"):
            alt_url = active_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            engine = create_engine(
                alt_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_recycle=300
            )
        else:
            raise d_err

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database Engine initialized for: {'Neon PostgreSQL' if 'postgres' in active_url else 'SQLite fallback'}")

except Exception as e:
    HAS_SQLALCHEMY = False
    logger.warning(f"SQLAlchemy / Database driver not active: {e}. Falling back to atomic JSON files.")


@contextmanager
def get_db_session():
    """Context manager for safe database transactions with auto-rollback."""
    if not HAS_SQLALCHEMY or SessionLocal is None:
        yield None
        return

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        session.close()


def is_db_available() -> bool:
    """Returns True if database engine is configured and reachable."""
    if not HAS_SQLALCHEMY or engine is None:
        return False
    try:
        with engine.connect() as conn:
            return True
    except Exception as e:
        logger.debug(f"Database ping failed: {e}")
        return False


def init_db_and_migrate():
    """
    Creates all database tables on PostgreSQL/Neon and auto-migrates initial
    records from JSON files if database tables are currently empty.
    """
    if not HAS_SQLALCHEMY or engine is None or Base is None:
        logger.info("SQLAlchemy not available; using local JSON file store.")
        return False

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema tables verified/created successfully.")

        # Auto-alter users table to add missing profile and security columns if needed
        try:
            inspector = inspect(engine)
            if "users" in inspector.get_table_names():
                existing_cols = {col["name"] for col in inspector.get_columns("users")}
                cols_to_add = [
                    ("username", "VARCHAR(80)"),
                    ("avatar_url", "VARCHAR(500)"),
                    ("cover_url", "VARCHAR(500)"),
                    ("city", "VARCHAR(100)"),
                    ("university", "VARCHAR(150)"),
                    ("graduation_year", "VARCHAR(50)"),
                    ("bio", "TEXT"),
                    ("languages", "TEXT"),
                    ("skills", "TEXT"),
                    ("interests", "TEXT"),
                    ("target_countries", "TEXT"),
                    ("scholarship_interests", "TEXT"),
                    ("social_links", "TEXT"),
                    ("email_verified", "BOOLEAN DEFAULT 0"),
                    ("verification_code", "VARCHAR(50)"),
                    ("reset_token", "VARCHAR(100)"),
                    ("reset_token_expires", "VARCHAR(50)"),
                    ("privacy_settings", "TEXT"),
                    ("updated_at", "VARCHAR(50)")
                ]
                with engine.connect() as conn:
                    for col_name, col_type in cols_to_add:
                        if col_name not in existing_cols:
                            try:
                                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                                if hasattr(conn, "commit"):
                                    conn.commit()
                                logger.info(f"Added column {col_name} to users table.")
                            except Exception as ce:
                                logger.debug(f"Could not add column {col_name}: {ce}")
        except Exception as insp_e:
            logger.debug(f"Schema inspection warning: {insp_e}")

        # Auto-migrate initial data from JSON to Neon DB
        with get_db_session() as db:
            if db is None:
                return False

            # 1. Migrate Users
            existing_users_count = db.query(UserDB).count()
            if existing_users_count == 0 and os.path.exists(USERS_JSON):
                try:
                    with open(USERS_JSON, "r", encoding="utf-8") as f:
                        users_data = json.load(f)
                    for u in users_data:
                        db.add(UserDB(
                            email=u.get("email", "").lower(),
                            full_name=u.get("full_name", "Student"),
                            role=u.get("role", "student"),
                            salt=u.get("salt", "00"),
                            password_hash=u.get("password_hash", ""),
                            degree=u.get("degree", "Undergraduate (Bachelor's)"),
                            majors=u.get("majors", []),
                            gpa=u.get("gpa", "85%"),
                            english_level=u.get("english_level", "Intermediate"),
                            country=u.get("country", "Palestine"),
                            talents_experience=u.get("talents_experience", ""),
                            saved_scholarships=u.get("saved_scholarships", []),
                            created_at=u.get("created_at", datetime.now().isoformat())
                        ))
                    logger.info(f"Auto-migrated {len(users_data)} users to Database.")
                except Exception as ue:
                    logger.warning(f"User auto-migration error: {ue}")

            # 2. Migrate Subscribers
            existing_subs_count = db.query(SubscriberDB).count()
            if existing_subs_count == 0 and os.path.exists(SUBSCRIBERS_JSON):
                try:
                    with open(SUBSCRIBERS_JSON, "r", encoding="utf-8") as f:
                        subs_data = json.load(f)
                    for s in subs_data:
                        db.add(SubscriberDB(
                            email=s.get("email", "").lower(),
                            full_name=s.get("full_name", "Student"),
                            degree=s.get("degree", "Undergraduate (Bachelor's)"),
                            majors=s.get("majors", []),
                            gpa=s.get("gpa", "85%"),
                            english_level=s.get("english_level", "Intermediate"),
                            target_destinations=s.get("target_destinations", ["Any"]),
                            country=s.get("country", "Palestine"),
                            talents_experience=s.get("talents_experience", ""),
                            saved_scholarships=s.get("saved_scholarships", []),
                            created_at=s.get("created_at", datetime.now().isoformat()),
                            last_sent_at=s.get("last_sent_at"),
                            status=s.get("status", "active")
                        ))
                    logger.info(f"Auto-migrated {len(subs_data)} subscribers to Database.")
                except Exception as se:
                    logger.warning(f"Subscriber auto-migration error: {se}")

            # 3. Migrate Live Scholarships
            existing_sch_count = db.query(LiveScholarshipDB).count()
            if existing_sch_count == 0 and os.path.exists(SCHOLARSHIPS_JSON):
                try:
                    with open(SCHOLARSHIPS_JSON, "r", encoding="utf-8") as f:
                        sch_data = json.load(f)
                    for item in sch_data:
                        db.add(LiveScholarshipDB(
                            id=item.get("id"),
                            name=item.get("name"),
                            university=item.get("university"),
                            country=item.get("country"),
                            degree=item.get("degree"),
                            match_score=item.get("matchScore"),
                            match_label=item.get("matchLabel"),
                            status=item.get("status"),
                            status_class=item.get("statusClass"),
                            deadline=item.get("deadline"),
                            deadline_display=item.get("deadline_display"),
                            deadline_days=item.get("deadlineDays"),
                            coverage=item.get("coverage"),
                            requirements=item.get("requirements"),
                            link=item.get("link"),
                            is_active=item.get("is_active", True)
                        ))
                    logger.info(f"Auto-migrated {len(sch_data)} scholarships to Database.")
                except Exception as sche:
                    logger.warning(f"Scholarship auto-migration error: {sche}")

            # 4. Migrate Community Acceptance Stories
            if CommunityStoryDB is not None:
                existing_story_count = db.query(CommunityStoryDB).count()
                if existing_story_count == 0 and os.path.exists(COMMUNITY_STORIES_JSON):
                    try:
                        with open(COMMUNITY_STORIES_JSON, "r", encoding="utf-8") as f:
                            story_data = json.load(f)
                        for item in story_data:
                            db.add(CommunityStoryDB(
                                id=item.get("id"),
                                author_name=item.get("author_name", "باحث أكاديمي"),
                                author_email=item.get("author_email"),
                                author_country=item.get("author_country", "فلسطين"),
                                scholarship_id=item.get("scholarship_id", "daad"),
                                scholarship_name=item.get("scholarship_name", "منحة دراسية"),
                                university=item.get("university", ""),
                                degree=item.get("degree", "ماجستير"),
                                field_of_study=item.get("field_of_study", "تخصص أكاديمي"),
                                acceptance_year=item.get("acceptance_year", "2025/2026"),
                                title=item.get("title", ""),
                                story_text=item.get("story_text", ""),
                                key_advice=item.get("key_advice", []),
                                gpa=item.get("gpa", "85%+"),
                                is_verified=item.get("is_verified", True),
                                upvotes=item.get("upvotes", 0),
                                upvoted_by=item.get("upvoted_by", []),
                                created_at=item.get("created_at", datetime.now().isoformat()),
                                tags=item.get("tags", [])
                            ))
                        logger.info(f"Auto-migrated {len(story_data)} community acceptance stories to Database.")
                    except Exception as ste:
                        logger.warning(f"Community stories auto-migration error: {ste}")

        return True
    except Exception as e:
        logger.error(f"Error during database initialization/migration: {e}")
        return False


NOTIFICATION_HISTORY_JSON = os.path.join(DATA_DIR, "notification_history.json")


def is_notification_sent(recipient: str, notification_type: str, target_id: str) -> bool:
    """Checks whether a specific notification was already sent to avoid duplicate dispatches."""
    clean_rec = recipient.strip().lower()
    clean_type = notification_type.strip()
    clean_target = target_id.strip()

    if is_db_available() and NotificationHistoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    found = db.query(NotificationHistoryDB).filter(
                        NotificationHistoryDB.recipient == clean_rec,
                        NotificationHistoryDB.notification_type == clean_type,
                        NotificationHistoryDB.target_id == clean_target,
                        NotificationHistoryDB.status == "sent"
                    ).first()
                    if found:
                        return True
        except Exception as e:
            logger.debug(f"DB check notification history error: {e}")

    # Fallback to local JSON
    if os.path.exists(NOTIFICATION_HISTORY_JSON):
        try:
            with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                logs = json.load(f)
                return any(
                    l.get("recipient", "").lower() == clean_rec
                    and l.get("notification_type") == clean_type
                    and l.get("target_id") == clean_target
                    and l.get("status") == "sent"
                    for l in logs
                )
        except Exception:
            pass

    return False


def record_notification(
    recipient: str,
    notification_type: str,
    target_id: str,
    subject: str,
    status: str = "sent",
    details: Optional[Dict[str, Any]] = None
):
    """Persists a notification event to both Database and local JSON store."""
    clean_rec = recipient.strip().lower()
    clean_type = notification_type.strip()
    clean_target = target_id.strip()
    now_iso = datetime.now().isoformat()
    record_dict = {
        "recipient": clean_rec,
        "notification_type": clean_type,
        "target_id": clean_target,
        "subject": subject,
        "sent_at": now_iso,
        "status": status,
        "details": details or {}
    }

    if is_db_available() and NotificationHistoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.add(NotificationHistoryDB(
                        recipient=clean_rec,
                        notification_type=clean_type,
                        target_id=clean_target,
                        subject=subject,
                        sent_at=now_iso,
                        status=status,
                        details=details or {}
                    ))
        except Exception as e:
            logger.error(f"Error persisting notification to DB: {e}")

    # Always mirror to atomic JSON for persistence across local restarts
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logs = []
        if os.path.exists(NOTIFICATION_HISTORY_JSON):
            try:
                with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        logs.insert(0, record_dict)
        if len(logs) > 500:
            logs = logs[:500]
        temp_file = NOTIFICATION_HISTORY_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, NOTIFICATION_HISTORY_JSON)
    except Exception as je:
        logger.error(f"Error writing notification history JSON: {je}")


def get_notification_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns the most recent notification dispatches."""
    if is_db_available() and NotificationHistoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_items = db.query(NotificationHistoryDB).order_by(NotificationHistoryDB.id.desc()).limit(limit).all()
                    if db_items:
                        return [item.to_dict() for item in db_items]
        except Exception as e:
            logger.debug(f"DB load notification history error: {e}")

    if os.path.exists(NOTIFICATION_HISTORY_JSON):
        try:
            with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                logs = json.load(f)
                return logs[:limit]
        except Exception:
            pass

    return []


def create_in_app_notification(
    recipient: str,
    title: str,
    message: str,
    notif_type: str = "match",
    scholarship_id: Optional[str] = None,
    link: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new in-app notification with dual DB + JSON persistence."""
    clean_rec = recipient.strip().lower()
    now_iso = datetime.now().isoformat()
    record = {
        "id": int(datetime.now().timestamp() * 1000),
        "recipient": clean_rec,
        "title": title,
        "message": message,
        "type": notif_type,
        "scholarship_id": scholarship_id,
        "link": link or "",
        "is_read": False,
        "created_at": now_iso
    }

    if is_db_available() and InAppNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_obj = InAppNotificationDB(
                        recipient=clean_rec,
                        title=title,
                        message=message,
                        type=notif_type,
                        scholarship_id=scholarship_id,
                        link=link or "",
                        is_read=False,
                        created_at=now_iso
                    )
                    db.add(db_obj)
                    db.flush()
                    record["id"] = db_obj.id
        except Exception as e:
            logger.error(f"Error persisting in-app notification to DB: {e}")

    # Mirror to JSON file
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        items = []
        if os.path.exists(IN_APP_NOTIFICATIONS_JSON):
            try:
                with open(IN_APP_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception:
                items = []
        items.insert(0, record)
        if len(items) > 1000:
            items = items[:1000]
        temp_file = IN_APP_NOTIFICATIONS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, IN_APP_NOTIFICATIONS_JSON)
    except Exception as je:
        logger.error(f"Error writing in_app_notifications JSON: {je}")

    return record


def get_in_app_notifications(
    recipient: str,
    limit: int = 50,
    unread_only: bool = False
) -> List[Dict[str, Any]]:
    """Retrieves in-app notifications for a student, newest first."""
    clean_rec = recipient.strip().lower()
    if is_db_available() and InAppNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(InAppNotificationDB).filter(InAppNotificationDB.recipient == clean_rec)
                    if unread_only:
                        q = q.filter(InAppNotificationDB.is_read == False)
                    items = q.order_by(InAppNotificationDB.id.desc()).limit(limit).all()
                    if items:
                        return [item.to_dict() for item in items]
        except Exception as e:
            logger.debug(f"DB load in-app notifications error: {e}")

    if os.path.exists(IN_APP_NOTIFICATIONS_JSON):
        try:
            with open(IN_APP_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
                matched = [
                    it for it in items
                    if it.get("recipient", "").lower() == clean_rec
                    and (not unread_only or not it.get("is_read", False))
                ]
                return matched[:limit]
        except Exception:
            pass
    return []


def mark_notification_as_read(recipient: str, notification_id: Union[int, str]) -> bool:
    """Marks a single notification as read."""
    clean_rec = recipient.strip().lower()
    updated = False

    if is_db_available() and InAppNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    try:
                        n_id = int(notification_id)
                        db_notif = db.query(InAppNotificationDB).filter(
                            InAppNotificationDB.id == n_id,
                            InAppNotificationDB.recipient == clean_rec
                        ).first()
                        if db_notif:
                            db_notif.is_read = True
                            updated = True
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.error(f"DB mark notification read error: {e}")

    if os.path.exists(IN_APP_NOTIFICATIONS_JSON):
        try:
            with open(IN_APP_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            str_id = str(notification_id)
            for it in items:
                if it.get("recipient", "").lower() == clean_rec and str(it.get("id")) == str_id:
                    it["is_read"] = True
                    updated = True
                    break
            if updated:
                temp_file = IN_APP_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, IN_APP_NOTIFICATIONS_JSON)
        except Exception as je:
            logger.error(f"JSON mark notification read error: {je}")

    return updated


def mark_all_notifications_as_read(recipient: str) -> int:
    """Marks all notifications for a recipient as read and returns the count."""
    clean_rec = recipient.strip().lower()
    count = 0

    if is_db_available() and InAppNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_items = db.query(InAppNotificationDB).filter(
                        InAppNotificationDB.recipient == clean_rec,
                        InAppNotificationDB.is_read == False
                    ).all()
                    for item in db_items:
                        item.is_read = True
                        count += 1
        except Exception as e:
            logger.error(f"DB mark all notifications read error: {e}")

    if os.path.exists(IN_APP_NOTIFICATIONS_JSON):
        try:
            with open(IN_APP_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            json_count = 0
            for it in items:
                if it.get("recipient", "").lower() == clean_rec and not it.get("is_read", False):
                    it["is_read"] = True
                    json_count += 1
            if json_count > 0:
                count = max(count, json_count)
                temp_file = IN_APP_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, IN_APP_NOTIFICATIONS_JSON)
        except Exception as je:
            logger.error(f"JSON mark all notifications read error: {je}")

    return count


def get_unread_notification_count(recipient: str) -> int:
    """Returns the number of unread notifications for a student."""
    clean_rec = recipient.strip().lower()
    if is_db_available() and InAppNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    return db.query(InAppNotificationDB).filter(
                        InAppNotificationDB.recipient == clean_rec,
                        InAppNotificationDB.is_read == False
                    ).count()
        except Exception as e:
            logger.debug(f"DB count unread notifications error: {e}")

    if os.path.exists(IN_APP_NOTIFICATIONS_JSON):
        try:
            with open(IN_APP_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
                return sum(1 for it in items if it.get("recipient", "").lower() == clean_rec and not it.get("is_read", False))
        except Exception:
            pass
    return 0


def record_notification_event(
    recipient: str,
    notification_type: str,
    channel: str,
    target_id: str,
    status: str = "created",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Tracks notification lifecycle: created -> sent -> delivered -> opened -> clicked."""
    clean_rec = recipient.strip().lower()
    now_iso = datetime.now().isoformat()
    record = {
        "id": int(datetime.now().timestamp() * 1000),
        "recipient": clean_rec,
        "notification_type": notification_type,
        "channel": channel,
        "target_id": target_id,
        "status": status,
        "timestamp": now_iso,
        "meta": meta or {}
    }

    if is_db_available() and NotificationEventDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_obj = NotificationEventDB(
                        recipient=clean_rec,
                        notification_type=notification_type,
                        channel=channel,
                        target_id=target_id,
                        status=status,
                        timestamp=now_iso,
                        meta=meta or {}
                    )
                    db.add(db_obj)
                    db.flush()
                    record["id"] = db_obj.id
        except Exception as e:
            logger.error(f"Error persisting notification event to DB: {e}")

    # Mirror to JSON file
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        items = []
        if os.path.exists(NOTIFICATION_EVENTS_JSON):
            try:
                with open(NOTIFICATION_EVENTS_JSON, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception:
                items = []
        items.insert(0, record)
        if len(items) > 1000:
            items = items[:1000]
        temp_file = NOTIFICATION_EVENTS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, NOTIFICATION_EVENTS_JSON)
    except Exception as je:
        logger.error(f"Error writing notification_events JSON: {je}")

    return record


def get_notification_events(recipient: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves notification lifecycle events."""
    clean_rec = recipient.strip().lower() if recipient else None
    if is_db_available() and NotificationEventDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(NotificationEventDB)
                    if clean_rec:
                        q = q.filter(NotificationEventDB.recipient == clean_rec)
                    items = q.order_by(NotificationEventDB.id.desc()).limit(limit).all()
                    if items:
                        return [item.to_dict() for item in items]
        except Exception as e:
            logger.debug(f"DB load notification events error: {e}")

    if os.path.exists(NOTIFICATION_EVENTS_JSON):
        try:
            with open(NOTIFICATION_EVENTS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
                if clean_rec:
                    items = [it for it in items if it.get("recipient", "").lower() == clean_rec]
                return items[:limit]
        except Exception:
            pass
    return []


def get_user_preferences(email: str) -> Dict[str, Any]:
    """Retrieves user notification & matching preferences."""
    clean_rec = email.strip().lower()
    defaults = {
        "preferred_countries": ["Turkey", "Germany", "Canada", "Europe", "Any"],
        "funding_type": "Any",
        "email_notifications": True,
        "telegram_notifications": False,
        "telegram_chat_id": "",
        "degree": "Undergraduate (Bachelor's)",
        "majors": ["Software Engineering", "Artificial Intelligence"]
    }

    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    u = None
                    if UserDB is not None:
                        u = db.query(UserDB).filter(UserDB.email == clean_rec).first()
                    if not u and SubscriberDB is not None:
                        u = db.query(SubscriberDB).filter(SubscriberDB.email == clean_rec).first()
                    if u:
                        return {
                            "preferred_countries": getattr(u, "preferred_countries", None) or defaults["preferred_countries"],
                            "funding_type": getattr(u, "funding_type", None) or defaults["funding_type"],
                            "email_notifications": getattr(u, "email_notifications", True) if getattr(u, "email_notifications", None) is not None else True,
                            "telegram_notifications": getattr(u, "telegram_notifications", False) if getattr(u, "telegram_notifications", None) is not None else False,
                            "telegram_chat_id": getattr(u, "telegram_chat_id", None) or "",
                            "degree": getattr(u, "degree", None) or defaults["degree"],
                            "majors": getattr(u, "majors", None) or defaults["majors"]
                        }
        except Exception as e:
            logger.debug(f"DB get_user_preferences error: {e}")

    # Fallback to subscribers.json / users.json
    for path in [USERS_JSON, SUBSCRIBERS_JSON]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                matched = next((r for r in records if r.get("email", "").lower() == clean_rec), None)
                if matched:
                    return {
                        "preferred_countries": matched.get("preferred_countries") or matched.get("target_destinations") or defaults["preferred_countries"],
                        "funding_type": matched.get("funding_type") or defaults["funding_type"],
                        "email_notifications": matched.get("email_notifications", True),
                        "telegram_notifications": matched.get("telegram_notifications", False),
                        "telegram_chat_id": matched.get("telegram_chat_id", ""),
                        "degree": matched.get("degree") or defaults["degree"],
                        "majors": matched.get("majors") or defaults["majors"]
                    }
            except Exception:
                pass

    return defaults


def update_user_preferences(email: str, preferences: Dict[str, Any]) -> bool:
    """Updates user notification & matching preferences across DB and JSON stores."""
    clean_rec = email.strip().lower()
    if not clean_rec or "@" not in clean_rec:
        return False

    pref_countries = preferences.get("preferred_countries")
    funding_type = preferences.get("funding_type")
    email_notifs = preferences.get("email_notifications")
    tg_notifs = preferences.get("telegram_notifications")
    tg_chat_id = preferences.get("telegram_chat_id")
    degree = preferences.get("degree")
    majors = preferences.get("majors")

    # Update in Database
    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    for Model in [UserDB, SubscriberDB]:
                        if Model is not None:
                            obj = db.query(Model).filter(Model.email == clean_rec).first()
                            if obj:
                                if pref_countries is not None:
                                    obj.preferred_countries = pref_countries
                                if funding_type is not None:
                                    obj.funding_type = funding_type
                                if email_notifs is not None:
                                    obj.email_notifications = email_notifs
                                if tg_notifs is not None:
                                    obj.telegram_notifications = tg_notifs
                                if tg_chat_id is not None:
                                    obj.telegram_chat_id = tg_chat_id
                                if degree is not None:
                                    obj.degree = degree
                                if majors is not None:
                                    obj.majors = majors
        except Exception as e:
            logger.error(f"Error updating preferences in DB: {e}")

    # Mirror update to JSON files
    for path in [USERS_JSON, SUBSCRIBERS_JSON]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                updated = False
                for r in records:
                    if r.get("email", "").lower() == clean_rec:
                        if pref_countries is not None:
                            r["preferred_countries"] = pref_countries
                            r["target_destinations"] = pref_countries
                        if funding_type is not None:
                            r["funding_type"] = funding_type
                        if email_notifs is not None:
                            r["email_notifications"] = email_notifs
                        if tg_notifs is not None:
                            r["telegram_notifications"] = tg_notifs
                        if tg_chat_id is not None:
                            r["telegram_chat_id"] = tg_chat_id
                        if degree is not None:
                            r["degree"] = degree
                        if majors is not None:
                            r["majors"] = majors
                        updated = True
                if not updated and path == SUBSCRIBERS_JSON:
                    new_rec = {
                        "email": clean_rec,
                        "full_name": "Student",
                        "degree": degree or "Undergraduate (Bachelor's)",
                        "majors": majors or ["Software Engineering"],
                        "gpa": "85%",
                        "english_level": "Intermediate",
                        "target_destinations": pref_countries or ["Any"],
                        "preferred_countries": pref_countries or ["Any"],
                        "funding_type": funding_type or "Any",
                        "email_notifications": email_notifs if email_notifs is not None else True,
                        "telegram_notifications": tg_notifs if tg_notifs is not None else False,
                        "telegram_chat_id": tg_chat_id or "",
                        "country": "Palestine",
                        "saved_scholarships": [],
                        "created_at": datetime.now().isoformat(),
                        "status": "active"
                    }
                    records.append(new_rec)
                    updated = True

                if updated:
                    temp_file = path + ".tmp"
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(records, f, ensure_ascii=False, indent=2)
                    os.replace(temp_file, path)
            except Exception as je:
                logger.error(f"Error updating preferences in {path}: {je}")

    return True


# =====================================================================
# STUDENT IDENTITY, PUBLIC PROFILE & ACCOUNT MANAGEMENT
# =====================================================================

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves full user record by email from DB or JSON fallback."""
    clean_rec = (email or "").strip().lower()
    if not clean_rec:
        return None

    if is_db_available() and UserDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    u = db.query(UserDB).filter(UserDB.email == clean_rec).first()
                    if u:
                        return u.to_dict()
        except Exception as e:
            logger.debug(f"DB get_user_by_email error: {e}")

    if os.path.exists(USERS_JSON):
        try:
            with open(USERS_JSON, "r", encoding="utf-8") as f:
                users = json.load(f)
            u = next((x for x in users if x.get("email", "").lower() == clean_rec), None)
            if u:
                return dict(u)
        except Exception:
            pass
    return None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieves full user record by username handle."""
    clean_uname = (username or "").strip().lower()
    if not clean_uname:
        return None

    if is_db_available() and UserDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    u = db.query(UserDB).filter(UserDB.username == clean_uname).first()
                    if u:
                        return u.to_dict()
                    # Fallback check if username matches email prefix
                    u2 = db.query(UserDB).all()
                    for item in u2:
                        derived = (item.username or item.email.split("@")[0]).lower()
                        if derived == clean_uname:
                            return item.to_dict()
        except Exception as e:
            logger.debug(f"DB get_user_by_username error: {e}")

    if os.path.exists(USERS_JSON):
        try:
            with open(USERS_JSON, "r", encoding="utf-8") as f:
                users = json.load(f)
            for x in users:
                u_uname = (x.get("username") or x.get("email", "").split("@")[0]).lower()
                if u_uname == clean_uname:
                    return dict(x)
        except Exception:
            pass
    return None


def save_or_update_user(user_data: Dict[str, Any]) -> bool:
    """Persists or updates complete student profile record across DB and JSON stores."""
    clean_rec = (user_data.get("email") or "").strip().lower()
    if not clean_rec:
        return False

    now_iso = datetime.now().isoformat()
    user_data["updated_at"] = now_iso
    if "created_at" not in user_data or not user_data["created_at"]:
        user_data["created_at"] = now_iso

    # Ensure username
    if not user_data.get("username"):
        user_data["username"] = clean_rec.split("@")[0].lower()

    # 1. Update in SQL Database
    if is_db_available() and UserDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    u = db.query(UserDB).filter(UserDB.email == clean_rec).first()
                    if not u:
                        u = UserDB(
                            email=clean_rec,
                            username=user_data.get("username"),
                            full_name=user_data.get("full_name", "Student"),
                            role=user_data.get("role", "student"),
                            salt=user_data.get("salt", "00"),
                            password_hash=user_data.get("password_hash", ""),
                            created_at=user_data["created_at"]
                        )
                        db.add(u)

                    u.username = user_data.get("username", u.username)
                    u.full_name = user_data.get("full_name", u.full_name)
                    u.role = user_data.get("role", u.role)
                    if user_data.get("password_hash"):
                        u.password_hash = user_data["password_hash"]
                    if user_data.get("salt"):
                        u.salt = user_data["salt"]

                    u.avatar_url = user_data.get("avatar_url", u.avatar_url)
                    u.cover_url = user_data.get("cover_url", u.cover_url)
                    u.city = user_data.get("city", u.city)
                    u.university = user_data.get("university", u.university)
                    u.degree = user_data.get("degree", u.degree)
                    u.majors = user_data.get("majors", u.majors)
                    u.graduation_year = user_data.get("graduation_year", u.graduation_year)
                    u.bio = user_data.get("bio", u.bio)
                    u.gpa = user_data.get("gpa", u.gpa)
                    u.english_level = user_data.get("english_level", u.english_level)
                    u.country = user_data.get("country", u.country)
                    u.talents_experience = user_data.get("talents_experience", u.talents_experience)

                    u.languages = user_data.get("languages", u.languages)
                    u.skills = user_data.get("skills", u.skills)
                    u.interests = user_data.get("interests", u.interests)
                    u.target_countries = user_data.get("target_countries", u.target_countries)
                    u.scholarship_interests = user_data.get("scholarship_interests", u.scholarship_interests)
                    u.social_links = user_data.get("social_links", u.social_links)

                    u.saved_scholarships = user_data.get("saved_scholarships", u.saved_scholarships)
                    u.preferred_countries = user_data.get("preferred_countries", u.preferred_countries)
                    u.funding_type = user_data.get("funding_type", u.funding_type)
                    u.email_notifications = user_data.get("email_notifications", u.email_notifications)
                    u.telegram_notifications = user_data.get("telegram_notifications", u.telegram_notifications)
                    u.telegram_chat_id = user_data.get("telegram_chat_id", u.telegram_chat_id)

                    u.email_verified = user_data.get("email_verified", u.email_verified)
                    u.verification_code = user_data.get("verification_code", u.verification_code)
                    u.reset_token = user_data.get("reset_token", u.reset_token)
                    u.reset_token_expires = user_data.get("reset_token_expires", u.reset_token_expires)
                    u.privacy_settings = user_data.get("privacy_settings", u.privacy_settings)
                    u.updated_at = now_iso
        except Exception as e:
            logger.error(f"Error saving/updating user in DB: {e}")

    # 2. Mirror to users.json
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        users = []
        if os.path.exists(USERS_JSON):
            try:
                with open(USERS_JSON, "r", encoding="utf-8") as f:
                    users = json.load(f)
            except Exception:
                users = []

        found_idx = next((i for i, x in enumerate(users) if x.get("email", "").lower() == clean_rec), None)
        if found_idx is not None:
            users[found_idx].update(user_data)
        else:
            users.append(user_data)

        temp_file = USERS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, USERS_JSON)
        return True
    except Exception as je:
        logger.error(f"Error writing users.json: {je}")
        return False


def delete_user_by_email(email: str) -> bool:
    """Permanently deletes a student account and associated subscriber records."""
    clean_rec = (email or "").strip().lower()
    if not clean_rec:
        return False

    # 1. Delete from DB
    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    if UserDB is not None:
                        db.query(UserDB).filter(UserDB.email == clean_rec).delete()
                    if SubscriberDB is not None:
                        db.query(SubscriberDB).filter(SubscriberDB.email == clean_rec).delete()
        except Exception as e:
            logger.error(f"DB delete user error: {e}")

    # 2. Delete from JSON files
    for path in [USERS_JSON, SUBSCRIBERS_JSON]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                filtered = [x for x in items if x.get("email", "").lower() != clean_rec]
                temp_file = path + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(filtered, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, path)
            except Exception as je:
                logger.error(f"Error deleting user from {path}: {je}")

    return True


# =====================================================================
# COMMUNITY & ACCEPTANCE EXPERIENCES ENGINE
# =====================================================================

def save_community_story(story_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new student acceptance story or community experience."""
    import uuid
    story_id = story_data.get("id") or f"story_{uuid.uuid4().hex[:10]}"
    story_data["id"] = story_id
    if "created_at" not in story_data:
        story_data["created_at"] = datetime.now().isoformat()
    if "upvotes" not in story_data:
        story_data["upvotes"] = 0
    if "upvoted_by" not in story_data:
        story_data["upvoted_by"] = []
    if "is_verified" not in story_data:
        story_data["is_verified"] = True

    # Persist in DB
    if is_db_available() and CommunityStoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_obj = db.query(CommunityStoryDB).filter(CommunityStoryDB.id == story_id).first()
                    if db_obj:
                        db_obj.title = story_data.get("title", db_obj.title)
                        db_obj.story_text = story_data.get("story_text", db_obj.story_text)
                        db_obj.key_advice = story_data.get("key_advice", db_obj.key_advice)
                        db_obj.upvotes = story_data.get("upvotes", db_obj.upvotes)
                        db_obj.upvoted_by = story_data.get("upvoted_by", db_obj.upvoted_by)
                    else:
                        new_obj = CommunityStoryDB(
                            id=story_id,
                            author_name=story_data.get("author_name", "باحث أكاديمي"),
                            author_email=story_data.get("author_email"),
                            author_country=story_data.get("author_country", "فلسطين"),
                            scholarship_id=story_data.get("scholarship_id", "general"),
                            scholarship_name=story_data.get("scholarship_name", "منحة دراسية"),
                            university=story_data.get("university", ""),
                            degree=story_data.get("degree", "ماجستير"),
                            field_of_study=story_data.get("field_of_study", "تخصص أكاديمي"),
                            acceptance_year=story_data.get("acceptance_year", "2025/2026"),
                            title=story_data.get("title", "تجربة قبول موثقة"),
                            story_text=story_data.get("story_text", ""),
                            key_advice=story_data.get("key_advice", []),
                            gpa=story_data.get("gpa", "85%+"),
                            is_verified=story_data.get("is_verified", True),
                            upvotes=story_data.get("upvotes", 0),
                            upvoted_by=story_data.get("upvoted_by", []),
                            created_at=story_data["created_at"],
                            tags=story_data.get("tags", [])
                        )
                        db.add(new_obj)
        except Exception as e:
            logger.error(f"Error persisting community story to DB: {e}")

    # Mirror to JSON file
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        stories = []
        if os.path.exists(COMMUNITY_STORIES_JSON):
            try:
                with open(COMMUNITY_STORIES_JSON, "r", encoding="utf-8") as f:
                    stories = json.load(f)
            except Exception:
                stories = []

        existing_idx = next((i for i, s in enumerate(stories) if s.get("id") == story_id), None)
        if existing_idx is not None:
            stories[existing_idx].update(story_data)
        else:
            stories.insert(0, story_data)

        temp_file = COMMUNITY_STORIES_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_STORIES_JSON)
    except Exception as je:
        logger.error(f"Error persisting community story to JSON: {je}")

    return story_data


def get_community_stories(scholarship_id: Optional[str] = None, degree: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves verified community stories filtered by scholarship or degree."""
    clean_sch = scholarship_id.strip().lower() if scholarship_id else None
    clean_deg = degree.strip().lower() if degree else None

    # Load from DB
    if is_db_available() and CommunityStoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(CommunityStoryDB)
                    if clean_sch and clean_sch != "all":
                        q = q.filter(CommunityStoryDB.scholarship_id == clean_sch)
                    if clean_deg and clean_deg != "all":
                        q = q.filter(CommunityStoryDB.degree.ilike(f"%{clean_deg}%"))
                    items = q.order_by(CommunityStoryDB.upvotes.desc(), CommunityStoryDB.id.desc()).limit(limit).all()
                    if items:
                        return [it.to_dict() for it in items]
        except Exception as e:
            logger.debug(f"DB load community stories error: {e}")

    # Fallback to JSON
    if os.path.exists(COMMUNITY_STORIES_JSON):
        try:
            with open(COMMUNITY_STORIES_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            if clean_sch and clean_sch != "all":
                items = [it for it in items if it.get("scholarship_id", "").lower() == clean_sch]
            if clean_deg and clean_deg != "all":
                items = [it for it in items if clean_deg in it.get("degree", "").lower()]
            items.sort(key=lambda x: (x.get("upvotes", 0)), reverse=True)
            return items[:limit]
        except Exception as je:
            logger.error(f"Error loading community stories from JSON: {je}")

    return []


def get_community_story_by_id(story_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single community story by its ID."""
    clean_id = story_id.strip()
    if is_db_available() and CommunityStoryDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    item = db.query(CommunityStoryDB).filter(CommunityStoryDB.id == clean_id).first()
                    if item:
                        return item.to_dict()
        except Exception as e:
            logger.debug(f"DB load story error: {e}")

    if os.path.exists(COMMUNITY_STORIES_JSON):
        try:
            with open(COMMUNITY_STORIES_JSON, "r", encoding="utf-8") as f:
                stories = json.load(f)
            return next((s for s in stories if s.get("id") == clean_id), None)
        except Exception:
            pass
    return None


def upvote_community_story(story_id: str, user_email: str) -> Dict[str, Any]:
    """Records a helpful upvote for a community story by a verified student."""
    clean_id = story_id.strip()
    clean_mail = user_email.strip().lower()

    story = get_community_story_by_id(clean_id)
    if not story:
        return {"success": False, "detail": "القصة غير موجودة."}

    upvoted_by = list(story.get("upvoted_by", []))
    if clean_mail in upvoted_by:
        # Toggle off
        upvoted_by.remove(clean_mail)
        story["upvotes"] = max(0, int(story.get("upvotes", 1)) - 1)
        action = "removed"
    else:
        # Add upvote
        upvoted_by.append(clean_mail)
        story["upvotes"] = int(story.get("upvotes", 0)) + 1
        action = "added"

    story["upvoted_by"] = upvoted_by
    save_community_story(story)

    return {
        "success": True,
        "action": action,
        "upvotes": story["upvotes"],
        "story_id": clean_id
    }


# =====================================================================
# TELEGRAM SCHOLARSHIP CHANNEL AUTOMATION & DEDUPLICATION
# =====================================================================

def is_scholarship_published_to_telegram(scholarship_id: str) -> bool:
    """
    Checks whether a scholarship was already broadcasted to the official Telegram channel.
    Ensures strict deduplication across Postgres, SQLite, and JSON fallbacks.
    """
    if not scholarship_id:
        return False
    clean_id = str(scholarship_id).strip()
    target_key = f"tg_post_{clean_id}"

    # 1. Check SQL Database (if connected)
    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    if LiveScholarshipDB is not None:
                        row = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.id == clean_id).first()
                        if row and row.telegram_message_id and len(str(row.telegram_message_id).strip()) > 0:
                            return True
                    if NotificationHistoryDB is not None:
                        n_row = db.query(NotificationHistoryDB).filter(
                            NotificationHistoryDB.notification_type == "telegram_channel_post",
                            NotificationHistoryDB.target_id == target_key
                        ).first()
                        if n_row:
                            return True
        except Exception as e:
            logger.debug(f"DB check telegram published error: {e}")

    # 2. Check Notification History JSON Store
    if os.path.exists(NOTIFICATION_HISTORY_JSON):
        try:
            with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if any(l.get("notification_type") == "telegram_channel_post" and l.get("target_id") == target_key for l in logs):
                return True
        except Exception:
            pass

    # 3. Check live_scholarships.json file
    if os.path.exists(SCHOLARSHIPS_JSON):
        try:
            with open(SCHOLARSHIPS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data:
                if str(s.get("id")) == clean_id and s.get("telegram_message_id"):
                    return True
        except Exception:
            pass

    return False


def save_scholarship_telegram_post(scholarship_id: str, telegram_message_id: Any, channel_id: str = "telegram_channel") -> bool:
    """
    Persists the Telegram post message_id and publication timestamp for a scholarship
    to guarantee it is never published again.
    """
    if not scholarship_id:
        return False
    clean_id = str(scholarship_id).strip()
    msg_id_str = str(telegram_message_id).strip()
    now_iso = datetime.now().isoformat()

    # 1. Update in SQL Database
    if is_db_available() and LiveScholarshipDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.id == clean_id).first()
                    if row:
                        row.telegram_message_id = msg_id_str
                        row.telegram_published_at = now_iso
        except Exception as e:
            logger.warning(f"Error persisting telegram_message_id to LiveScholarshipDB: {e}")

    # 2. Update live_scholarships.json store
    if os.path.exists(SCHOLARSHIPS_JSON):
        try:
            with open(SCHOLARSHIPS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            updated = False
            for itm in items:
                if str(itm.get("id")) == clean_id:
                    itm["telegram_message_id"] = msg_id_str
                    itm["telegram_published_at"] = now_iso
                    updated = True
                    break
            if updated:
                temp_file = SCHOLARSHIPS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, SCHOLARSHIPS_JSON)
        except Exception as je:
            logger.warning(f"Error persisting telegram_message_id to live_scholarships.json: {je}")

    # 3. Log idempotency history and notification event
    target_key = f"tg_post_{clean_id}"
    record_notification(
        recipient=channel_id or "telegram_channel",
        notification_type="telegram_channel_post",
        target_id=target_key,
        subject=f"Telegram Post #{msg_id_str}",
        status="sent",
        details={"scholarship_id": clean_id, "telegram_message_id": msg_id_str, "published_at": now_iso}
    )
    record_notification_event(
        recipient=channel_id or "telegram_channel",
        notification_type="telegram_channel_post",
        channel="telegram",
        target_id=target_key,
        status="sent",
        meta={"scholarship_id": clean_id, "telegram_message_id": msg_id_str}
    )
    logger.info(f"Telegram publication recorded for scholarship {clean_id} with post ID {msg_id_str}")
    return True


def get_scholarship_telegram_post_id(scholarship_id: str) -> Optional[str]:
    """Retrieves the Telegram post message ID if already published."""
    if not scholarship_id:
        return None
    clean_id = str(scholarship_id).strip()
    target_key = f"tg_post_{clean_id}"

    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    if LiveScholarshipDB is not None:
                        row = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.id == clean_id).first()
                        if row and row.telegram_message_id:
                            return str(row.telegram_message_id)
                    if NotificationHistoryDB is not None:
                        n_row = db.query(NotificationHistoryDB).filter(
                            NotificationHistoryDB.notification_type == "telegram_channel_post",
                            NotificationHistoryDB.target_id == target_key
                        ).first()
                        if n_row and n_row.details:
                            return str(n_row.details.get("telegram_message_id", ""))
        except Exception:
            pass

    if os.path.exists(SCHOLARSHIPS_JSON):
        try:
            with open(SCHOLARSHIPS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data:
                if str(s.get("id")) == clean_id and s.get("telegram_message_id"):
                    return str(s.get("telegram_message_id"))
        except Exception:
            pass

    if os.path.exists(NOTIFICATION_HISTORY_JSON):
        try:
            with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                logs = json.load(f)
            for l in logs:
                if l.get("notification_type") == "telegram_channel_post" and l.get("target_id") == target_key:
                    details = l.get("details", {})
                    if details.get("telegram_message_id"):
                        return str(details.get("telegram_message_id"))
        except Exception:
            pass

    return None



# =====================================================================
# ACADEMIC COMMUNITY HUB DATA PERSISTENCE & INTERACTIONS
# =====================================================================

def save_community_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new or updated community post across Database and JSON stores."""
    import uuid
    post_id = post_data.get("id") or f"post_{uuid.uuid4().hex[:12]}"
    post_data["id"] = post_id
    now_iso = datetime.now().isoformat()
    if "created_at" not in post_data:
        post_data["created_at"] = now_iso
    post_data["updated_at"] = now_iso

    if "likes_count" not in post_data:
        post_data["likes_count"] = 0
    if "liked_by" not in post_data:
        post_data["liked_by"] = []
    if "saved_by" not in post_data:
        post_data["saved_by"] = []
    if "shares_count" not in post_data:
        post_data["shares_count"] = 0
    if "comments_count" not in post_data:
        post_data["comments_count"] = 0
    if "is_hidden" not in post_data:
        post_data["is_hidden"] = False
    if "is_pinned" not in post_data:
        post_data["is_pinned"] = False

    # 1. Persist in SQL DB if available
    if is_db_available() and CommunityPostDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_obj = db.query(CommunityPostDB).filter(CommunityPostDB.id == post_id).first()
                    if db_obj:
                        db_obj.title = post_data.get("title", db_obj.title)
                        db_obj.content = post_data.get("content", db_obj.content)
                        db_obj.category = post_data.get("category", db_obj.category)
                        db_obj.post_type = post_data.get("post_type", db_obj.post_type)
                        db_obj.media_urls = post_data.get("media_urls", db_obj.media_urls)
                        db_obj.video_url = post_data.get("video_url", db_obj.video_url)
                        db_obj.link_url = post_data.get("link_url", db_obj.link_url)
                        db_obj.link_meta = post_data.get("link_meta", db_obj.link_meta)
                        db_obj.scholarship_id = post_data.get("scholarship_id", db_obj.scholarship_id)
                        db_obj.scholarship_name = post_data.get("scholarship_name", db_obj.scholarship_name)
                        db_obj.country = post_data.get("country", db_obj.country)
                        db_obj.university = post_data.get("university", db_obj.university)
                        db_obj.major = post_data.get("major", db_obj.major)
                        db_obj.likes_count = post_data.get("likes_count", db_obj.likes_count)
                        db_obj.liked_by = post_data.get("liked_by", db_obj.liked_by)
                        db_obj.saved_by = post_data.get("saved_by", db_obj.saved_by)
                        db_obj.shares_count = post_data.get("shares_count", db_obj.shares_count)
                        db_obj.comments_count = post_data.get("comments_count", db_obj.comments_count)
                        db_obj.is_success_story = post_data.get("is_success_story", db_obj.is_success_story)
                        db_obj.success_details = post_data.get("success_details", db_obj.success_details)
                        db_obj.is_pinned = post_data.get("is_pinned", db_obj.is_pinned)
                        db_obj.is_hidden = post_data.get("is_hidden", db_obj.is_hidden)
                        db_obj.updated_at = now_iso
                    else:
                        new_obj = CommunityPostDB(
                            id=post_id,
                            author_id=post_data.get("author_id", ""),
                            author_name=post_data.get("author_name", ""),
                            author_username=post_data.get("author_username", ""),
                            author_avatar=post_data.get("author_avatar", ""),
                            author_university=post_data.get("author_university", ""),
                            author_degree=post_data.get("author_degree", ""),
                            category=post_data.get("category", "general_discussion"),
                            title=post_data.get("title", ""),
                            content=post_data.get("content", ""),
                            post_type=post_data.get("post_type", "text"),
                            media_urls=post_data.get("media_urls", []),
                            video_url=post_data.get("video_url", ""),
                            link_url=post_data.get("link_url", ""),
                            link_meta=post_data.get("link_meta", {}),
                            scholarship_id=post_data.get("scholarship_id"),
                            scholarship_name=post_data.get("scholarship_name"),
                            country=post_data.get("country", ""),
                            university=post_data.get("university", ""),
                            major=post_data.get("major", ""),
                            likes_count=post_data.get("likes_count", 0),
                            liked_by=post_data.get("liked_by", []),
                            saved_by=post_data.get("saved_by", []),
                            shares_count=post_data.get("shares_count", 0),
                            comments_count=post_data.get("comments_count", 0),
                            is_success_story=post_data.get("is_success_story", False),
                            success_details=post_data.get("success_details", {}),
                            is_pinned=post_data.get("is_pinned", False),
                            is_hidden=post_data.get("is_hidden", False),
                            created_at=post_data["created_at"],
                            updated_at=now_iso
                        )
                        db.add(new_obj)
        except Exception as e:
            logger.error(f"Error persisting community post to DB: {e}")

    # 2. Mirror to JSON file
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        posts = []
        if os.path.exists(COMMUNITY_POSTS_JSON):
            try:
                with open(COMMUNITY_POSTS_JSON, "r", encoding="utf-8") as f:
                    posts = json.load(f)
            except Exception:
                posts = []

        existing_idx = next((i for i, p in enumerate(posts) if p.get("id") == post_id), None)
        if existing_idx is not None:
            posts[existing_idx].update(post_data)
        else:
            posts.insert(0, post_data)

        temp_file = COMMUNITY_POSTS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_POSTS_JSON)
    except Exception as je:
        logger.error(f"Error persisting community post to JSON: {je}")

    return post_data


def get_community_posts(filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves public community posts matching optional category, scholarship, or author filters."""
    filters = filters or {}
    category = filters.get("category")
    author_username = filters.get("author_username")
    scholarship_id = filters.get("scholarship_id")
    only_success = filters.get("only_success", False)
    country = filters.get("country")
    search_q = filters.get("search")

    # DB Fetch
    if is_db_available() and CommunityPostDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(CommunityPostDB).filter(CommunityPostDB.is_hidden == False)
                    if category and category != "all":
                        q = q.filter(CommunityPostDB.category == category)
                    if author_username:
                        q = q.filter(CommunityPostDB.author_username == author_username)
                    if scholarship_id:
                        q = q.filter(CommunityPostDB.scholarship_id == scholarship_id)
                    if only_success:
                        q = q.filter(CommunityPostDB.is_success_story == True)
                    if country and country != "all":
                        q = q.filter(CommunityPostDB.country.ilike(f"%{country}%"))
                    if search_q:
                        sq = f"%{search_q}%"
                        q = q.filter(
                            (CommunityPostDB.title.ilike(sq)) |
                            (CommunityPostDB.content.ilike(sq)) |
                            (CommunityPostDB.author_name.ilike(sq)) |
                            (CommunityPostDB.university.ilike(sq))
                        )
                    items = q.order_by(CommunityPostDB.is_pinned.desc(), CommunityPostDB.created_at.desc()).limit(limit).all()
                    if items:
                        return [it.to_dict() for it in items]
        except Exception as e:
            logger.debug(f"DB load community posts error: {e}")

    # JSON Fallback
    if os.path.exists(COMMUNITY_POSTS_JSON):
        try:
            with open(COMMUNITY_POSTS_JSON, "r", encoding="utf-8") as f:
                posts = json.load(f)
            results = [p for p in posts if not p.get("is_hidden", False)]
            if category and category != "all":
                results = [p for p in results if p.get("category") == category]
            if author_username:
                results = [p for p in results if p.get("author_username") == author_username]
            if scholarship_id:
                results = [p for p in results if p.get("scholarship_id") == scholarship_id]
            if only_success:
                results = [p for p in results if p.get("is_success_story", False)]
            if country and country != "all":
                results = [p for p in results if country.lower() in p.get("country", "").lower()]
            if search_q:
                sq = search_q.lower()
                results = [
                    p for p in results if
                    sq in p.get("title", "").lower() or
                    sq in p.get("content", "").lower() or
                    sq in p.get("author_name", "").lower() or
                    sq in p.get("university", "").lower()
                ]
            results.sort(key=lambda x: (not x.get("is_pinned", False), x.get("created_at", "")), reverse=False)
            return results[:limit]
        except Exception as je:
            logger.error(f"Error loading community posts from JSON: {je}")

    return []


def get_community_post_by_id(post_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single community post by its ID."""
    clean_id = str(post_id).strip()
    if is_db_available() and CommunityPostDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    obj = db.query(CommunityPostDB).filter(CommunityPostDB.id == clean_id).first()
                    if obj:
                        return obj.to_dict()
        except Exception as e:
            logger.debug(f"DB load post by ID error: {e}")

    if os.path.exists(COMMUNITY_POSTS_JSON):
        try:
            with open(COMMUNITY_POSTS_JSON, "r", encoding="utf-8") as f:
                posts = json.load(f)
            return next((p for p in posts if p.get("id") == clean_id), None)
        except Exception:
            pass
    return None


def delete_community_post(post_id: str) -> bool:
    """Soft deletes or removes a community post and its related comments."""
    clean_id = str(post_id).strip()
    deleted = False

    if is_db_available() and CommunityPostDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.query(CommunityPostDB).filter(CommunityPostDB.id == clean_id).delete()
                    if CommunityCommentDB is not None:
                        db.query(CommunityCommentDB).filter(CommunityCommentDB.post_id == clean_id).delete()
                    deleted = True
        except Exception as e:
            logger.error(f"DB delete post error: {e}")

    if os.path.exists(COMMUNITY_POSTS_JSON):
        try:
            with open(COMMUNITY_POSTS_JSON, "r", encoding="utf-8") as f:
                posts = json.load(f)
            orig_len = len(posts)
            posts = [p for p in posts if p.get("id") != clean_id]
            if len(posts) < orig_len:
                temp_file = COMMUNITY_POSTS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(posts, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, COMMUNITY_POSTS_JSON)
                deleted = True
        except Exception as je:
            logger.error(f"JSON delete post error: {je}")

    # Remove comments
    if os.path.exists(COMMUNITY_COMMENTS_JSON):
        try:
            with open(COMMUNITY_COMMENTS_JSON, "r", encoding="utf-8") as f:
                comments = json.load(f)
            comments = [c for c in comments if c.get("post_id") != clean_id]
            temp_file = COMMUNITY_COMMENTS_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, COMMUNITY_COMMENTS_JSON)
        except Exception:
            pass

    return deleted


def save_community_comment(comment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new or updated comment / nested reply."""
    import uuid
    comment_id = comment_data.get("id") or f"comm_{uuid.uuid4().hex[:12]}"
    comment_data["id"] = comment_id
    now_iso = datetime.now().isoformat()
    if "created_at" not in comment_data:
        comment_data["created_at"] = now_iso
    comment_data["updated_at"] = now_iso

    if "likes_count" not in comment_data:
        comment_data["likes_count"] = 0
    if "liked_by" not in comment_data:
        comment_data["liked_by"] = []
    if "is_edited" not in comment_data:
        comment_data["is_edited"] = False
    if "is_hidden" not in comment_data:
        comment_data["is_hidden"] = False

    # Persist in DB
    if is_db_available() and CommunityCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db_obj = db.query(CommunityCommentDB).filter(CommunityCommentDB.id == comment_id).first()
                    if db_obj:
                        db_obj.content = comment_data.get("content", db_obj.content)
                        db_obj.likes_count = comment_data.get("likes_count", db_obj.likes_count)
                        db_obj.liked_by = comment_data.get("liked_by", db_obj.liked_by)
                        db_obj.is_edited = comment_data.get("is_edited", db_obj.is_edited)
                        db_obj.updated_at = now_iso
                    else:
                        new_obj = CommunityCommentDB(
                            id=comment_id,
                            post_id=comment_data.get("post_id", ""),
                            parent_id=comment_data.get("parent_id"),
                            author_id=comment_data.get("author_id", ""),
                            author_name=comment_data.get("author_name", ""),
                            author_username=comment_data.get("author_username", ""),
                            author_avatar=comment_data.get("author_avatar", ""),
                            author_university=comment_data.get("author_university", ""),
                            content=comment_data.get("content", ""),
                            likes_count=comment_data.get("likes_count", 0),
                            liked_by=comment_data.get("liked_by", []),
                            is_edited=comment_data.get("is_edited", False),
                            is_hidden=comment_data.get("is_hidden", False),
                            created_at=comment_data["created_at"],
                            updated_at=now_iso
                        )
                        db.add(new_obj)
        except Exception as e:
            logger.error(f"Error persisting comment to DB: {e}")

    # Mirror to JSON
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        comments = []
        if os.path.exists(COMMUNITY_COMMENTS_JSON):
            try:
                with open(COMMUNITY_COMMENTS_JSON, "r", encoding="utf-8") as f:
                    comments = json.load(f)
            except Exception:
                comments = []

        existing_idx = next((i for i, c in enumerate(comments) if c.get("id") == comment_id), None)
        if existing_idx is not None:
            comments[existing_idx].update(comment_data)
        else:
            comments.append(comment_data)

        temp_file = COMMUNITY_COMMENTS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_COMMENTS_JSON)
    except Exception as je:
        logger.error(f"Error persisting comment to JSON: {je}")

    # Update comment count on post
    post_id = comment_data.get("post_id")
    if post_id:
        post = get_community_post_by_id(post_id)
        if post:
            all_c = get_community_comments(post_id)
            post["comments_count"] = len(all_c)
            save_community_post(post)

    return comment_data


def get_community_comments(post_id: str) -> List[Dict[str, Any]]:
    """Retrieves all comments and nested replies for a given post."""
    clean_id = str(post_id).strip()
    if is_db_available() and CommunityCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    items = db.query(CommunityCommentDB).filter(
                        CommunityCommentDB.post_id == clean_id,
                        CommunityCommentDB.is_hidden == False
                    ).order_by(CommunityCommentDB.created_at.asc()).all()
                    if items:
                        return [it.to_dict() for it in items]
        except Exception as e:
            logger.debug(f"DB load comments error: {e}")

    if os.path.exists(COMMUNITY_COMMENTS_JSON):
        try:
            with open(COMMUNITY_COMMENTS_JSON, "r", encoding="utf-8") as f:
                comments = json.load(f)
            post_comments = [c for c in comments if c.get("post_id") == clean_id and not c.get("is_hidden", False)]
            post_comments.sort(key=lambda x: x.get("created_at", ""))
            return post_comments
        except Exception:
            pass

    return []


def get_community_comment_by_id(comment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single comment by ID."""
    clean_id = str(comment_id).strip()
    if is_db_available() and CommunityCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    obj = db.query(CommunityCommentDB).filter(CommunityCommentDB.id == clean_id).first()
                    if obj:
                        return obj.to_dict()
        except Exception:
            pass

    if os.path.exists(COMMUNITY_COMMENTS_JSON):
        try:
            with open(COMMUNITY_COMMENTS_JSON, "r", encoding="utf-8") as f:
                comments = json.load(f)
            return next((c for c in comments if c.get("id") == clean_id), None)
        except Exception:
            pass
    return None


def delete_community_comment(comment_id: str) -> bool:
    """Deletes a comment and updates post comment counter."""
    clean_id = str(comment_id).strip()
    comment = get_community_comment_by_id(clean_id)
    if not comment:
        return False
    post_id = comment.get("post_id")

    if is_db_available() and CommunityCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    # Delete comment and its direct replies
                    db.query(CommunityCommentDB).filter(
                        (CommunityCommentDB.id == clean_id) | (CommunityCommentDB.parent_id == clean_id)
                    ).delete()
        except Exception as e:
            logger.error(f"DB delete comment error: {e}")

    if os.path.exists(COMMUNITY_COMMENTS_JSON):
        try:
            with open(COMMUNITY_COMMENTS_JSON, "r", encoding="utf-8") as f:
                comments = json.load(f)
            comments = [c for c in comments if c.get("id") != clean_id and c.get("parent_id") != clean_id]
            temp_file = COMMUNITY_COMMENTS_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, COMMUNITY_COMMENTS_JSON)
        except Exception:
            pass

    if post_id:
        post = get_community_post_by_id(post_id)
        if post:
            all_c = get_community_comments(post_id)
            post["comments_count"] = len(all_c)
            save_community_post(post)

    return True


def toggle_follow_user(follower_email: str, following_email: str, following_username: str) -> Dict[str, Any]:
    """Toggles following relationship between two verified students."""
    f_email = follower_email.strip().lower()
    target_email = following_email.strip().lower()
    target_uname = following_username.strip().lower()

    if f_email == target_email:
        return {"success": False, "is_following": False, "error": "Cannot follow yourself"}

    import uuid
    is_following = False

    # Check DB
    if is_db_available() and CommunityFollowDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    existing = db.query(CommunityFollowDB).filter(
                        CommunityFollowDB.follower_email == f_email,
                        CommunityFollowDB.following_email == target_email
                    ).first()
                    if existing:
                        db.delete(existing)
                        is_following = False
                    else:
                        db.add(CommunityFollowDB(
                            id=f"fol_{uuid.uuid4().hex[:10]}",
                            follower_email=f_email,
                            following_email=target_email,
                            following_username=target_uname,
                            created_at=datetime.now().isoformat()
                        ))
                        is_following = True
        except Exception as e:
            logger.error(f"DB follow toggle error: {e}")

    # JSON Mirror
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        follows = []
        if os.path.exists(COMMUNITY_FOLLOWS_JSON):
            try:
                with open(COMMUNITY_FOLLOWS_JSON, "r", encoding="utf-8") as f:
                    follows = json.load(f)
            except Exception:
                follows = []

        existing_idx = next((i for i, fl in enumerate(follows) if fl.get("follower_email") == f_email and fl.get("following_email") == target_email), None)
        if existing_idx is not None:
            follows.pop(existing_idx)
            is_following = False
        else:
            follows.append({
                "id": f"fol_{uuid.uuid4().hex[:10]}",
                "follower_email": f_email,
                "following_email": target_email,
                "following_username": target_uname,
                "created_at": datetime.now().isoformat()
            })
            is_following = True

        temp_file = COMMUNITY_FOLLOWS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(follows, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_FOLLOWS_JSON)
    except Exception as je:
        logger.error(f"JSON follow toggle error: {je}")

    counts = get_user_follow_counts(target_uname)
    return {
        "success": True,
        "is_following": is_following,
        "followers_count": counts.get("followers", 0),
        "following_count": counts.get("following", 0)
    }


def get_follow_status(follower_email: str, following_email: str) -> bool:
    """Checks whether follower_email follows following_email."""
    f_email = follower_email.strip().lower()
    target_email = following_email.strip().lower()

    if is_db_available() and CommunityFollowDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(CommunityFollowDB).filter(
                        CommunityFollowDB.follower_email == f_email,
                        CommunityFollowDB.following_email == target_email
                    ).first()
                    if row:
                        return True
        except Exception:
            pass

    if os.path.exists(COMMUNITY_FOLLOWS_JSON):
        try:
            with open(COMMUNITY_FOLLOWS_JSON, "r", encoding="utf-8") as f:
                follows = json.load(f)
            return any(fl.get("follower_email") == f_email and fl.get("following_email") == target_email for fl in follows)
        except Exception:
            pass
    return False


def get_user_follow_counts(email_or_username: str) -> Dict[str, int]:
    """Calculates number of followers and following for a student."""
    key = email_or_username.strip().lower()
    followers = 0
    following = 0

    if is_db_available() and CommunityFollowDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    followers = db.query(CommunityFollowDB).filter(
                        (CommunityFollowDB.following_email == key) | (CommunityFollowDB.following_username == key)
                    ).count()
                    following = db.query(CommunityFollowDB).filter(
                        CommunityFollowDB.follower_email == key
                    ).count()
                    return {"followers": followers, "following": following}
        except Exception:
            pass

    if os.path.exists(COMMUNITY_FOLLOWS_JSON):
        try:
            with open(COMMUNITY_FOLLOWS_JSON, "r", encoding="utf-8") as f:
                follows = json.load(f)
            followers = sum(1 for fl in follows if fl.get("following_email") == key or fl.get("following_username") == key)
            following = sum(1 for fl in follows if fl.get("follower_email") == key)
        except Exception:
            pass

    return {"followers": followers, "following": following}


def save_community_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Logs a moderation report for a suspicious post or comment."""
    import uuid
    report_id = report_data.get("id") or f"rep_{uuid.uuid4().hex[:10]}"
    report_data["id"] = report_id
    if "created_at" not in report_data:
        report_data["created_at"] = datetime.now().isoformat()
    if "status" not in report_data:
        report_data["status"] = "pending"

    if is_db_available() and CommunityReportDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.add(CommunityReportDB(
                        id=report_id,
                        reporter_email=report_data.get("reporter_email", ""),
                        target_type=report_data.get("target_type", "post"),
                        target_id=report_data.get("target_id", ""),
                        reason=report_data.get("reason", "spam"),
                        details=report_data.get("details", ""),
                        status=report_data.get("status", "pending"),
                        created_at=report_data["created_at"]
                    ))
        except Exception as e:
            logger.error(f"DB save report error: {e}")

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        reports = []
        if os.path.exists(COMMUNITY_REPORTS_JSON):
            try:
                with open(COMMUNITY_REPORTS_JSON, "r", encoding="utf-8") as f:
                    reports = json.load(f)
            except Exception:
                reports = []
        reports.append(report_data)
        temp_file = COMMUNITY_REPORTS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_REPORTS_JSON)
    except Exception as je:
        logger.error(f"JSON save report error: {je}")

    return report_data


def save_community_notification(notif_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new in-app community notification for a student."""
    import uuid
    notif_id = notif_data.get("id") or f"notif_{uuid.uuid4().hex[:12]}"
    notif_data["id"] = notif_id
    if "created_at" not in notif_data:
        notif_data["created_at"] = datetime.now().isoformat()
    if "is_read" not in notif_data:
        notif_data["is_read"] = False

    if is_db_available() and CommunityNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.add(CommunityNotificationDB(
                        id=notif_id,
                        recipient_email=notif_data.get("recipient_email", ""),
                        actor_name=notif_data.get("actor_name", ""),
                        actor_username=notif_data.get("actor_username", ""),
                        actor_avatar=notif_data.get("actor_avatar", ""),
                        action_type=notif_data.get("action_type", "like"),
                        target_id=notif_data.get("target_id", ""),
                        message=notif_data.get("message", ""),
                        is_read=notif_data.get("is_read", False),
                        created_at=notif_data["created_at"]
                    ))
        except Exception as e:
            logger.error(f"DB save notification error: {e}")

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        notifs = []
        if os.path.exists(COMMUNITY_NOTIFICATIONS_JSON):
            try:
                with open(COMMUNITY_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                    notifs = json.load(f)
            except Exception:
                notifs = []
        notifs.insert(0, notif_data)
        temp_file = COMMUNITY_NOTIFICATIONS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(notifs[:200], f, ensure_ascii=False, indent=2)
        os.replace(temp_file, COMMUNITY_NOTIFICATIONS_JSON)
    except Exception as je:
        logger.error(f"JSON save notification error: {je}")

    return notif_data


def get_community_notifications(user_email: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves unread and recent community notifications for a student."""
    clean_rec = user_email.strip().lower()

    if is_db_available() and CommunityNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    rows = db.query(CommunityNotificationDB).filter(
                        CommunityNotificationDB.recipient_email == clean_rec
                    ).order_by(CommunityNotificationDB.created_at.desc()).limit(limit).all()
                    if rows:
                        return [r.to_dict() for r in rows]
        except Exception as e:
            logger.debug(f"DB load notifications error: {e}")

    if os.path.exists(COMMUNITY_NOTIFICATIONS_JSON):
        try:
            with open(COMMUNITY_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                notifs = json.load(f)
            user_notifs = [n for n in notifs if n.get("recipient_email", "").lower() == clean_rec]
            user_notifs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return user_notifs[:limit]
        except Exception:
            pass

    return []


def mark_community_notifications_read(user_email: str) -> bool:
    """Marks all community notifications as read for a student."""
    clean_rec = user_email.strip().lower()

    if is_db_available() and CommunityNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.query(CommunityNotificationDB).filter(
                        CommunityNotificationDB.recipient_email == clean_rec
                    ).update({"is_read": True})
        except Exception as e:
            logger.error(f"DB mark notifications read error: {e}")

    if os.path.exists(COMMUNITY_NOTIFICATIONS_JSON):
        try:
            with open(COMMUNITY_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                notifs = json.load(f)
            for n in notifs:
                if n.get("recipient_email", "").lower() == clean_rec:
                    n["is_read"] = True
            temp_file = COMMUNITY_NOTIFICATIONS_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(notifs, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, COMMUNITY_NOTIFICATIONS_JSON)
            return True
        except Exception:
            pass

    return True


# =====================================================================
# SCHOLARSHIP NEWS CENTER PERSISTENCE & DEADLINE PROTECTION
# =====================================================================

def enforce_news_deadlines() -> int:
    """
    Checks all news articles for deadline validity against today's date.
    Automatically marks expired scholarship news opportunities with is_expired = True.
    Ensures expired items are never presented as active opportunities.
    """
    today_str = datetime.now().date().isoformat()
    updated_count = 0

    # 1. Update in SQL DB if available
    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    articles = db.query(NewsArticleDB).all()
                    for art in articles:
                        if art.deadline:
                            clean_dl = str(art.deadline).strip()
                            if len(clean_dl) >= 10:
                                dl_date = clean_dl[:10]
                                should_expire = dl_date < today_str
                                if art.is_expired != should_expire:
                                    art.is_expired = should_expire
                                    updated_count += 1
        except Exception as e:
            logger.debug(f"DB enforce deadlines error: {e}")

    # 2. Update JSON fallback
    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            changed = False
            for art in articles:
                dl = art.get("deadline")
                if dl:
                    clean_dl = str(dl).strip()
                    if len(clean_dl) >= 10:
                        dl_date = clean_dl[:10]
                        should_expire = dl_date < today_str
                        if art.get("is_expired") != should_expire:
                            art["is_expired"] = should_expire
                            changed = True
                            updated_count += 1
            if changed:
                temp_file = NEWS_ARTICLES_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, NEWS_ARTICLES_JSON)
        except Exception as je:
            logger.debug(f"JSON enforce deadlines error: {je}")

    return updated_count


def get_news_articles(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "latest",
    only_active: bool = True,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Retrieves filtered, searched, and sorted news articles.
    If only_active=True, strictly excludes expired scholarship opportunities.
    """
    # Enforce real-time deadline checks
    enforce_news_deadlines()

    articles: List[Dict[str, Any]] = []

    # 1. Query from SQL DB if available
    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(NewsArticleDB)
                    if only_active:
                        q = q.filter(NewsArticleDB.is_expired == False)
                    if category and category.strip() and category != "all":
                        q = q.filter(NewsArticleDB.category == category.strip().lower())
                    if search and search.strip():
                        s = f"%{search.strip().lower()}%"
                        q = q.filter(
                            (NewsArticleDB.title.ilike(s)) |
                            (NewsArticleDB.summary.ilike(s)) |
                            (NewsArticleDB.content.ilike(s)) |
                            (NewsArticleDB.source_name.ilike(s)) |
                            (NewsArticleDB.country.ilike(s))
                        )
                    
                    if sort_by == "popular":
                        q = q.order_by((NewsArticleDB.views_count + NewsArticleDB.shares_count * 2 + NewsArticleDB.comments_count * 3).desc())
                    elif sort_by == "deadline":
                        q = q.order_by(NewsArticleDB.deadline.asc().nulls_last())
                    else: # latest
                        q = q.order_by(NewsArticleDB.publish_date.desc())
                    
                    total = q.count()
                    rows = q.offset((page - 1) * limit).limit(limit).all()
                    articles = [r.to_dict() for r in rows]
                    return {
                        "articles": articles,
                        "total": total,
                        "page": page,
                        "pages": (total + limit - 1) // limit if limit > 0 else 1,
                        "limit": limit
                    }
        except Exception as e:
            logger.debug(f"DB load news articles error: {e}")

    # 2. Query from JSON file
    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception:
            articles = []

    # Filter only_active
    if only_active:
        articles = [a for a in articles if not a.get("is_expired", False)]

    # Filter by category
    if category and category.strip() and category != "all":
        clean_cat = category.strip().lower()
        articles = [a for a in articles if a.get("category", "").lower() == clean_cat]

    # Filter by search
    if search and search.strip():
        q_clean = search.strip().lower()
        articles = [
            a for a in articles
            if q_clean in a.get("title", "").lower()
            or q_clean in a.get("summary", "").lower()
            or q_clean in a.get("content", "").lower()
            or q_clean in a.get("source_name", "").lower()
            or q_clean in a.get("country", "").lower()
        ]

    # Sort
    if sort_by == "popular":
        articles.sort(key=lambda x: (x.get("views_count", 0) + x.get("shares_count", 0) * 2 + x.get("comments_count", 0) * 3), reverse=True)
    elif sort_by == "deadline":
        articles.sort(key=lambda x: x.get("deadline") or "9999-99-99")
    else: # latest
        articles.sort(key=lambda x: x.get("publish_date", ""), reverse=True)

    total = len(articles)
    start_idx = (page - 1) * limit
    paged_articles = articles[start_idx:start_idx + limit]

    return {
        "articles": paged_articles,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
        "limit": limit
    }


def get_news_article_by_id(article_id: str, increment_views: bool = False) -> Optional[Dict[str, Any]]:
    """Retrieves a single news article by ID, optionally incrementing view count."""
    clean_id = article_id.strip()

    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    art = db.query(NewsArticleDB).filter(NewsArticleDB.id == clean_id).first()
                    if art:
                        if increment_views:
                            art.views_count = (art.views_count or 0) + 1
                        return art.to_dict()
        except Exception as e:
            logger.debug(f"DB get news article error: {e}")

    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            for a in articles:
                if a.get("id") == clean_id:
                    if increment_views:
                        a["views_count"] = a.get("views_count", 0) + 1
                        temp_file = NEWS_ARTICLES_JSON + ".tmp"
                        with open(temp_file, "w", encoding="utf-8") as wf:
                            json.dump(articles, wf, ensure_ascii=False, indent=2)
                        os.replace(temp_file, NEWS_ARTICLES_JSON)
                    return a
        except Exception:
            pass

    return None


def save_news_article(article_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts or updates a verified news article in the database and JSON store."""
    import uuid
    art_id = article_data.get("id") or f"news_{uuid.uuid4().hex[:12]}"
    article_data["id"] = art_id
    if "publish_date" not in article_data:
        article_data["publish_date"] = datetime.now().isoformat()
    if "created_at" not in article_data:
        article_data["created_at"] = datetime.now().isoformat()
    article_data["updated_at"] = datetime.now().isoformat()
    if "views_count" not in article_data:
        article_data["views_count"] = 0
    if "shares_count" not in article_data:
        article_data["shares_count"] = 0
    if "comments_count" not in article_data:
        article_data["comments_count"] = 0
    if "saved_by" not in article_data:
        article_data["saved_by"] = []

    # Deadline check
    dl = article_data.get("deadline")
    if dl and len(str(dl).strip()) >= 10:
        article_data["is_expired"] = str(dl).strip()[:10] < datetime.now().date().isoformat()
    elif "is_expired" not in article_data:
        article_data["is_expired"] = False

    # 1. DB Save
    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    existing = db.query(NewsArticleDB).filter(NewsArticleDB.id == art_id).first()
                    if existing:
                        for k, v in article_data.items():
                            if hasattr(existing, k):
                                setattr(existing, k, v)
                    else:
                        db.add(NewsArticleDB(
                            id=art_id,
                            title=article_data.get("title", ""),
                            summary=article_data.get("summary", ""),
                            content=article_data.get("content", ""),
                            category=article_data.get("category", "scholarships"),
                            category_label=article_data.get("category_label", "منح دراسية"),
                            publish_date=article_data.get("publish_date"),
                            source_name=article_data.get("source_name", "ScholarPilot Newsroom"),
                            source_url=article_data.get("source_url"),
                            image_url=article_data.get("image_url"),
                            country=article_data.get("country", ""),
                            degree_level=article_data.get("degree_level", ""),
                            scholarship_id=article_data.get("scholarship_id"),
                            deadline=article_data.get("deadline"),
                            is_expired=article_data.get("is_expired", False),
                            is_featured=article_data.get("is_featured", False),
                            is_trending=article_data.get("is_trending", False),
                            views_count=article_data.get("views_count", 0),
                            shares_count=article_data.get("shares_count", 0),
                            comments_count=article_data.get("comments_count", 0),
                            saved_by=article_data.get("saved_by", []),
                            telegram_message_id=article_data.get("telegram_message_id"),
                            telegram_published_at=article_data.get("telegram_published_at"),
                            created_at=article_data.get("created_at"),
                            updated_at=article_data.get("updated_at")
                        ))
        except Exception as e:
            logger.error(f"DB save news article error: {e}")

    # 2. JSON Save
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        articles = []
        if os.path.exists(NEWS_ARTICLES_JSON):
            try:
                with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                    articles = json.load(f)
            except Exception:
                articles = []

        idx = next((i for i, a in enumerate(articles) if a.get("id") == art_id), None)
        if idx is not None:
            articles[idx] = article_data
        else:
            articles.insert(0, article_data)

        temp_file = NEWS_ARTICLES_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, NEWS_ARTICLES_JSON)
    except Exception as je:
        logger.error(f"JSON save news article error: {je}")

    return article_data


def get_news_comments(article_id: str) -> List[Dict[str, Any]]:
    """Retrieves all comments and nested replies for an article."""
    clean_id = article_id.strip()
    comments: List[Dict[str, Any]] = []

    if is_db_available() and NewsCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    rows = db.query(NewsCommentDB).filter(
                        NewsCommentDB.article_id == clean_id
                    ).order_by(NewsCommentDB.created_at.asc()).all()
                    if rows:
                        comments = [r.to_dict() for r in rows]
        except Exception as e:
            logger.debug(f"DB load news comments error: {e}")

    if not comments and os.path.exists(NEWS_COMMENTS_JSON):
        try:
            with open(NEWS_COMMENTS_JSON, "r", encoding="utf-8") as f:
                all_comments = json.load(f)
            comments = [c for c in all_comments if c.get("article_id") == clean_id]
            comments.sort(key=lambda x: x.get("created_at", ""))
        except Exception:
            comments = []

    # Structure into top-level comments with replies list
    top_level = []
    comment_map = {}
    for c in comments:
        c["replies"] = []
        comment_map[c["id"]] = c

    for c in comments:
        parent_id = c.get("parent_id")
        if parent_id and parent_id in comment_map:
            comment_map[parent_id]["replies"].append(c)
        else:
            top_level.append(c)

    return top_level


def save_news_comment(comment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new comment or reply and increments comments_count on the article."""
    import uuid
    c_id = comment_data.get("id") or f"ncomm_{uuid.uuid4().hex[:12]}"
    comment_data["id"] = c_id
    if "created_at" not in comment_data:
        comment_data["created_at"] = datetime.now().isoformat()
    comment_data["updated_at"] = datetime.now().isoformat()
    if "likes_count" not in comment_data:
        comment_data["likes_count"] = 0
    if "liked_by" not in comment_data:
        comment_data["liked_by"] = []

    art_id = comment_data.get("article_id")

    # 1. DB Save
    if is_db_available() and NewsCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.add(NewsCommentDB(
                        id=c_id,
                        article_id=art_id,
                        parent_id=comment_data.get("parent_id"),
                        author_id=comment_data.get("author_id", ""),
                        author_name=comment_data.get("author_name", "Student"),
                        author_username=comment_data.get("author_username", "student"),
                        author_avatar=comment_data.get("author_avatar", ""),
                        author_university=comment_data.get("author_university", ""),
                        content=comment_data.get("content", ""),
                        likes_count=comment_data.get("likes_count", 0),
                        liked_by=comment_data.get("liked_by", []),
                        created_at=comment_data.get("created_at"),
                        updated_at=comment_data.get("updated_at")
                    ))
                    if NewsArticleDB is not None and art_id:
                        art = db.query(NewsArticleDB).filter(NewsArticleDB.id == art_id).first()
                        if art:
                            art.comments_count = (art.comments_count or 0) + 1
        except Exception as e:
            logger.error(f"DB save news comment error: {e}")

    # 2. JSON Save
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        comments = []
        if os.path.exists(NEWS_COMMENTS_JSON):
            try:
                with open(NEWS_COMMENTS_JSON, "r", encoding="utf-8") as f:
                    comments = json.load(f)
            except Exception:
                comments = []
        comments.append(comment_data)
        temp_file = NEWS_COMMENTS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, NEWS_COMMENTS_JSON)

        # Increment article comments count in JSON
        if art_id and os.path.exists(NEWS_ARTICLES_JSON):
            try:
                with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as af:
                    articles = json.load(af)
                for a in articles:
                    if a.get("id") == art_id:
                        a["comments_count"] = a.get("comments_count", 0) + 1
                temp_art = NEWS_ARTICLES_JSON + ".tmp"
                with open(temp_art, "w", encoding="utf-8") as af:
                    json.dump(articles, af, ensure_ascii=False, indent=2)
                os.replace(temp_art, NEWS_ARTICLES_JSON)
            except Exception:
                pass
    except Exception as je:
        logger.error(f"JSON save news comment error: {je}")

    return comment_data


def like_news_comment(comment_id: str, user_email: str) -> Dict[str, Any]:
    """Toggles like on a news comment."""
    clean_id = comment_id.strip()
    clean_email = user_email.strip().lower()
    is_liked = False
    likes_count = 0

    if is_db_available() and NewsCommentDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(NewsCommentDB).filter(NewsCommentDB.id == clean_id).first()
                    if row:
                        liked_by = list(row.liked_by or [])
                        if clean_email in liked_by:
                            liked_by.remove(clean_email)
                            is_liked = False
                        else:
                            liked_by.append(clean_email)
                            is_liked = True
                        row.liked_by = liked_by
                        row.likes_count = len(liked_by)
                        likes_count = row.likes_count
        except Exception as e:
            logger.error(f"DB like comment error: {e}")

    if os.path.exists(NEWS_COMMENTS_JSON):
        try:
            with open(NEWS_COMMENTS_JSON, "r", encoding="utf-8") as f:
                comments = json.load(f)
            for c in comments:
                if c.get("id") == clean_id:
                    liked_by = list(c.get("liked_by", []))
                    if clean_email in liked_by:
                        liked_by.remove(clean_email)
                        is_liked = False
                    else:
                        liked_by.append(clean_email)
                        is_liked = True
                    c["liked_by"] = liked_by
                    c["likes_count"] = len(liked_by)
                    likes_count = c["likes_count"]
            temp_file = NEWS_COMMENTS_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, NEWS_COMMENTS_JSON)
        except Exception:
            pass

    return {"success": True, "is_liked": is_liked, "likes_count": likes_count}


def toggle_save_news_article(article_id: str, user_email: str) -> Dict[str, Any]:
    """Toggles saving a news article to a student's reading list."""
    clean_id = article_id.strip()
    clean_email = user_email.strip().lower()
    is_saved = False

    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(NewsArticleDB).filter(NewsArticleDB.id == clean_id).first()
                    if row:
                        saved_by = list(row.saved_by or [])
                        if clean_email in saved_by:
                            saved_by.remove(clean_email)
                            is_saved = False
                        else:
                            saved_by.append(clean_email)
                            is_saved = True
                        row.saved_by = saved_by
        except Exception as e:
            logger.error(f"DB toggle save news article error: {e}")

    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            for a in articles:
                if a.get("id") == clean_id:
                    saved_by = list(a.get("saved_by", []))
                    if clean_email in saved_by:
                        saved_by.remove(clean_email)
                        is_saved = False
                    else:
                        saved_by.append(clean_email)
                        is_saved = True
                    a["saved_by"] = saved_by
            temp_file = NEWS_ARTICLES_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, NEWS_ARTICLES_JSON)
        except Exception:
            pass

    return {"success": True, "is_saved": is_saved}


def increment_news_shares(article_id: str) -> int:
    """Increments the share count for a news article."""
    clean_id = article_id.strip()
    shares_count = 0

    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(NewsArticleDB).filter(NewsArticleDB.id == clean_id).first()
                    if row:
                        row.shares_count = (row.shares_count or 0) + 1
                        shares_count = row.shares_count
        except Exception as e:
            logger.error(f"DB increment shares error: {e}")

    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            for a in articles:
                if a.get("id") == clean_id:
                    a["shares_count"] = a.get("shares_count", 0) + 1
                    shares_count = a["shares_count"]
            temp_file = NEWS_ARTICLES_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, NEWS_ARTICLES_JSON)
        except Exception:
            pass

    return shares_count


def is_news_published_to_telegram(article_id: str) -> bool:
    """Checks whether a news article was already published to the Telegram channel."""
    clean_id = str(article_id).strip()
    target_key = f"tg_news_{clean_id}"

    if is_db_available():
        try:
            with get_db_session() as db:
                if db is not None:
                    if NewsArticleDB is not None:
                        row = db.query(NewsArticleDB).filter(NewsArticleDB.id == clean_id).first()
                        if row and row.telegram_message_id and len(str(row.telegram_message_id).strip()) > 0:
                            return True
                    if NotificationHistoryDB is not None:
                        n_row = db.query(NotificationHistoryDB).filter(
                            NotificationHistoryDB.notification_type == "telegram_channel_post",
                            NotificationHistoryDB.target_id == target_key
                        ).first()
                        if n_row:
                            return True
        except Exception as e:
            logger.debug(f"DB check telegram news error: {e}")

    if os.path.exists(NOTIFICATION_HISTORY_JSON):
        try:
            with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if any(l.get("notification_type") == "telegram_channel_post" and l.get("target_id") == target_key for l in logs):
                return True
        except Exception:
            pass

    if os.path.exists(NEWS_ARTICLES_JSON):
        try:
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            for a in articles:
                if a.get("id") == clean_id and a.get("telegram_message_id"):
                    return True
        except Exception:
            pass

    return False


def save_news_telegram_post(article_id: str, telegram_message_id: Any, channel_id: str = "telegram_channel") -> bool:
    """Records the Telegram message ID for a published news article to prevent duplicates."""
    clean_id = str(article_id).strip()
    msg_id = str(telegram_message_id).strip()
    target_key = f"tg_news_{clean_id}"

    if is_db_available() and NewsArticleDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(NewsArticleDB).filter(NewsArticleDB.id == clean_id).first()
                    if row:
                        row.telegram_message_id = msg_id
                        row.telegram_published_at = datetime.now().isoformat()
                    if NotificationHistoryDB is not None:
                        db.add(NotificationHistoryDB(
                            recipient=channel_id,
                            notification_type="telegram_channel_post",
                            target_id=target_key,
                            subject=f"Telegram News Broadcast: {clean_id}",
                            sent_at=datetime.now().isoformat(),
                            status="sent",
                            details={"news_id": clean_id, "message_id": msg_id}
                        ))
        except Exception as e:
            logger.error(f"DB save telegram news post error: {e}")

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(NEWS_ARTICLES_JSON):
            with open(NEWS_ARTICLES_JSON, "r", encoding="utf-8") as f:
                articles = json.load(f)
            for a in articles:
                if a.get("id") == clean_id:
                    a["telegram_message_id"] = msg_id
                    a["telegram_published_at"] = datetime.now().isoformat()
            temp_file = NEWS_ARTICLES_JSON + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, NEWS_ARTICLES_JSON)

        # Log into notification history
        logs = []
        if os.path.exists(NOTIFICATION_HISTORY_JSON):
            try:
                with open(NOTIFICATION_HISTORY_JSON, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []
        logs.append({
            "recipient": channel_id,
            "notification_type": "telegram_channel_post",
            "target_id": target_key,
            "subject": f"Telegram News Broadcast: {clean_id}",
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
            "details": {"news_id": clean_id, "message_id": msg_id}
        })
        temp_notif = NOTIFICATION_HISTORY_JSON + ".tmp"
        with open(temp_notif, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        os.replace(temp_notif, NOTIFICATION_HISTORY_JSON)
        return True
    except Exception as je:
        logger.error(f"JSON save telegram news post error: {je}")
        return False


def get_news_category_counts() -> Dict[str, int]:
    """Returns the count of active news articles across all categories."""
    res = {
        "scholarships": 0,
        "universities": 0,
        "study_abroad": 0,
        "admissions": 0,
        "research": 0,
        "funding_opportunities": 0,
        "international_programs": 0,
        "internship_opportunities": 0
    }
    articles_data = get_news_articles(only_active=True, limit=500)
    for a in articles_data.get("articles", []):
        cat = a.get("category", "")
        if cat in res:
            res[cat] += 1
    return res


def get_all_scholarships():
    import os, json
    if os.path.exists(SCHOLARSHIPS_JSON):
        try:
            with open(SCHOLARSHIPS_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


# =====================================================================
# UNIFIED NOTIFICATION ENGINE (SCHOLARSHIPS, COMMUNITY, NEWS, SYSTEM)
# =====================================================================

DEFAULT_NOTIFICATION_PREFERENCES = {
    "scholarship_enabled": True,
    "community_enabled": True,
    "news_enabled": True,
    "system_enabled": True,
    "email_enabled": True,
    "browser_enabled": True,
    "subscribed_countries": [],
    "subscribed_majors": [],
    "subscribed_degrees": [],
    "email_frequency": "daily_digest"
}


def get_user_notification_preferences(email: str) -> Dict[str, Any]:
    """Retrieves notification settings & subscriptions for a student."""
    clean_email = (email or "").strip().lower()
    prefs = dict(DEFAULT_NOTIFICATION_PREFERENCES)

    if os.path.exists(NOTIFICATION_PREFERENCES_JSON):
        try:
            with open(NOTIFICATION_PREFERENCES_JSON, "r", encoding="utf-8") as f:
                all_prefs = json.load(f)
            if clean_email in all_prefs:
                prefs.update(all_prefs[clean_email])
        except Exception:
            pass

    return prefs


def update_user_notification_preferences(email: str, new_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Updates and persists notification preferences for a student."""
    clean_email = (email or "").strip().lower()
    current = get_user_notification_preferences(clean_email)
    current.update(new_prefs)

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        all_prefs = {}
        if os.path.exists(NOTIFICATION_PREFERENCES_JSON):
            try:
                with open(NOTIFICATION_PREFERENCES_JSON, "r", encoding="utf-8") as f:
                    all_prefs = json.load(f)
            except Exception:
                all_prefs = {}
        all_prefs[clean_email] = current
        temp_file = NOTIFICATION_PREFERENCES_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(all_prefs, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, NOTIFICATION_PREFERENCES_JSON)
    except Exception as e:
        logger.error(f"Error persisting notification preferences: {e}")

    return current


def create_unified_notification(notif_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates or intelligently groups a notification.
    If group_key is provided and an unread notification with that key exists,
    it updates the message and increments the counter instead of spamming.
    """
    import uuid
    clean_rec = (notif_data.get("recipient_email") or notif_data.get("recipient") or "").strip().lower()
    notif_data["recipient_email"] = clean_rec
    group_key = notif_data.get("group_key") or ""
    now_iso = datetime.now().isoformat()

    # 1. Check for intelligent grouping in JSON store
    updated_existing = False
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        items = []
        if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
            try:
                with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception:
                items = []

        if group_key:
            for it in items:
                if it.get("recipient_email") == clean_rec and it.get("group_key") == group_key and not it.get("is_read", False) and not it.get("is_archived", False):
                    # Intelligent grouping match!
                    it["count"] = it.get("count", 1) + 1
                    it["updated_at"] = now_iso
                    it["title"] = notif_data.get("title", it.get("title"))
                    it["message"] = notif_data.get("message", it.get("message"))
                    it["actor_name"] = notif_data.get("actor_name", it.get("actor_name"))
                    it["actor_avatar"] = notif_data.get("actor_avatar", it.get("actor_avatar"))
                    notif_data = it
                    updated_existing = True
                    break

        if not updated_existing:
            notif_id = notif_data.get("id") or f"ntf_{uuid.uuid4().hex[:12]}"
            notif_data["id"] = notif_id
            notif_data["is_read"] = bool(notif_data.get("is_read", False))
            notif_data["is_archived"] = bool(notif_data.get("is_archived", False))
            notif_data["priority"] = notif_data.get("priority", "normal")
            notif_data["count"] = notif_data.get("count", 1)
            notif_data["type"] = notif_data.get("action_type", notif_data.get("type", ""))
            notif_data["meta"] = notif_data.get("meta", {})
            notif_data["created_at"] = notif_data.get("created_at") or now_iso
            notif_data["updated_at"] = now_iso
            items.insert(0, notif_data)

        temp_file = UNIFIED_NOTIFICATIONS_JSON + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(items[:1500], f, ensure_ascii=False, indent=2)
        os.replace(temp_file, UNIFIED_NOTIFICATIONS_JSON)
    except Exception as je:
        logger.error(f"Error persisting unified notification to JSON: {je}")

    # Also record in DB if available
    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    db.add(UnifiedNotificationDB(
                        id=notif_data["id"],
                        recipient_email=clean_rec,
                        category=notif_data.get("category", "system"),
                        action_type=notif_data.get("action_type", "announcement"),
                        title=notif_data.get("title", ""),
                        message=notif_data.get("message", ""),
                        actor_name=notif_data.get("actor_name", ""),
                        actor_username=notif_data.get("actor_username", ""),
                        actor_avatar=notif_data.get("actor_avatar", ""),
                        target_type=notif_data.get("target_type", ""),
                        target_id=notif_data.get("target_id", ""),
                        link=notif_data.get("link", ""),
                        is_read=notif_data["is_read"],
                        is_archived=notif_data["is_archived"],
                        priority=notif_data["priority"],
                        group_key=group_key,
                        count=notif_data["count"],
                        meta=notif_data["meta"],
                        created_at=notif_data["created_at"],
                        updated_at=notif_data["updated_at"]
                    ))
        except Exception as dbe:
            logger.debug(f"DB save unified notification error: {dbe}")

    return notif_data


def get_unified_notifications(
    recipient_email: str,
    category: Optional[str] = None,
    unread_only: bool = False,
    archived_only: bool = False,
    limit: int = 50,
    page: int = 1
) -> Dict[str, Any]:
    """Retrieves paginated notifications filtered by category, read status, or archived status."""
    clean_rec = (recipient_email or "").strip().lower()
    items: List[Dict[str, Any]] = []

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(UnifiedNotificationDB).filter(UnifiedNotificationDB.recipient_email == clean_rec)
                    if archived_only:
                        q = q.filter(UnifiedNotificationDB.is_archived == True)
                    else:
                        q = q.filter(UnifiedNotificationDB.is_archived == False)
                        if unread_only:
                            q = q.filter(UnifiedNotificationDB.is_read == False)
                    if category and category.strip() and category != "all":
                        q = q.filter(UnifiedNotificationDB.category == category.strip().lower())
                    total = q.count()
                    rows = q.order_by(UnifiedNotificationDB.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
                    return {
                        "notifications": [r.to_dict() for r in rows],
                        "total": total,
                        "page": page,
                        "pages": (total + limit - 1) // limit if limit > 0 else 1
                    }
        except Exception as e:
            logger.debug(f"DB load unified notifications error: {e}")

    # Fallback to JSON file
    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

    filtered = [it for it in items if it.get("recipient_email", "").lower() == clean_rec]

    if archived_only:
        filtered = [it for it in filtered if it.get("is_archived", False)]
    else:
        filtered = [it for it in filtered if not it.get("is_archived", False)]
        if unread_only:
            filtered = [it for it in filtered if not it.get("is_read", False)]

    if category and category.strip() and category != "all":
        clean_cat = category.strip().lower()
        filtered = [it for it in filtered if it.get("category", "").lower() == clean_cat]

    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(filtered)
    start_idx = (page - 1) * limit
    paged = filtered[start_idx:start_idx + limit]

    return {
        "notifications": paged,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 1
    }


def mark_unified_notification_read(notification_id: str, recipient_email: str) -> bool:
    """Marks a single notification as read."""
    clean_id = str(notification_id).strip()
    clean_rec = (recipient_email or "").strip().lower()
    updated = False

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(UnifiedNotificationDB).filter(
                        UnifiedNotificationDB.id == clean_id,
                        UnifiedNotificationDB.recipient_email == clean_rec
                    ).first()
                    if row:
                        row.is_read = True
                        row.updated_at = datetime.now().isoformat()
                        updated = True
        except Exception as e:
            logger.debug(f"DB mark notification read error: {e}")

    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                if str(it.get("id")) == clean_id and it.get("recipient_email", "").lower() == clean_rec:
                    it["is_read"] = True
                    it["updated_at"] = datetime.now().isoformat()
                    updated = True
                    break
            if updated:
                temp_file = UNIFIED_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, UNIFIED_NOTIFICATIONS_JSON)
        except Exception:
            pass

    return updated


def mark_all_unified_notifications_read(recipient_email: str, category: Optional[str] = None) -> int:
    """Marks all notifications as read for a student, optionally filtered by category."""
    clean_rec = (recipient_email or "").strip().lower()
    count = 0

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    q = db.query(UnifiedNotificationDB).filter(
                        UnifiedNotificationDB.recipient_email == clean_rec,
                        UnifiedNotificationDB.is_read == False
                    )
                    if category and category.strip() and category != "all":
                        q = q.filter(UnifiedNotificationDB.category == category.strip().lower())
                    rows = q.all()
                    for r in rows:
                        r.is_read = True
                        r.updated_at = datetime.now().isoformat()
                        count += 1
        except Exception as e:
            logger.debug(f"DB mark all read error: {e}")

    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                if it.get("recipient_email", "").lower() == clean_rec and not it.get("is_read", False):
                    if not category or category == "all" or it.get("category", "").lower() == category.strip().lower():
                        it["is_read"] = True
                        it["updated_at"] = datetime.now().isoformat()
                        count += 1
            if count > 0:
                temp_file = UNIFIED_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, UNIFIED_NOTIFICATIONS_JSON)
        except Exception:
            pass

    return count


def archive_unified_notification(notification_id: str, recipient_email: str) -> bool:
    """Archives a notification so it is removed from active views."""
    clean_id = str(notification_id).strip()
    clean_rec = (recipient_email or "").strip().lower()
    updated = False

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(UnifiedNotificationDB).filter(
                        UnifiedNotificationDB.id == clean_id,
                        UnifiedNotificationDB.recipient_email == clean_rec
                    ).first()
                    if row:
                        row.is_archived = True
                        row.updated_at = datetime.now().isoformat()
                        updated = True
        except Exception as e:
            logger.debug(f"DB archive notification error: {e}")

    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                if str(it.get("id")) == clean_id and it.get("recipient_email", "").lower() == clean_rec:
                    it["is_archived"] = True
                    it["updated_at"] = datetime.now().isoformat()
                    updated = True
                    break
            if updated:
                temp_file = UNIFIED_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, UNIFIED_NOTIFICATIONS_JSON)
        except Exception:
            pass

    return updated


def delete_unified_notification(notification_id: str, recipient_email: str) -> bool:
    """Permanently deletes a notification."""
    clean_id = str(notification_id).strip()
    clean_rec = (recipient_email or "").strip().lower()
    deleted = False

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    row = db.query(UnifiedNotificationDB).filter(
                        UnifiedNotificationDB.id == clean_id,
                        UnifiedNotificationDB.recipient_email == clean_rec
                    ).first()
                    if row:
                        db.delete(row)
                        deleted = True
        except Exception as e:
            logger.debug(f"DB delete notification error: {e}")

    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            orig_len = len(items)
            items = [it for it in items if not (str(it.get("id")) == clean_id and it.get("recipient_email", "").lower() == clean_rec)]
            if len(items) < orig_len:
                deleted = True
                temp_file = UNIFIED_NOTIFICATIONS_JSON + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, UNIFIED_NOTIFICATIONS_JSON)
        except Exception:
            pass

    return deleted


def get_unified_unread_counts(recipient_email: str) -> Dict[str, int]:
    """Returns total unread count and category breakdown for a student."""
    clean_rec = (recipient_email or "").strip().lower()
    res = {
        "total": 0,
        "scholarship": 0,
        "community": 0,
        "news": 0,
        "system": 0,
        "group": 0,
        "chat": 0
    }

    if is_db_available() and UnifiedNotificationDB is not None:
        try:
            with get_db_session() as db:
                if db is not None:
                    rows = db.query(UnifiedNotificationDB).filter(
                        UnifiedNotificationDB.recipient_email == clean_rec,
                        UnifiedNotificationDB.is_read == False,
                        UnifiedNotificationDB.is_archived == False
                    ).all()
                    for r in rows:
                        res["total"] += 1
                        cat = (r.category or "").lower()
                        if cat in res:
                            res[cat] += 1
                    return res
        except Exception as e:
            logger.debug(f"DB unread counts error: {e}")

    if os.path.exists(UNIFIED_NOTIFICATIONS_JSON):
        try:
            with open(UNIFIED_NOTIFICATIONS_JSON, "r", encoding="utf-8") as f:
                items = json.load(f)
            for it in items:
                if it.get("recipient_email", "").lower() == clean_rec and not it.get("is_read", False) and not it.get("is_archived", False):
                    res["total"] += 1
                    cat = (it.get("category") or "").lower()
                    if cat in res:
                        res[cat] += 1
        except Exception:
            pass

    return res


def get_all_users():
    import os, json
    if os.path.exists(USERS_JSON):
        try:
            with open(USERS_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []
