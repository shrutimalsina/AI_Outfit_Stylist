# Deployment and verification

Use the [README](../README.md) for startup, catalog publication, and database backups. Run `bash scripts/smoke_compose.sh` to test an isolated fixture stack. It exercises PostgreSQL migrations, snapshot publication, and the frontend proxy. Production operators should terminate TLS at the reverse proxy and mount persistent catalog and database storage.

## Performance measurements

With the API serving the same snapshot, run from the repository root:

```sh
.venv/bin/python -m scripts.benchmark "$SNAPSHOT_DIR" /path/to/photo.jpg top \
  data/reports/benchmark.json --hardware "CPU model and memory" \
  --api http://127.0.0.1:8000
```

Omit `--api` to measure inference and ranking without HTTP. The cold measurement includes encoder initialization and first inference using the current model cache. Each warmed measurement discards one warm-up and reports median and p95. Batch throughput measures encoding of already decoded images. Matrix bytes describe the embedding payload; process memory also includes model weights, metadata, and runtime overhead.
