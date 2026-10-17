"""SQLAlchemy модели сократителя ссылок."""
import datetime as dt

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Table, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


link_tags = Table(
    "link_tags",
    Base.metadata,
    Column("link_id", Integer, ForeignKey("links.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    links = relationship("Link", back_populates="owner", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), default="default")
    key_prefix = Column(String(16), nullable=False)
    key_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="tags")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    target_url = Column(Text, nullable=False)
    fallback_url = Column(Text, nullable=True)
    is_custom = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    max_clicks = Column(Integer, nullable=True)
    clicks_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    show_preview = Column(Boolean, default=False)
    og_title = Column(String(255), nullable=True)
    og_description = Column(String(512), nullable=True)
    og_image = Column(Text, nullable=True)
    trackers = Column(Text, nullable=True, default="{}")  # JSON: {"ga": "...", "fb": "...", "ym": "..."}
    webhook_url = Column(Text, nullable=True)
    price_amount = Column(Float, nullable=True)  # рубли; None = бесплатно
    price_currency = Column(String(8), default="RUB")
    health_ok = Column(Boolean, default=True)
    last_health_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="links")
    tags_rel = relationship("Tag", secondary=link_tags, lazy="joined")
    clicks = relationship("Click", back_populates="link", cascade="all, delete-orphan")


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    ts = Column(DateTime, default=utcnow, index=True)
    ip = Column(String(64), nullable=True)
    country = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    browser = Column(String(64), nullable=True)
    os = Column(String(64), nullable=True)
    device = Column(String(32), nullable=True)
    referrer = Column(Text, nullable=True)

    link = relationship("Link", back_populates="clicks")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="RUB")
    yookassa_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), default="pending", index=True)  # pending/succeeded/canceled
    payer_ip = Column(String(64), nullable=True)
    confirmation_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True)
    click_id = Column(Integer, ForeignKey("clicks.id", ondelete="SET NULL"), nullable=True)
    target_url = Column(Text, nullable=False)
    payload = Column(Text, nullable=False, default="{}")
    status = Column(String(32), default="pending")  # pending/ok/failed
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
