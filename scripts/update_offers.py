"""
PASO 4: Migración de update_offers.py a Google Sheets

Este script descarga ofertas de Mercado Público y las almacena en Google Sheets.
También gestiona filtros de usuario y envía alertas por email.

Uso:
    python -m scripts.update_offers_v2
"""

import argparse
import csv
import io
import json
import logging
import os
import re
import zipfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

from scripts.helpers import (
    append_to_sheet,
    append_many_rows,
    get_sheet_data,
    clean_old_offers
)
from app.query import calculate_days_until_close
from app.db import get_conn, init_db

DEFAULT_FEED_URL = "https://www.mercadopublico.cl/Portal/att.ashx?id=5"
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "update_trace.log"
BATCH_SIZE = 200


def get_logger() -> logging.Logger:
    """Configurar logger para la ejecución"""
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
    """Normalizar nombres de columnas"""
    value = value.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = value.replace("á", "a").replace("é", "e").replace("í", "i")
    value = value.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return value


def normalize_cell(value) -> str:
    """Normalizar valores de celdas"""
    if isinstance(value, list):
        return " | ".join((str(v).strip() for v in value if v is not None))
    return str(value or "").strip()


def detect_encoding(raw: bytes) -> str:
    """Detectar encoding del CSV"""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample: str) -> str:
    """Detectar delimitador del CSV"""
    return ";" if sample.count(";") >= sample.count(",") else ","


def is_header_row(normalized_headers: List[str]) -> bool:
    """Detectar si una fila es header"""
    header_set = set(normalized_headers)
    # Headers posibles de Mercado Público
    code_keys = {"codigoexterno", "codigo_externo", "codigo", "textbox36"}
    name_keys = {"nombre", "textbox37", "nombre_licitacion"}
    desc_keys = {"descripcion", "textbox38", "rbidescription"}
    
    # Verificar que tenga código Y (nombre O descripción)
    has_code = bool(header_set.intersection(code_keys))
    has_name = bool(header_set.intersection(name_keys))
    has_desc = bool(header_set.intersection(desc_keys))
    
    # Must have code and at least 2 of (name, description, tipo, rbidescription)
    return has_code and (has_name or has_desc) and len(normalized_headers) >= 3


def parse_monto(value: str) -> str:
    """Parsear monto a número"""
    if not value:
        return "0"
    cleaned = value.replace(".", "").replace(",", ".").strip()
    try:
        return str(float(cleaned))
    except ValueError:
        return "0"


def parse_date(value: str) -> str:
    """Parsear fecha a ISO format"""
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
    """Parsear CSV desde bytes"""
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
    """Extraer primer valor disponible de varias claves"""
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return ""


def download_csv(feed_url: str) -> Tuple[List[Dict[str, str]], str]:
    """Descargar CSV desde Mercado Público"""
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
    """Mapear fila CSV a esquema de oferta
    
    Nota: El CSV de Mercado Público tiene headers específicos como:
    Textbox36, Textbox37, Textbox38, etc.
    """
    # Mapeo completo de posibles nombres de columnas
    codigo = pick_value(
        row, 
        "textbox36",  # MP actual
        "codigoexterno", "codigo_externo", "codigo"
    )
    
    nombre = pick_value(
        row, 
        "textbox37",  # MP actual
        "nombre", "nombre_licitacion"
    )
    
    descripcion = pick_value(
        row, 
        "textbox38",  # MP actual: Descripción Licitación
        "descripcion", "descripcion_licitacion", "rbidescription"
    )
    
    descripcion_producto = pick_value(
        row, 
        "rbidescription",  # MP actual: Descripción del Producto
        "productoname", "producto", "descripcion_producto"
    )
    
    nombre_organismo = pick_value(
        row, 
        "textbox39",  # MP actual
        "nombreorganismo", "nombre_organismo", "organismo"
    )
    
    estado = pick_value(
        row, 
        "codigoestado", "codigo_estado", "estado"
    )
    
    region = pick_value(
        row, 
        "citname",  # MP actual
        "regionunidad", "region_unidad", "region"
    )
    
    comuna = pick_value(
        row, 
        "comunaunidad", "comuna_unidad", "comuna"
    )
    
    tipo_oferta = pick_value(
        row,
        "tipolc",  # MP actual
        "tipoconvocatoria", "tipo_convocatoria", "tipooferta", "tipo_oferta", "tipo"
    )
    
    moneda = pick_value(row, "moneda", "codigomoneda", "codigo_moneda")
    
    monto_raw = pick_value(row, "montoestimado", "monto_estimado", "monto")
    
    fecha_publicacion = pick_value(
        row, 
        "textbox40",  # MP actual
        "fechapublicacion", "fecha_publicacion", "fecha_publicacion_oferta"
    )
    
    fecha_cierre = pick_value(
        row, 
        "fechacierre1",  # MP actual
        "fechacierre", "fecha_cierre"
    )
    
    # URL: si no viene en CSV, generar desde código
    link = pick_value(row, "link", "url", "url_licitacion", "url_licitacion_detalle")
    if not link and codigo:
        link = f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion={codigo}"
    
    return {
        "codigo_externo": codigo,
        "nombre": nombre,
        "descripcion": descripcion,
        "descripcion_producto": descripcion_producto,
        "organismo": nombre_organismo,
        "estado": estado,
        "region": region,
        "comuna": comuna,
        "tipo_oferta": tipo_oferta,
        "moneda": moneda,
        "monto_estimado": parse_monto(monto_raw),
        "fecha_publicacion": parse_date(fecha_publicacion),
        "fecha_cierre": parse_date(fecha_cierre),
        "link": link,
    }


def update_offers(feed_url: str = DEFAULT_FEED_URL):
    """Descargar ofertas de Mercado Público y guardar en Google Sheets"""

    stats = {
        "new_count": 0,
        "updated_count": 0,
        "deleted_count": 0,
        "total_matches": 0,
        "total_alerts_sent": 0,
    }

    start_time = time.time()

    try:

        print("[INFO] Iniciando actualización de ofertas...")
        
        # Inicializar base de datos (crear tabla si no existe)
        init_db()

        # DESCARGAR CSV
        offers_data, filename = download_csv(feed_url)

        print(
            f"[INFO] Mercado Público retornó {len(offers_data)} filas desde {filename}"
        )

        # MAPEAR OFERTAS
        offers_raw = [map_offer(row) for row in offers_data]

        print(f"[INFO] {len(offers_raw)} ofertas mapeadas")

        # OBTENER EXISTENTES
        existing_offers = get_sheet_data("ofertas")

        existing_codes = set()

        if existing_offers and len(existing_offers) > 1:
            for row in existing_offers[1:]:
                if row and len(row) > 0:
                    existing_codes.add(str(row[0]).strip())

        print(f"[INFO] Existen {len(existing_codes)} ofertas previas")

        # DEDUPLICAR
        unique_offers = {}

        for offer in offers_raw:

            codigo = offer.get("codigo_externo", "").strip()

            if not codigo:
                continue

            # mantener solo primera aparición
            if codigo not in unique_offers:
                unique_offers[codigo] = offer

        print(
            f"[DEDUP] {len(unique_offers)} ofertas únicas"
        )

        # PREPARAR INSERTS
        rows_to_insert = []

        now_iso = datetime.now().isoformat()

        for codigo, offer in unique_offers.items():

            # evitar reinsertar
            if codigo in existing_codes:
                stats["updated_count"] += 1
                continue

            minimal_raw = {
                "codigo": codigo,
                "producto": offer.get("descripcion_producto"),
            }
            
            # Calcular días restantes hasta cierre
            dias_que_quedan = calculate_days_until_close(offer.get("fecha_cierre", ""))

            values = [
                offer.get("codigo_externo", ""),
                offer.get("nombre", ""),
                offer.get("descripcion", ""),
                offer.get("descripcion_producto", ""),
                offer.get("organismo", ""),
                offer.get("estado", ""),
                offer.get("region", ""),
                offer.get("comuna", ""),
                offer.get("tipo_oferta", ""),
                offer.get("moneda", ""),
                offer.get("monto_estimado", "0"),
                offer.get("fecha_publicacion", ""),
                offer.get("fecha_cierre", ""),
                dias_que_quedan if dias_que_quedan is not None else "",
                offer.get("link", ""),
                json.dumps(minimal_raw, ensure_ascii=False),
                now_iso,
                now_iso,
                now_iso,
            ]

            rows_to_insert.append((values, [
                offer.get("codigo_externo", ""),
                offer.get("nombre", ""),
                offer.get("descripcion", ""),
                offer.get("descripcion_producto", ""),
                offer.get("organismo", ""),
                offer.get("estado", ""),
                offer.get("region", ""),
                offer.get("comuna", ""),
                offer.get("tipo_oferta", ""),
                offer.get("moneda", ""),
                offer.get("monto_estimado", "0"),
                offer.get("fecha_publicacion", ""),
                offer.get("fecha_cierre", ""),
                dias_que_quedan if dias_que_quedan is not None else "",
                offer.get("link", ""),
                json.dumps(minimal_raw, ensure_ascii=False),
                now_iso,
            ]))

            stats["new_count"] += 1

        print(
            f"[INSERT] Preparadas {len(rows_to_insert)} nuevas ofertas"
        )

        # INSERTS POR BATCH
        for i in range(0, len(rows_to_insert), BATCH_SIZE):

            chunk = rows_to_insert[i:i + BATCH_SIZE]

            print(
                f"[BATCH] Insertando {i} - {i + len(chunk)}"
            )

            # Insert to Google Sheets (using google_sheets_values)
            gs_rows = [item[0] for item in chunk]
            append_many_rows("ofertas", gs_rows)

            # Insert to SQLite database (using sqlite_values)
            with get_conn() as conn:
                for item in chunk:
                    sqlite_values = item[1]
                    conn.execute("""
                        INSERT OR REPLACE INTO offers 
                        (codigo_externo, nombre, descripcion, descripcion_producto, 
                         organismo, estado, region, comuna, tipo_oferta, moneda, 
                         monto_estimado, fecha_publicacion, fecha_cierre, dias_que_quedan, 
                         link, raw_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, sqlite_values)
                conn.commit()

            # evitar quota exceeded
            time.sleep(2)

        # LIMPIAR ANTIGUAS
        stats["deleted_count"] = clean_old_offers()

        # ALERTAS DESACTIVADAS
        stats["total_matches"] = 0
        stats["total_alerts_sent"] = 0

        # REGISTRAR EJECUCIÓN
        duration = int(time.time() - start_time)

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        append_to_sheet("notification_runs", [
            run_id,
            datetime.now().isoformat(),
            "SUCCESS",
            stats["new_count"],
            stats["updated_count"],
            stats["deleted_count"],
            stats["total_matches"],
            stats["total_alerts_sent"],
            "",
            duration,
        ])

        print("[SUCCESS] Update completado")
        print(f"Nuevas: {stats['new_count']}")
        print(f"Existentes: {stats['updated_count']}")
        print(f"Borradas: {stats['deleted_count']}")

        return stats

    except Exception as e:

        print(f"[ERROR] Fallo update_offers: {str(e)}")

        duration = int(time.time() - start_time)

        append_to_sheet("notification_runs", [
            f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            datetime.now().isoformat(),
            "ERROR",
            stats["new_count"],
            stats["updated_count"],
            stats["deleted_count"],
            stats["total_matches"],
            stats["total_alerts_sent"],
            str(e),
            duration,
        ])

        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualizar ofertas desde Mercado Público")
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help="URL del feed CSV (default: Mercado Público oficial)"
    )
    args = parser.parse_args()
    
    try:
        update_offers(feed_url=args.feed_url)
    except Exception as e:
        print(f"[FATAL] {str(e)}")
        exit(1)
