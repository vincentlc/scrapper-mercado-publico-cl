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
import subprocess
import zipfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Tuple

import requests

from scripts.helpers import (
    append_to_sheet,
    append_many_rows,
    get_sheet_data,
    clean_old_offers
)
from app.query import calculate_days_until_close
from app.db import get_conn, init_db

_FALLBACK_FEED_URL = "https://www.mercadopublico.cl/Portal/att.ashx?id=5"
MP_API_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
API_ESTADOS = {
    "5": "Publicada",
    "6": "Cerrada",
    "7": "Desierta",
    "8": "Adjudicada",
    "18": "Revocada",
    "19": "Suspendida",
}
API_TIPOS = {
    "L1": "Licitación Pública Menor a 100 UTM (L1)",
    "LE": "Licitación Pública Entre 100 y 1000 UTM (LE)",
    "LP": "Licitación Pública Mayor 1000 UTM (LP)",
    "LS": "Licitación Pública Servicios personales especializados (LS)",
    "A1": "Licitación Privada por Licitación Pública anterior sin oferentes (A1)",
    "B1": "Licitación Privada por otras causales, excluidas de la ley de Compras",
    "J1": "Licitación Privada por Servicios de Naturaleza Confidencial",
    "F1": "Licitación Privada por Convenios con Personas Jurídicas Extranjeras fuera del Territorio Nacional",
    "E1": "Licitación Privada por Remanente de Contrato anterior",
    "CO": "Licitación Privada entre 100 y 1000 UTM",
    "B2": "Licitación Privada Mayor a 1000 UTM",
    "A2": "Trato Directo por Producto de Licitación Privada anterior sin oferentes o desierta",
    "D1": "Trato Directo por Proveedor Único (D1)",
    "E2": "Licitación Privada Menor a 100 UTM",
    "C2": "Trato Directo (Cotización) (C2)",
    "C1": "Compra Directa (Orden de compra) (C1)",
    "F2": "Trato Directo (Cotización) (F2)",
    "F3": "Compra Directa (Orden de compra) (F3)",
    "G2": "Directo (Cotización) (G2)",
    "G1": "Compra Directa (Orden de compra) (G1)",
    "R1": "Orden de Compra menor a 3 UTM (R1)",
    "CA": "Orden de Compra sin Resolución (CA)",
    "SE": "Orden de Compra proveniente de adquisición sin emisión automática de OC (SE)",
}
DEFAULT_FEED_URL = os.environ.get("MERCADO_PUBLICO_FEED_URL") or _FALLBACK_FEED_URL
MP_PORTAL_ORIGIN = "https://www.mercadopublico.cl"
MP_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Referer": f"{MP_PORTAL_ORIGIN}/",
}
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
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for pattern in patterns:
        try:
            dt = datetime.strptime(value, pattern)
            return dt.isoformat()
        except ValueError:
            continue
    return value


def format_date_for_sheet(value: str, include_time: bool = False) -> str:
    """Formatear fecha para Google Sheets (dd/mm/yyyy o con hora)."""
    iso_value = parse_date(value)
    if not iso_value:
        return value
    try:
        dt = datetime.fromisoformat(iso_value)
        if include_time:
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
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


def _get_nested(data: dict, *paths: Tuple[str, ...]) -> str:
    for path in paths:
        cur = data
        for key in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(key)
        if cur is not None and cur != "":
            return normalize_cell(cur)
    return ""


def _api_ticket() -> str:
    return os.environ.get("MERCADO_PUBLICO_API_TICKET", "").strip()


def _github_actions_csv_blocked_message() -> str:
    return (
        "Mercado Público bloquea la descarga CSV desde GitHub Actions (403).\n"
        "Configura el secret MERCADO_PUBLICO_API_TICKET:\n"
        "  1. Solicita tu ticket en https://api.mercadopublico.cl/modules/Participa.aspx\n"
        "     (Clave Única → motivo: Solicitud de Ticket)\n"
        "  2. GitHub → Settings → Secrets and variables → Actions → New repository secret\n"
        "     Nombre: MERCADO_PUBLICO_API_TICKET\n"
        "Alternativa: ejecutar el workflow en un self-hosted runner (tu PC)."
    )


def _fetch_licitacion_detail_raw(ticket: str, codigo: str) -> Dict:
    try:
        response = requests.get(
            MP_API_URL,
            params={"codigo": codigo, "ticket": ticket},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("Codigo") not in (None, 0, "0"):
            return {}
        items = payload.get("Listado") or []
        return items[0] if items else {}
    except requests.RequestException:
        return {}


def _resolve_api_estado(item: Dict) -> str:
    raw = _get_nested(item, ("CodigoEstado",), ("Estado",))
    return API_ESTADOS.get(str(raw), raw)


def _resolve_api_tipo(item: Dict) -> str:
    tipo = _get_nested(item, ("Tipo",), ("CodigoTipo",), ("CodigoTipoLicitacion",))
    if tipo in API_TIPOS:
        return API_TIPOS[tipo]
    if tipo and len(tipo) > 4:
        return tipo
    return tipo


def _resolve_api_producto(item: Dict) -> str:
    items = item.get("Items")
    if isinstance(items, dict):
        listado = items.get("Listado") or []
        if listado and isinstance(listado[0], dict):
            return _get_nested(
                listado[0],
                ("NombreProducto",),
                ("Descripcion",),
                ("EspecificacionComprador",),
            )
    return _get_nested(item, ("DescripcionProducto",), ("NombreProducto",))


def fetch_offers_from_api(ticket: str) -> List[Dict[str, str]]:
    """Obtener licitaciones publicadas vía API oficial (funciona desde cloud)."""
    response = requests.get(
        MP_API_URL,
        params={"estado": "activas", "ticket": ticket},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()

    codigo = payload.get("Codigo")
    if codigo not in (None, 0, "0"):
        raise RuntimeError(
            f"API Mercado Público error {codigo}: {payload.get('Mensaje', 'sin mensaje')}"
        )

    items = payload.get("Listado") or []
    if not items:
        raise RuntimeError("API retornó Listado vacío para estado=activas")

    return [map_offer_from_api(item) for item in items]


def enrich_offer_from_api(ticket: str, offer: Dict[str, str]) -> Dict[str, str]:
    """Completar oferta con detalle API (listado activas trae campos mínimos)."""
    codigo = offer.get("codigo_externo", "").strip()
    if not codigo:
        return offer

    detail = _fetch_licitacion_detail_raw(ticket, codigo)
    if not detail:
        return offer

    enriched = map_offer_from_api({**offer, **detail})
    merged = dict(offer)
    for key, value in enriched.items():
        if value:
            merged[key] = value
    return merged


def map_offer_from_api(item: Dict) -> Dict[str, str]:
    """Mapear licitación JSON de la API oficial al esquema interno."""
    codigo = _get_nested(item, ("CodigoExterno",), ("Codigo",), ("codigo_externo",))
    nombre = _get_nested(item, ("Nombre",), ("NombreLicitacion",), ("nombre",))
    descripcion = _get_nested(
        item,
        ("Descripcion",),
        ("DescripcionLicitacion",),
        ("descripcion",),
    )
    descripcion_producto = _resolve_api_producto(item)
    organismo = _get_nested(
        item,
        ("Comprador", "NombreOrganismo"),
        ("Comprador", "NombreUnidad"),
        ("NombreOrganismo",),
        ("organismo",),
    )
    estado = _resolve_api_estado(item)
    region = _get_nested(
        item,
        ("Comprador", "RegionUnidad"),
        ("Comprador", "Region"),
        ("Region",),
        ("region",),
    )
    comuna = _get_nested(
        item,
        ("Comprador", "ComunaUnidad"),
        ("Comprador", "Comuna"),
        ("Comuna",),
        ("comuna",),
    )
    tipo_oferta = _resolve_api_tipo(item)
    moneda = _get_nested(item, ("Moneda",), ("CodigoMoneda",), ("moneda",))
    monto_raw = _get_nested(
        item,
        ("MontoEstimado",),
        ("Monto",),
        ("monto_estimado",),
    )
    fecha_publicacion = _get_nested(
        item,
        ("Fechas", "FechaPublicacion"),
        ("FechaPublicacion",),
        ("Fechas", "FechaCreacion"),
        ("fecha_publicacion",),
    )
    fecha_cierre = _get_nested(
        item,
        ("Fechas", "FechaCierre"),
        ("FechaCierre",),
        ("fecha_cierre",),
    )
    link = _get_nested(item, ("Link",), ("Url",), ("UrlLicitacion",))
    if not link and codigo:
        link = (
            "http://www.mercadopublico.cl/Procurement/Modules/RFB/"
            f"DetailsAcquisition.aspx?idLicitacion={codigo}"
        )

    return {
        "codigo_externo": codigo,
        "nombre": nombre,
        "descripcion": descripcion,
        "descripcion_producto": descripcion_producto,
        "organismo": organismo,
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


def fetch_offers(
    feed_url: str,
    api_ticket: str = "",
    source: str = "auto",
) -> Tuple[List[Dict[str, str]], str]:
    """Descargar ofertas: API en CI, CSV en local (con fallback)."""
    logger = get_logger()
    ticket = (api_ticket or _api_ticket()).strip()
    in_github = os.environ.get("GITHUB_ACTIONS") == "true"
    source = (source or "auto").lower()

    if source not in {"auto", "api", "csv"}:
        raise ValueError(f"source inválido: {source}")

    if source == "csv":
        offers_data, filename = download_csv(feed_url)
        return [map_offer(row) for row in offers_data], filename

    if source == "api":
        if not ticket:
            raise RuntimeError(
                "source=api requiere MERCADO_PUBLICO_API_TICKET o --api-ticket"
            )
        logger.info("Obteniendo ofertas vía API oficial (estado=activas)...")
        return fetch_offers_from_api(ticket), "api:estado=activas"

    if ticket:
        try:
            logger.info("Obteniendo ofertas vía API oficial (estado=activas)...")
            return fetch_offers_from_api(ticket), "api:estado=activas"
        except Exception as exc:
            if in_github:
                raise RuntimeError(f"API Mercado Público falló: {exc}") from exc
            logger.warning("API falló, intentando CSV: %s", exc)

    if in_github:
        raise RuntimeError(_github_actions_csv_blocked_message())

    offers_data, filename = download_csv(feed_url)
    return [map_offer(row) for row in offers_data], filename


def _warmup_portal_session(session) -> None:
    try:
        session.get(f"{MP_PORTAL_ORIGIN}/", timeout=30)
    except requests.RequestException:
        pass


def _download_with_requests(feed_url: str) -> bytes:
    session = requests.Session()
    session.headers.update(MP_BROWSER_HEADERS)
    _warmup_portal_session(session)
    response = session.get(feed_url, timeout=90)
    response.raise_for_status()
    return response.content


def _download_with_curl(feed_url: str) -> bytes:
    cmd = [
        "curl",
        "-fsSL",
        "--max-time",
        "90",
        "-A",
        MP_BROWSER_HEADERS["User-Agent"],
        "-H",
        f"Accept-Language: {MP_BROWSER_HEADERS['Accept-Language']}",
        "-H",
        f"Referer: {MP_BROWSER_HEADERS['Referer']}",
        feed_url,
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"curl exit {proc.returncode}: {stderr}")
    return proc.stdout


def _download_with_curl_cffi(feed_url: str) -> bytes:
    from curl_cffi import requests as curl_requests

    session = curl_requests.Session()
    try:
        session.get(f"{MP_PORTAL_ORIGIN}/", impersonate="chrome120", timeout=30)
    except Exception:
        pass
    response = session.get(feed_url, impersonate="chrome120", timeout=90)
    response.raise_for_status()
    return response.content


def download_feed_bytes(feed_url: str) -> bytes:
    """Descargar bytes del feed probando varias estrategias anti-bloqueo."""
    logger = get_logger()
    strategies: List[Tuple[str, Callable[[str], bytes]]] = [
        ("requests", _download_with_requests),
        ("curl_cffi", _download_with_curl_cffi),
        ("curl", _download_with_curl),
    ]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        strategies = [
            ("curl_cffi", _download_with_curl_cffi),
            ("curl", _download_with_curl),
            ("requests", _download_with_requests),
        ]
    errors: List[str] = []

    for name, strategy in strategies:
        try:
            logger.info("Descargando feed con %s ...", name)
            return strategy(feed_url)
        except Exception as exc:
            logger.warning("Descarga con %s falló: %s", name, exc)
            errors.append(f"{name}: {exc}")

    raise RuntimeError(
        "No se pudo descargar el feed de Mercado Público. Intentos:\n"
        + "\n".join(errors)
        + "\nMercado Público suele bloquear IPs de datacenter (p. ej. GitHub Actions). "
        "Opciones: self-hosted runner, proxy, o API oficial en api.mercadopublico.cl."
    )


def download_csv(feed_url: str) -> Tuple[List[Dict[str, str]], str]:
    """Descargar CSV desde Mercado Público"""
    content = download_feed_bytes(feed_url)

    if content[:2] == b"PK":
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


def _use_google_sheets(local_only: bool) -> bool:
    if local_only:
        return False
    if not os.environ.get("GOOGLE_SHEETS_ID") or not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        raise RuntimeError(
            "Google Sheets no configurado. Para prueba local usa --local-only "
            "o define GOOGLE_SHEETS_ID y GOOGLE_SERVICE_ACCOUNT_JSON en .env"
        )
    return True


def _get_existing_codes(use_sheets: bool) -> set:
    existing_codes = set()
    if use_sheets:
        existing_offers = get_sheet_data("ofertas")
        if existing_offers and len(existing_offers) > 1:
            for row in existing_offers[1:]:
                if row and len(row) > 0:
                    existing_codes.add(str(row[0]).strip())
        return existing_codes

    with get_conn() as conn:
        rows = conn.execute("SELECT codigo_externo FROM offers").fetchall()
        for row in rows:
            if row["codigo_externo"]:
                existing_codes.add(str(row["codigo_externo"]).strip())
    return existing_codes


def _clean_old_offers_local(days: int = 30) -> int:
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM offers WHERE updated_at IS NOT NULL AND updated_at < ?",
            (cutoff_date,),
        )
        conn.commit()
        return cur.rowcount


def update_offers(
    feed_url: str = DEFAULT_FEED_URL,
    api_ticket: str = "",
    local_only: bool = False,
    source: str = "auto",
):
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
        use_sheets = _use_google_sheets(local_only)
        if local_only:
            print("[INFO] Modo local: solo SQLite (sin Google Sheets)")
        
        # Inicializar base de datos (crear tabla si no existe)
        init_db()

        # DESCARGAR OFERTAS (API en GitHub Actions, CSV en local)
        offers_raw, source_name = fetch_offers(
            feed_url,
            api_ticket=api_ticket,
            source=source,
        )
        using_api = source_name.startswith("api")
        active_ticket = (api_ticket or _api_ticket()).strip()

        print(
            f"[INFO] Mercado Público retornó {len(offers_raw)} ofertas desde {source_name}"
        )

        print(f"[INFO] {len(offers_raw)} ofertas mapeadas")

        # OBTENER EXISTENTES
        existing_codes = _get_existing_codes(use_sheets)

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

            if using_api and active_ticket:
                offer = enrich_offer_from_api(active_ticket, offer)
                unique_offers[codigo] = offer
                time.sleep(0.12)

            minimal_raw = {
                "codigo": codigo,
                "producto": offer.get("descripcion_producto"),
            }
            
            # Calcular días restantes hasta cierre
            dias_que_quedan = calculate_days_until_close(offer.get("fecha_cierre", ""))
            fecha_publicacion_sheet = format_date_for_sheet(offer.get("fecha_publicacion", ""))
            fecha_cierre_sheet = format_date_for_sheet(offer.get("fecha_cierre", ""), include_time=True)

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
                fecha_publicacion_sheet,
                fecha_cierre_sheet,
                offer.get("link", ""),
                json.dumps(minimal_raw, ensure_ascii=False),
                now_iso,
                now_iso,
                now_iso,
                dias_que_quedan if dias_que_quedan is not None else "",
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
                offer.get("link", ""),
                json.dumps(minimal_raw, ensure_ascii=False),
                now_iso,
                dias_que_quedan if dias_que_quedan is not None else "",
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

            # Insert to SQLite database (using sqlite_values)
            with get_conn() as conn:
                for item in chunk:
                    sqlite_values = item[1]
                    conn.execute("""
                        INSERT OR REPLACE INTO offers 
                        (codigo_externo, nombre, descripcion, descripcion_producto, organismo, estado, region, 
                         comuna, tipo_oferta, moneda, monto_estimado, fecha_publicacion, 
                         fecha_cierre, link, raw_json, updated_at, dias_que_quedan)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, sqlite_values)
                conn.commit()

            if use_sheets:
                gs_rows = [item[0] for item in chunk]
                append_many_rows("ofertas", gs_rows)
                # evitar quota exceeded
                time.sleep(2)

        # LIMPIAR ANTIGUAS
        if use_sheets:
            stats["deleted_count"] = clean_old_offers()
        else:
            stats["deleted_count"] = _clean_old_offers_local()

        # ALERTAS DESACTIVADAS
        stats["total_matches"] = 0
        stats["total_alerts_sent"] = 0

        # REGISTRAR EJECUCIÓN
        duration = int(time.time() - start_time)

        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if use_sheets:
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

        if not local_only and os.environ.get("GOOGLE_SHEETS_ID") and os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
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
    parser.add_argument(
        "--api-ticket",
        default="",
        help="Ticket API Mercado Público (o usar env MERCADO_PUBLICO_API_TICKET)",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Guardar solo en SQLite local (sin Google Sheets)",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "api", "csv"],
        default="auto",
        help="Fuente de datos: auto (API si hay ticket, si no CSV), api o csv",
    )
    args = parser.parse_args()
    
    try:
        update_offers(
            feed_url=args.feed_url,
            api_ticket=args.api_ticket,
            local_only=args.local_only,
            source=args.source,
        )
    except Exception as e:
        print(f"[FATAL] {str(e)}")
        exit(1)
