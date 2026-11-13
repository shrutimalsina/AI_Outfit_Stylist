"""HTTP interface for a locally configured outfit catalog."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from io import BytesIO
import logging
import os
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from pydantic import BaseModel, Field
from psycopg import Error as DatabaseError

from backend.app.database.connection import active_snapshot, load_evaluation, record_request
from backend.app.ml.encoder import ClipEncoder
from backend.app.recommendations.engine import ALGORITHM_VERSION, Catalog, NoCandidatesError
from pipeline.prepare_dataset import read_json

MAX_BYTES = 5 * 1024 * 1024
logger = logging.getLogger(__name__)


def fail(status, code, message):
    raise HTTPException(status, detail={"code": code, "message": message})


def decode(payload):
    if len(payload) > MAX_BYTES:
        fail(413, "file_too_large", "Maximum upload size is 5 MiB")
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
            if (image.format not in {"JPEG", "PNG", "WEBP"} or min(width, height) < 64
                    or width * height > 16_000_000):
                raise ValueError("unsupported format or dimensions")
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            return image.convert("RGB")
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        fail(422, "invalid_image", "Use a valid JPEG, PNG, or WebP of at least 64 × 64 pixels")


class ItemQuery(BaseModel):
    item_id: str
    top_k: int = Field(3, ge=1, le=3)
    alternatives: int = Field(0, ge=0, le=12)


def create_app(catalog=None, encoder_factory=ClipEncoder, image_root=None):
    model = None
    inference_lock = Lock()
    root = Path(image_root or os.environ.get("STYLIST_IMAGE_ROOT", "data/raw/polyvore_outfits")).resolve()

    @asynccontextmanager
    async def lifespan(_):
        nonlocal catalog
        snapshot = os.environ.get("STYLIST_SNAPSHOT")
        if catalog is None and not snapshot and os.environ.get("DATABASE_URL"):
            try:
                snapshot = active_snapshot()
            except DatabaseError:
                logger.exception("Unable to resolve the active catalog")
        if catalog is None and snapshot:
            try:
                catalog = Catalog(Path(snapshot))
            except (OSError, ValueError):
                logger.exception("Unable to load catalog")
        yield

    app = FastAPI(title="AI Outfit Stylist", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def http_error(_, exc):
        detail = exc.detail if isinstance(exc.detail, dict) else {
            "code": "http_error", "message": str(exc.detail)}
        return JSONResponse({"error": detail}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        return JSONResponse({"error": {"code": "invalid_request", "message": "Invalid request fields"}},
                            status_code=422)

    @app.exception_handler(Exception)
    async def internal_error(_, exc):
        logger.error("Unhandled API error", exc_info=exc)
        return JSONResponse({"error": {"code": "internal_error", "message": "Internal server error"}},
                            status_code=500)

    def current():
        if catalog is None:
            fail(503, "catalog_unavailable", "A validated catalog snapshot is required")
        return catalog

    def get_model():
        nonlocal model
        if model is None:
            try:
                model = encoder_factory()
            except Exception:
                logger.exception("Unable to load CLIP")
                fail(503, "model_unavailable", "CLIP model is unavailable")
        return model

    def lookup(item_id):
        selected = current()
        if item_id not in selected.rows:
            fail(404, "item_not_found", "Catalog item was not found")
        return selected.items[selected.rows[item_id]]

    def result(category, select, embedding, alternatives):
        selected = current()
        if category not in selected.policy:
            fail(422, "invalid_category", "Select a supported clothing category")
        try:
            matches, warnings = select()
        except NoCandidatesError:
            fail(404, "no_candidates", "No eligible catalog items")
        request_id = uuid4()
        if os.environ.get("DATABASE_URL"):
            try:
                record_request(request_id, selected.metadata["snapshot_id"], category)
            except DatabaseError:
                logger.exception("Unable to persist recommendation request")
                fail(503, "database_unavailable", "Database is unavailable")
        def serialize(match):
            return {**asdict(match), "image_url": f"/api/v1/items/{match.item_id}/image",
                    "title": lookup(match.item_id).get("title")}

        payload = {
            "request_id": str(request_id), "snapshot_id": selected.metadata["snapshot_id"],
            "model": selected.metadata["model"], "algorithm_version": ALGORITHM_VERSION,
            "input_category": category, "warnings": warnings,
            "recommendations": [serialize(match) for match in matches],
        }
        if alternatives:
            payload["alternatives"] = {
                slot: [serialize(match) for match in ranked]
                for slot, ranked in selected.alternatives(embedding, matches, alternatives).items()
            }
        return payload

    @app.get("/api/v1/catalog/samples")
    def samples():
        selected = current()
        result = []
        for category in ("top", "dress", "outerwear", "footwear"):
            for index in selected.category_rows[category]:
                item = selected.items[index]
                path = (root / item["image"]).resolve()
                if path.is_relative_to(root) and path.is_file():
                    result.append({"item_id": item["id"], "title": item.get("title"),
                                   "category": category,
                                   "image_url": f"/api/v1/items/{item['id']}/image"})
                    break
        return result

    @app.get("/health/live")
    def live():
        return {"status": "live"}

    @app.get("/health/ready")
    def ready():
        selected = current()
        try:
            registered = active_snapshot()
        except (DatabaseError, KeyError):
            fail(503, "database_unavailable", "Database is unavailable")
        if not registered or Path(registered).name != selected.metadata["snapshot_id"]:
            fail(503, "catalog_unavailable", "The loaded snapshot is not active in PostgreSQL")
        with inference_lock:
            get_model()
        return {"status": "ready"}

    @app.get("/api/v1/catalog")
    def catalog_metadata():
        return current().metadata

    @app.get("/api/v1/categories")
    def categories():
        return current().policy

    @app.get("/api/v1/items/{item_id}")
    def item(item_id: str):
        row = lookup(item_id)
        return {key: row.get(key) for key in ("id", "title", "category")}

    @app.get("/api/v1/items/{item_id}/image")
    def item_image(item_id: str):
        path = (root / lookup(item_id)["image"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            fail(404, "image_not_found", "Catalog image is unavailable")
        return FileResponse(path)

    @app.post("/api/v1/recommendations/by-item")
    def by_item(query: ItemQuery):
        row = lookup(query.item_id)
        selected = current()
        return result(row["category"], lambda: selected.recommend_by_item(query.item_id, top_k=query.top_k),
                      selected.matrix[selected.rows[query.item_id]], query.alternatives)

    @app.post("/api/v1/recommendations")
    def upload(image: UploadFile = File(), category: str = Form(), top_k: int = Form(3, ge=1, le=3),
               alternatives: int = Form(0, ge=0, le=12)):
        selected = current()
        if category not in selected.policy:
            fail(422, "invalid_category", "Select a supported clothing category")
        with decode(image.file.read(MAX_BYTES + 1)) as pixels:
            with inference_lock:
                query = get_model()([pixels])[0]
        return result(category, lambda: selected.recommend(query, category, top_k=top_k), query, alternatives)

    @app.get("/api/v1/evaluations/{run_id}")
    def evaluation(run_id: str):
        try:
            identifier = str(UUID(run_id))
        except ValueError:
            fail(404, "evaluation_not_found", "Evaluation was not found")
        if os.environ.get("DATABASE_URL"):
            try:
                saved = load_evaluation(identifier)
            except DatabaseError:
                fail(503, "database_unavailable", "Database is unavailable")
            if saved is not None:
                return saved
        report = Path(os.environ.get("STYLIST_REPORT_ROOT", "data/reports")) / f"{identifier}.json"
        if not report.is_file():
            fail(404, "evaluation_not_found", "Evaluation was not found")
        return read_json(report)

    return app


app = create_app()
