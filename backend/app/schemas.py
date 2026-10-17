import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class Trackers(BaseModel):
    ga: Optional[str] = None
    fb: Optional[str] = None
    ym: Optional[str] = None
    gtm: Optional[str] = None


class LinkCreate(BaseModel):
    target_url: str
    slug: Optional[str] = Field(default=None, max_length=64)
    fallback_url: Optional[str] = None
    password: Optional[str] = Field(default=None, max_length=128)
    expires_at: Optional[dt.datetime] = None
    max_clicks: Optional[int] = Field(default=None, ge=1)
    show_preview: bool = False
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    tags: list[str] = []
    trackers: Trackers = Trackers()
    webhook_url: Optional[str] = None
    price_amount: Optional[float] = Field(default=None, ge=0)


class LinkUpdate(BaseModel):
    target_url: Optional[str] = None
    fallback_url: Optional[str] = None
    password: Optional[str] = None  # "" = снять пароль
    expires_at: Optional[dt.datetime] = None
    max_clicks: Optional[int] = Field(default=None, ge=1)
    show_preview: Optional[bool] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    tags: Optional[list[str]] = None
    trackers: Optional[Trackers] = None
    webhook_url: Optional[str] = None
    price_amount: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class LinkOut(BaseModel):
    id: int
    code: str
    short_url: str
    target_url: str
    fallback_url: Optional[str] = None
    expires_at: Optional[dt.datetime] = None
    max_clicks: Optional[int] = None
    clicks_count: int = 0
    is_active: bool = True
    has_password: bool = False
    is_paid: bool = False
    price_amount: Optional[float] = None
    show_preview: bool = False
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    tags: list[str] = []
    webhook_url: Optional[str] = None
    created_at: Optional[dt.datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: Optional[dt.datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = "default"
