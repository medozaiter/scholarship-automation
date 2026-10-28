"""
Database Service for ScholarPilot AI.
Supports Neon PostgreSQL in production, with fallback to SQLite or JSON data stores.
Provides automatic table creation and automatic data migration from JSON files on first boot.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
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

# Try importing SQLAlchemy
HAS_SQLALCHEMY = False
Base = None
engine = None
SessionLocal = None

try:
    from sqlalchemy import (
        create_engine, Column, Integer, String, Text, Boolean, JSON, inspect
    )
    from sqlalchemy.orm import declarative_base, sessionmaker

    HAS_SQLALCHEMY = True
    Base = declarative_base()

    # Define PostgreSQL / SQLite models
    class UserDB(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, autoincrement=True)
        email = Column(String(120), unique=True, index=True, nullable=False)
        full_name = Column(String(120), default="Student")
        role = Column(String(50), default="student")
        salt = Column(String(64), nullable=False)
        password_hash = Column(String(256), nullable=False)
        degree = Column(String(100), default="Undergraduate (Bachelor's)")
        majors = Column(JSON, default=list)
        gpa = Column(String(50), default="85%")
        english_level = Column(String(100), default="Intermediate")
        country = Column(String(100), default="Palestine")
        talents_experience = Column(Text, default="")
        saved_scholarships = Column(JSON, default=list)
        created_at = Column(String(50), default=lambda: datetime.now().isoformat())

        def to_dict(self) -> Dict[str, Any]:
            return {
                "email": self.email,
                "full_name": self.full_name,
                "role": self.role,
                "salt": self.salt,
                "password_hash": self.password_hash,
                "degree": self.degree,
                "majors": self.majors or [],
                "gpa": self.gpa,
                "english_level": self.english_level,
                "country": self.country,
                "talents_experience": self.talents_experience or "",
                "saved_scholarships": self.saved_scholarships or [],
                "created_at": self.created_at
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
                "is_active": self.is_active
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

    engine = create_engine(
        active_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300
    )
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

        return True
    except Exception as e:
        logger.error(f"Error during database initialization/migration: {e}")
        return False
