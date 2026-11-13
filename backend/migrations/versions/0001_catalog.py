"""Initial PostgreSQL catalog and experiment schema."""

from alembic import op

revision = "0001_catalog"
down_revision = None

TABLES = {
    "datasets": "id uuid PRIMARY KEY, source text NOT NULL, revision text NOT NULL, UNIQUE(source, revision)",
    "catalog_snapshots": """id text PRIMARY KEY, dataset_id uuid NOT NULL REFERENCES datasets,
        manifest_path text NOT NULL, matrix_sha256 text NOT NULL CHECK (length(matrix_sha256) = 64),
        dimension integer NOT NULL CHECK (dimension = 512), active boolean NOT NULL DEFAULT false""",
    "items": """id uuid PRIMARY KEY, dataset_id uuid NOT NULL REFERENCES datasets,
        source_id text NOT NULL, category text NOT NULL CHECK (category IN
        ('top','bottom','dress','outerwear','footwear','accessory','unknown')),
        metadata jsonb NOT NULL, UNIQUE(dataset_id, source_id)""",
    "outfits": """id uuid PRIMARY KEY, dataset_id uuid NOT NULL REFERENCES datasets,
        source_id text NOT NULL, split text NOT NULL CHECK (split IN ('train','valid','test')),
        UNIQUE(dataset_id, source_id)""",
    "outfit_items": """outfit_id uuid REFERENCES outfits, item_id uuid REFERENCES items,
        PRIMARY KEY(outfit_id, item_id)""",
    "snapshot_items": """snapshot_id text REFERENCES catalog_snapshots, item_id uuid REFERENCES items,
        PRIMARY KEY(snapshot_id, item_id)""",
    "item_embeddings": """snapshot_id text, item_id uuid, row_index integer NOT NULL CHECK (row_index >= 0),
        PRIMARY KEY(snapshot_id, item_id), UNIQUE(snapshot_id, row_index),
        FOREIGN KEY(snapshot_id, item_id) REFERENCES snapshot_items""",
    "evaluation_runs": """id uuid PRIMARY KEY, snapshot_id text NOT NULL REFERENCES catalog_snapshots,
        report jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()""",
    "evaluation_cases": """run_id uuid REFERENCES evaluation_runs, outfit_id uuid REFERENCES outfits,
        query_id uuid REFERENCES items, hidden_id uuid REFERENCES items, outcome jsonb NOT NULL,
        CHECK (query_id <> hidden_id), PRIMARY KEY(run_id, outfit_id, query_id, hidden_id)""",
    "recommendation_requests": """id uuid PRIMARY KEY, snapshot_id text NOT NULL REFERENCES catalog_snapshots,
        input_category text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()""",
}


def upgrade():
    for table, columns in TABLES.items():
        op.execute(f"CREATE TABLE {table} ({columns})")
    op.execute("CREATE UNIQUE INDEX only_one_active_catalog ON catalog_snapshots (active) WHERE active")
    op.execute("CREATE INDEX outfit_items_by_item ON outfit_items (item_id)")
    op.execute("CREATE INDEX evaluation_runs_by_snapshot ON evaluation_runs (snapshot_id)")


def downgrade():
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
