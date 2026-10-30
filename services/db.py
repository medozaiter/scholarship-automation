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

