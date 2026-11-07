"""Initial catalog, provenance, models and jobs; PostGIS footprint on PostgreSQL."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "regions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("bounds", sa.JSON(), nullable=False),
    )
    op.create_table(
        "dataset_provenance",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_table(
        "scenes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("region_id", sa.String(), sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("dataset_provenance.id"), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scene_id", sa.String(), sa.ForeignKey("scenes.id"), nullable=False),
        sa.Column("model_id", sa.String(), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
    )
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_table(
        "analysis_results",
        sa.Column("analysis_id", sa.String(), sa.ForeignKey("analysis_jobs.id"), primary_key=True),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute("ALTER TABLE regions ADD COLUMN footprint geometry(Polygon,4326)")
        op.execute("CREATE INDEX ix_regions_footprint ON regions USING GIST(footprint)")


def downgrade():
    for table in [
        "analysis_results",
        "analysis_jobs",
        "scenes",
        "model_versions",
        "dataset_provenance",
        "regions",
    ]:
        op.drop_table(table)
