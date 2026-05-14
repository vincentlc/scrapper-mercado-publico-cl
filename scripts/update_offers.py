import argparse
import csv
import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

from app.db import get_conn, init_db


DEFAULT_FEED_URL = "https://www.mercadopublico.cl/Portal/att.ashx?id=5"
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "update_trace.log"


def get_logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("update_offers")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def normalize_header(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return value


def normalize_cell(value) -> str:
    if isinstance(value, list):
        return " | ".join((str(v).strip() for v in value if v is not None))
    return str(value or "").strip()


def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample: str) -> str:
    return ";" if sample.count(";") >= sample.count(",") else ","


def is_header_row(normalized_headers: List[str]) -> bool:
    header_set = set(normalized_headers)
    code_keys = {"codigoexterno", "codigo_externo", "codigo", "textbox36"}
    return bool(header_set.intersection(code_keys)) and len(normalized_headers) >= 2


def parse_monto(value: str) -> float:
    if not value:
        return 0.0
    cleaned = value.replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    patterns = [
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
    ]
    for pattern in patterns:
        try:
            dt = datetime.strptime(value, pattern)
            return dt.isoformat()
        except ValueError:
            continue
    return value


def parse_csv_bytes(raw: bytes) -> List[Dict[str, str]]:
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    delimiter = detect_delimiter(text[:2000])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    headers: List[str] = []
    for raw_row in reader:
        normalized_headers = [normalize_header(c) for c in raw_row]
        if is_header_row(normalized_headers):
            headers = raw_row
            break
    if not headers:
        raise RuntimeError("Could not detect CSV header row with offer columns.")

    out: List[Dict[str, str]] = []
    for row in reader:
        if not row:
            continue
        normalized: Dict[str, str] = {}
        for idx, key in enumerate(headers):
            cell = row[idx] if idx < len(row) else ""
            normalized[normalize_header(key)] = normalize_cell(cell)
        if len(row) > len(headers):
            normalized["extra_columns"] = normalize_cell(row[len(headers) :])
        out.append(normalized)
    return out


def pick_value(row: Dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return ""


def download_csv(feed_url: str) -> Tuple[List[Dict[str, str]], str]:
    response = requests.get(feed_url, timeout=90)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    content = response.content

    if "zip" in content_type or content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for info in zf.infolist():
                if info.filename.lower().endswith(".csv"):
                    return parse_csv_bytes(zf.read(info.filename)), info.filename
        raise RuntimeError("ZIP downloaded but no CSV found inside.")

    return parse_csv_bytes(content), "feed.csv"


def map_offer(row: Dict[str, str]) -> Dict[str, str]:
    monto_raw = pick_value(row, "montoestimado", "monto_estimado", "monto")
    codigo = pick_value(row, "codigoexterno", "codigo_externo", "codigo", "textbox36")
    return {
        "codigo_externo": codigo,
        "nombre": pick_value(row, "nombre", "nombre_licitacion", "textbox37"),
        "descripcion": pick_value(row, "descripcion", "descripcion_licitacion", "textbox38", "rbidescription"),
        "descripcion_producto": pick_value(row, "productoname", "producto", "descripcion_producto"),
        "organismo": pick_value(row, "nombreorganismo", "nombre_organismo", "organismo", "textbox39"),
        "estado": pick_value(row, "codigoestado", "codigo_estado", "estado"),
        "region": pick_value(row, "regionunidad", "region_unidad", "region", "citname"),
        "comuna": pick_value(row, "comunaunidad", "comuna_unidad", "comuna"),
        "tipo_oferta": pick_value(
            row,
            "tipoconvocatoria",
            "tipo_convocatoria",
            "tipooferta",
            "tipo_oferta",
            "tipo",
            "tipolc",
        ),
        "moneda": pick_value(row, "moneda", "codigomoneda", "codigo_moneda"),
        "monto_estimado": parse_monto(monto_raw),
        "fecha_publicacion": parse_date(
            pick_value(row, "fechapublicacion", "fecha_publicacion", "fecha_publicacion_oferta", "textbox40")
        ),
        "fecha_cierre": parse_date(pick_value(row, "fechacierre", "fecha_cierre", "fechacierre1")),
        "link": pick_value(
            row,
            "link",
            "url",
            "url_licitacion",
            "url_licitacion_detalle",
        )
        or (f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion={codigo}" if codigo else ""),
        "raw_json": json.dumps(row, ensure_ascii=True),
    }


def upsert_offers(rows: Iterable[Dict[str, str]]) -> Tuple[int, int]:
    inserted = 0
    updated = 0
    skipped_missing_code = 0
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        for row in rows:
            offer = map_offer(row)
            if not offer["codigo_externo"]:
                skipped_missing_code += 1
                continue
            existing = conn.execute(
                "SELECT codigo_externo FROM offers WHERE codigo_externo = ?",
                (offer["codigo_externo"],),
            ).fetchone()
            if existing:
                updated += 1
            else:
                inserted += 1
            conn.execute(
                """
                INSERT INTO offers (
                    codigo_externo, nombre, descripcion, descripcion_producto, organismo, estado, region, comuna,
                    tipo_oferta, moneda, monto_estimado, fecha_publicacion, fecha_cierre,
                    link, raw_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_externo) DO UPDATE SET
                    nombre=excluded.nombre,
                    descripcion=excluded.descripcion,
                    descripcion_producto=excluded.descripcion_producto,
                    organismo=excluded.organismo,
                    estado=excluded.estado,
                    region=excluded.region,
                    comuna=excluded.comuna,
                    tipo_oferta=excluded.tipo_oferta,
                    moneda=excluded.moneda,
                    monto_estimado=excluded.monto_estimado,
                    fecha_publicacion=excluded.fecha_publicacion,
                    fecha_cierre=excluded.fecha_cierre,
                    link=excluded.link,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                (
                    offer["codigo_externo"],
                    offer["nombre"],
                    offer["descripcion"],
                    offer["descripcion_producto"],
                    offer["organismo"],
                    offer["estado"],
                    offer["region"],
                    offer["comuna"],
                    offer["tipo_oferta"],
                    offer["moneda"],
                    offer["monto_estimado"],
                    offer["fecha_publicacion"],
                    offer["fecha_cierre"],
                    offer["link"],
                    offer["raw_json"],
                    now,
                ),
            )
        conn.commit()
    logger = get_logger()
    logger.info("Upsert summary inserted=%s updated=%s skipped_missing_code=%s", inserted, updated, skipped_missing_code)
    return inserted, updated


def match_saved_filters() -> int:
    matched = 0
    with get_conn() as conn:
        filters = conn.execute("SELECT * FROM saved_filters").fetchall()
        for sf in filters:
            clauses = []
            args: List[object] = []
            if sf["keyword"]:
                clauses.append("(nombre LIKE ? OR descripcion LIKE ?)")
                pattern = f"%{sf['keyword']}%"
                args.extend([pattern, pattern])
            for col in ("tipo_oferta", "estado", "organismo", "region", "comuna"):
                if sf[col]:
                    clauses.append(f"{col} = ?")
                    args.append(sf[col])
            if sf["utm_range"]:
                ur = sf["utm_range"]
                if ur == "lt100":
                    clauses.append("LOWER(tipo_oferta) LIKE '%inferior a 100 utm%'")
                elif ur == "100_1000":
                    clauses.append("LOWER(tipo_oferta) LIKE '%igual o superior a 100 utm%'")
                elif ur == "1000_2000":
                    clauses.append("LOWER(tipo_oferta) LIKE '%igual o superior a 1.000 utm%'")
                elif ur == "2000_5000":
                    clauses.append(
                        "(LOWER(tipo_oferta) LIKE '%igual o superior a 2.000 utm%' OR LOWER(tipo_oferta) LIKE '%igual o superior a 2000 utm%')"
                    )
                elif ur == "gt5000":
                    clauses.append("LOWER(tipo_oferta) LIKE '%mayor a 5000 utm%'")
            if sf["min_monto"] is not None:
                clauses.append("monto_estimado >= ?")
                args.append(sf["min_monto"])
            if sf["max_monto"] is not None:
                clauses.append("monto_estimado <= ?")
                args.append(sf["max_monto"])
            if sf["start_date"]:
                clauses.append("fecha_publicacion >= ?")
                args.append(sf["start_date"])
            if sf["end_date"]:
                clauses.append("fecha_publicacion <= ?")
                args.append(sf["end_date"])
            if sf["start_close_date"]:
                clauses.append("fecha_cierre >= ?")
                args.append(sf["start_close_date"])
            if sf["end_close_date"]:
                clauses.append("fecha_cierre <= ?")
                args.append(sf["end_close_date"])
            where = " AND ".join(clauses) if clauses else "1=1"
            query = f"SELECT COUNT(*) AS c FROM offers WHERE {where} AND updated_at >= datetime('now', '-1 day')"
            c = conn.execute(query, args).fetchone()["c"]
            if c > 0:
                matched += 1
    return matched


def persist_run(inserted: int, updated: int, matched_filters: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notification_runs (offers_inserted, offers_updated, matched_saved_filters)
            VALUES (?, ?, ?)
            """,
            (inserted, updated, matched_filters),
        )
        conn.commit()


def run_update(feed_url: str = DEFAULT_FEED_URL, csv_path: str = "") -> Dict[str, object]:
    logger = get_logger()
    logger.info("Starting update feed_url=%s csv_path=%s", feed_url, csv_path or "<none>")
    init_db()
    if csv_path:
        raw = Path(csv_path).read_bytes()
        rows = parse_csv_bytes(raw)
        source_name = Path(csv_path).name
        logger.info("Loaded local CSV source=%s rows=%s", source_name, len(rows))
    else:
        rows, source_name = download_csv(feed_url)
        logger.info("Downloaded source=%s rows=%s", source_name, len(rows))
    inserted, updated = upsert_offers(rows)
    matched = match_saved_filters()
    persist_run(inserted, updated, matched)
    logger.info("Finished update source=%s inserted=%s updated=%s matched_saved_filters=%s", source_name, inserted, updated, matched)
    return {
        "source": source_name,
        "rows": len(rows),
        "inserted": inserted,
        "updated": updated,
        "matched_saved_filters": matched,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download, parse, and upsert MercadoPublico licitaciones.")
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL, help="MercadoPublico feed URL")
    parser.add_argument("--csv-path", default="", help="Local CSV path for debugging/import")
    args = parser.parse_args()
    result = run_update(args.feed_url, args.csv_path)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
