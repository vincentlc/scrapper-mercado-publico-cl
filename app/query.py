from typing import Dict, List, Optional, Tuple
from datetime import datetime


def is_less_than_100_utm(tipo_oferta: str) -> bool:
    """Verificar si una licitación es <100 UTM"""
    if not tipo_oferta:
        return False
    tipo_lower = tipo_oferta.lower()
    return "inferior a 100 utm" in tipo_lower


def format_tipo_oferta(tipo_oferta: str) -> str:
    """Formatear tipo de oferta agregando (compra ágil) si es <100 UTM"""
    if not tipo_oferta:
        return ""
    
    if is_less_than_100_utm(tipo_oferta):
        # Si ya tiene "(compra ágil)", no duplicar
        if "(compra ágil)" in tipo_oferta.lower():
            return tipo_oferta
        return f"{tipo_oferta} (compra ágil)"
    
    return tipo_oferta


def calculate_days_until_close(fecha_cierre: str) -> Optional[int]:
    """Calcular días restantes hasta cierre de la licitación"""
    if not fecha_cierre:
        return None
    
    try:
        # Soporta formatos ISO, datetime con o sin hora, y DD/MM/YYYY
        close_date = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",  # ISO with T separator
            "%Y-%m-%d %H:%M:%S",  # ISO with space separator
            "%Y-%m-%d",           # ISO date only
            "%d/%m/%Y %H:%M:%S",  # DD/MM/YYYY with time
            "%d/%m/%Y",           # DD/MM/YYYY only
        ]:
            try:
                close_date = datetime.strptime(fecha_cierre[:19], fmt)
                break
            except ValueError:
                continue
        
        if not close_date:
            return None
        
        now = datetime.now()
        delta = close_date - now
        days = delta.days
        
        # Si falta menos de 1 día pero aún no cerró, mostrar 0
        if days < 0:
            return None  # Ya cerró
        return max(0, days)
    except Exception:
        return None


MP_OFFER_LINK_TEMPLATE = (
    "http://www.mercadopublico.cl/Procurement/Modules/RFB/"
    "DetailsAcquisition.aspx?idLicitacion={codigo}"
)


def normalize_offer_link(item: Dict[str, object]) -> None:
    """Asegurar link HTTP válido; reparar filas con fecha en columna link."""
    codigo = str(item.get("codigo_externo") or "").strip()
    link = str(item.get("link") or "").strip()
    fecha_cierre = str(item.get("fecha_cierre") or "").strip()

    if link.startswith(("http://", "https://")):
        return

    if link and not fecha_cierre and ("T" in link or link[:4].isdigit()):
        item["fecha_cierre"] = link
        fecha_cierre = link

    if codigo:
        item["link"] = MP_OFFER_LINK_TEMPLATE.format(codigo=codigo)
    else:
        item["link"] = ""


def build_offer_filters(
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
) -> Tuple[str, List[object]]:
    where: List[str] = []
    args: List[object] = []

    if keyword:
        where.append(
            "(nombre LIKE ? OR descripcion LIKE ? OR descripcion_producto LIKE ? OR codigo_externo LIKE ?)"
        )
        pattern = f"%{keyword}%"
        args.extend([pattern, pattern, pattern, pattern])

    for col, value in (
        ("tipo_oferta", tipo_oferta),
        ("estado", estado),
        ("organismo", organismo),
        ("region", region),
        ("comuna", comuna),
    ):
        if value:
            where.append(f"LOWER(TRIM(COALESCE({col}, ''))) = LOWER(TRIM(?))")
            args.append(value)

    if utm_range:
        if utm_range == "lt100":
            where.append("LOWER(tipo_oferta) LIKE '%inferior a 100 utm%'")
        elif utm_range == "100_1000":
            where.append("LOWER(tipo_oferta) LIKE '%igual o superior a 100 utm%'")
        elif utm_range == "1000_2000":
            where.append("LOWER(tipo_oferta) LIKE '%igual o superior a 1.000 utm%'")
        elif utm_range == "2000_5000":
            where.append(
                "(LOWER(tipo_oferta) LIKE '%igual o superior a 2.000 utm%' OR LOWER(tipo_oferta) LIKE '%igual o superior a 2000 utm%')"
            )
        elif utm_range == "gt5000":
            where.append("LOWER(tipo_oferta) LIKE '%mayor a 5000 utm%'")

    if min_monto is not None:
        where.append("monto_estimado >= ?")
        args.append(min_monto)
    if max_monto is not None:
        where.append("monto_estimado <= ?")
        args.append(max_monto)
    if start_date:
        where.append("fecha_publicacion >= ?")
        args.append(start_date)
    if end_date:
        where.append("fecha_publicacion <= ?")
        args.append(end_date)
    if start_close_date:
        where.append("fecha_cierre >= ?")
        args.append(start_close_date)
    if end_close_date:
        where.append("fecha_cierre <= ?")
        args.append(end_close_date)
    
    # Filtros por días restantes para cierre
    # Usa DATETIME para calcular la diferencia
    if min_days_to_close is not None:
        # fecha_cierre debe estar al menos min_days_to_close días en el futuro
        # datetime('now', '+X days') retorna la fecha en X días
        where.append("fecha_cierre > datetime('now', ? || ' days')")
        args.append(min_days_to_close - 1)  # -1 porque queremos >= min_days
    
    if max_days_to_close is not None:
        # fecha_cierre debe estar como máximo max_days_to_close días en el futuro
        # Esto significa: cierre <= hoy + max_days
        where.append("fecha_cierre <= datetime('now', ? || ' days')")
        args.append(max_days_to_close)

    return (" AND ".join(where) if where else "1=1"), args


def normalize_option_values(rows: List[Dict[str, object]]) -> List[str]:
    return sorted({str(r["value"]).strip() for r in rows if str(r["value"]).strip()})
