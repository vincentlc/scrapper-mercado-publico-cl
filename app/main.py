from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.db import get_conn, init_db
from app.query import build_offer_filters, normalize_option_values, format_tipo_oferta, calculate_days_until_close
from scripts.update_offers import run_update


class SavedFilterIn(BaseModel):
    name: str
    keyword: Optional[str] = None
    tipo_oferta: Optional[str] = None
    estado: Optional[str] = None
    organismo: Optional[str] = None
    region: Optional[str] = None
    comuna: Optional[str] = None
    utm_range: Optional[str] = None
    min_monto: Optional[float] = None
    max_monto: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_close_date: Optional[str] = None
    end_close_date: Optional[str] = None
    min_days_to_close: Optional[int] = None
    max_days_to_close: Optional[int] = None


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app = FastAPI(title="ScrapMercadoPublico")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/update-offers")
def update_offers_now() -> Dict[str, object]:
    try:
        return run_update()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update failed: {exc}") from exc


@app.get("/api/offers")
def list_offers(
    keyword: Optional[str] = None,
    tipo_oferta: Optional[str] = None,
    estado: Optional[str] = None,
    organismo: Optional[str] = None,
    region: Optional[str] = None,
    comuna: Optional[str] = None,
    utm_range: Optional[str] = None,
    min_monto: Optional[float] = None,
    max_monto: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_close_date: Optional[str] = None,
    end_close_date: Optional[str] = None,
    min_days_to_close: Optional[int] = None,
    max_days_to_close: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Dict[str, object]:
    where_sql, args = build_offer_filters(
        keyword=keyword,
        tipo_oferta=tipo_oferta,
        estado=estado,
        organismo=organismo,
        region=region,
        comuna=comuna,
        utm_range=utm_range,
        min_monto=min_monto,
        max_monto=max_monto,
        start_date=start_date,
        end_date=end_date,
        start_close_date=start_close_date,
        end_close_date=end_close_date,
        min_days_to_close=min_days_to_close,
        max_days_to_close=max_days_to_close,
    )
    offset = (page - 1) * page_size
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM offers WHERE {where_sql}", args).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT * FROM offers
            WHERE {where_sql}
            ORDER BY fecha_publicacion DESC, updated_at DESC
            LIMIT ? OFFSET ?
            """,
            [*args, page_size, offset],
        ).fetchall()
        items = [dict(r) for r in rows]
    
    # Enriquecer datos con tipo formateado y días restantes
    for item in items:
        item["tipo_oferta_formateado"] = format_tipo_oferta(item.get("tipo_oferta", ""))
        item["dias_para_cierre"] = calculate_days_until_close(item.get("fecha_cierre", ""))
    
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/filters/options")
def filter_options() -> Dict[str, List[str]]:
    fields = ["tipo_oferta", "estado", "organismo", "region", "comuna"]
    out: Dict[str, List[str]] = {}
    with get_conn() as conn:
        for field in fields:
            rows = conn.execute(
                f"SELECT DISTINCT {field} AS value FROM offers WHERE {field} IS NOT NULL AND {field} <> '' ORDER BY {field} LIMIT 1000"
            ).fetchall()
            out[field] = normalize_option_values([dict(r) for r in rows])
    return out


@app.get("/api/saved-filters")
def get_saved_filters() -> Dict[str, object]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM saved_filters ORDER BY name").fetchall()
    return {"items": [dict(r) for r in rows]}


@app.post("/api/saved-filters")
def create_saved_filter(payload: SavedFilterIn) -> Dict[str, object]:
    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO saved_filters (
                    name, keyword, tipo_oferta, estado, organismo, region, comuna,
                    utm_range, min_monto, max_monto, start_date, end_date, start_close_date, end_close_date,
                    min_days_to_close, max_days_to_close
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.name,
                    payload.keyword,
                    payload.tipo_oferta,
                    payload.estado,
                    payload.organismo,
                    payload.region,
                    payload.comuna,
                    payload.utm_range,
                    payload.min_monto,
                    payload.max_monto,
                    payload.start_date,
                    payload.end_date,
                    payload.start_close_date,
                    payload.end_close_date,
                    payload.min_days_to_close,
                    payload.max_days_to_close,
                ),
            )
            conn.commit()
            created = conn.execute("SELECT * FROM saved_filters WHERE name = ?", (payload.name,)).fetchone()
            return {"item": dict(created)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not save filter: {exc}") from exc


@app.delete("/api/saved-filters/{filter_id}")
def delete_saved_filter(filter_id: int) -> Dict[str, str]:
    with get_conn() as conn:
        conn.execute("DELETE FROM saved_filters WHERE id = ?", (filter_id,))
        conn.commit()
    return {"status": "ok"}
