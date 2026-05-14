from typing import Dict, List, Optional, Tuple


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

    return (" AND ".join(where) if where else "1=1"), args


def normalize_option_values(rows: List[Dict[str, object]]) -> List[str]:
    return sorted({str(r["value"]).strip() for r in rows if str(r["value"]).strip()})
