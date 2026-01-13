#!/usr/bin/env python

from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, Index, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    Base = DeclarativeBase
else:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class GroupInfo(Base):
    __tablename__ = "group_info"
    group_name: Mapped[str] = mapped_column(String(256), primary_key=True)
    feed_name: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))


class FeedInfo(Base):
    __tablename__ = "feed_info"

    feed_name: Mapped[str] = mapped_column(String(256), default="", primary_key=True)
    feed_title: Mapped[str] = mapped_column(String(256), default="")
    group_name: Mapped[str] = mapped_column(String(256), default="", primary_key=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[str] = mapped_column(Text, default="")
    config_modify_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    url_list_count: Mapped[int] = mapped_column(Integer, default=0)

    collect_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    total_item_count: Mapped[int] = mapped_column(Integer, default=0)
    unit_size_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    progress_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    feedmaker: Mapped[bool] = mapped_column(Boolean, default=False)
    rss_update_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    public_html: Mapped[bool] = mapped_column(Boolean, default=False)
    public_feed_file_path: Mapped[str] = mapped_column(String(512), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    num_items: Mapped[int] = mapped_column(Integer, default=0)
    upload_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    http_request: Mapped[bool] = mapped_column(Boolean, default=False)
    access_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    view_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("feed_info_access_date_idx", "access_date"),
        Index("feed_info_view_date_idx", "view_date"),
    )


class HtmlFileInfo(Base):
    __tablename__ = "html_file_info"

    file_path: Mapped[str] = mapped_column(String(512), default="", primary_key=True)
    file_name: Mapped[str] = mapped_column(String(256), default="")
    feed_dir_path: Mapped[str] = mapped_column(String(512), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    count_with_many_image_tag: Mapped[int] = mapped_column(Integer, default=0)
    count_without_image_tag: Mapped[int] = mapped_column(Integer, default=0)
    count_with_image_not_found: Mapped[int] = mapped_column(Integer, default=0)
    update_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("html_file_info_feed_dir_path_idx", "feed_dir_path"),
    )


class ElementNameCount(Base):
    __tablename__ = "element_name_count"
    element_name: Mapped[str] = mapped_column(String(256), default="", primary_key=True)
    count: Mapped[int] = mapped_column(Integer)


class LockForConcurrentLoading(Base):
    __tablename__ = "lock_for_concurrent_loading"
    lock_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, server_default=text('CURRENT_TIMESTAMP'))


class SampleTable(Base):
    __tablename__ = "test_table"
    name: Mapped[str] = mapped_column(String(256), primary_key=True)
    age: Mapped[int] = mapped_column(Integer, default=0)


class UserSession(Base):
    __tablename__ = "user_session"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_email: Mapped[str] = mapped_column(String(256), nullable=False)
    user_name: Mapped[str] = mapped_column(String(256), nullable=False)
    facebook_access_token: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'))

    __table_args__ = (
        Index("user_session_expires_at_idx", "expires_at"),
        Index("user_session_user_email_idx", "user_email"),
    )
