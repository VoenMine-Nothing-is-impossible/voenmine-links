"""initial: users, links, tags, clicks, payments, webhooks"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), default="default"),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_api_keys_user", "api_keys", ["user_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime),
        sa.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),
    )

    op.create_table(
        "links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("fallback_url", sa.Text, nullable=True),
        sa.Column("is_custom", sa.Boolean, default=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("max_clicks", sa.Integer, nullable=True),
        sa.Column("clicks_count", sa.Integer, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("show_preview", sa.Boolean, default=False),
        sa.Column("og_title", sa.String(255), nullable=True),
        sa.Column("og_description", sa.String(512), nullable=True),
        sa.Column("og_image", sa.Text, nullable=True),
        sa.Column("trackers", sa.Text, nullable=True, default="{}"),
        sa.Column("webhook_url", sa.Text, nullable=True),
        sa.Column("price_amount", sa.Float, nullable=True),
        sa.Column("price_currency", sa.String(8), default="RUB"),
        sa.Column("health_ok", sa.Boolean, default=True),
        sa.Column("last_health_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_links_code", "links", ["code"], unique=True)
    op.create_index("ix_links_owner", "links", ["owner_id"])
    op.create_index("ix_links_active", "links", ["is_active"])
    op.create_index("ix_links_expires", "links", ["expires_at"])

    op.create_table(
        "link_tags",
        sa.Column("link_id", sa.Integer, sa.ForeignKey("links.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "clicks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("country", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("browser", sa.String(64), nullable=True),
        sa.Column("os", sa.String(64), nullable=True),
        sa.Column("device", sa.String(32), nullable=True),
        sa.Column("referrer", sa.Text, nullable=True),
    )
    op.create_index("ix_clicks_link", "clicks", ["link_id"])
    op.create_index("ix_clicks_ts", "clicks", ["ts"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(8), default="RUB"),
        sa.Column("yookassa_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("payer_ip", sa.String(64), nullable=True),
        sa.Column("confirmation_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_payments_link", "payments", ["link_id"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("link_id", sa.Integer, sa.ForeignKey("links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("click_id", sa.Integer, sa.ForeignKey("clicks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_url", sa.Text, nullable=False),
        sa.Column("payload", sa.Text, nullable=False, default="{}"),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("attempts", sa.Integer, default=0),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade():
    for t in ["webhook_deliveries", "payments", "clicks", "link_tags", "links", "tags", "api_keys", "users"]:
        op.drop_table(t)
