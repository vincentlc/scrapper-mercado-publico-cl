"""
Matcher para el sistema de alertas.

Este módulo implementa la lógica de coincidencia entre ofertas nuevas y filtros
de usuarios. Es completamente independiente del backend de almacenamiento,
lo que lo hace fácilmente testeable.

La lógica de matching soporta:
- Coincidencia por palabra clave (en nombre, descripción, producto)
- Filtro por región
- Filtro por comuna
- Filtro por organismo
- Filtro por tipo de oferta
- Filtro por estado
- Filtro por rango de monto (min/max)
- Filtro por moneda
- Filtro por rango UTM
"""

import re
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

from scripts.alerts.models import UserFilter, Offer


@dataclass
class MatchResult:
    """Resultado de una coincidencia."""
    filter: UserFilter
    offer: Offer
    score: float  # Puntuación de coincidencia (0-1)
    matched_fields: List[str]  # Lista de campos que coincidieron
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'filter_id': self.filter.filter_id,
            'user_id': self.filter.user_id,
            'filter_name': self.filter.filter_name,
            'offer_code': self.offer.codigo_externo,
            'offer_name': self.offer.nombre,
            'score': self.score,
            'matched_fields': self.matched_fields,
        }


class OfferMatcher:
    """
    Clase para hacer matching entre ofertas y filtros de usuarios.
    
    Esta clase es independiente del backend y puede ser testeada con datos mock.
    """
    
    def __init__(self):
        """Inicializar el matcher."""
        self._normalizers = {
            'keyword': self._normalize_text,
            'region': self._normalize_text,
            'comuna': self._normalize_text,
            'organismo': self._normalize_text,
            'tipo_oferta': self._normalize_text,
            'estado': self._normalize_text,
            'moneda': self._normalize_text,
            'descripcion': self._normalize_text,
            'descripcion_producto': self._normalize_text,
        }
    
    @staticmethod
    def _normalize_text(text: Optional[str]) -> str:
        """Normalizar texto para comparación (lowercase, sin acentos, sin espacios extra)."""
        if not text:
            return ''
        text = text.strip().lower()
        # Remover acentos
        text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        text = text.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        text = text.replace('Á', 'A').replace('É', 'E').replace('Í', 'I')
        text = text.replace('Ó', 'O').replace('Ú', 'U').replace('Ñ', 'N')
        return re.sub(r'\s+', ' ', text)
    
    def _parse_monto(self, monto: Optional[str]) -> Optional[float]:
        """Parsear monto a float."""
        if not monto:
            return None
        try:
            # Si ya es un float, devolverlo directamente
            if isinstance(monto, (int, float)):
                return float(monto)
            
            # Si es un string, procesarlo
            monto_str = str(monto).strip()
            
            # Contar puntos para determinar formato
            point_count = monto_str.count('.')
            comma_count = monto_str.count(',')
            
            # Si hay más de un punto, asumir que son separadores de miles
            if point_count > 1:
                # Remover todos los puntos (separadores de miles)
                cleaned = monto_str.replace('.', '').replace(',', '.')
            # Si hay una coma, asumir formato europeo (1.000.000,50)
            elif comma_count >= 1:
                # Remover puntos (separadores de miles) y mantener coma como decimal
                cleaned = monto_str.replace('.', '')
            # Si hay un solo punto, puede ser decimal o separador de miles
            # Asumimos que es decimal si está en posición esperada
            else:
                # Probar de parsear directamente
                try:
                    return float(monto_str)
                except ValueError:
                    # Si falla, remover el punto (era separador de miles)
                    cleaned = monto_str.replace('.', '').replace(',', '.')
            
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _parse_utm_range(self, utm_range: Optional[str]) -> Optional[tuple]:
        """
        Parsear rango UTM.
        
        Ejemplos: "1-100", "100-1000", ">1000"
        Retorna: (min, max) o None
        """
        if not utm_range:
            return None
        
        utm_range = utm_range.strip().lower()
        
        if utm_range == '<100' or utm_range == 'menor a 100 utm':
            return (0, 100)
        elif utm_range == '100-1000' or utm_range == 'entre 100 y 1000 utm':
            return (100, 1000)
        elif utm_range == '>1000' or utm_range == 'mayor a 1000 utm':
            return (1000, None)
        
        # Intentar parsear rango numérico
        match = re.match(r'([\d,]+)\-([\d,]+)', utm_range)
        if match:
            min_val = self._parse_monto(match.group(1))
            max_val = self._parse_monto(match.group(2))
            if min_val is not None and max_val is not None:
                return (min_val, max_val)
        
        # Intentar parsear ">N"
        match = re.match(r'[>\s]*([\d,]+)', utm_range)
        if match:
            min_val = self._parse_monto(match.group(1))
            if min_val is not None:
                return (min_val, None)
        
        return None
    
    def _match_keyword(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """
        Verificar si la oferta coincide con la palabra clave del filtro.
        
        Busca la palabra clave en:
        - Nombre de la oferta
        - Descripción
        - Descripción del producto
        
        Retorna: puntuación (0.0 a 1.0) si coincide, None si no
        """
        if not filter.keyword:
            return None
        
        keyword = self._normalize_text(filter.keyword)
        if not keyword:
            return None
        
        # Buscar en múltiples campos
        fields_to_check = [
            offer.nombre,
            offer.descripcion,
            offer.descripcion_producto,
        ]
        
        score = 0.0
        matches = []
        
        for field in fields_to_check:
            if field:
                normalized_field = self._normalize_text(field)
                if keyword in normalized_field:
                    # Puntuación más alta si está en el nombre
                    if field == offer.nombre:
                        score += 0.5
                        matches.append('nombre')
                    elif field == offer.descripcion:
                        score += 0.3
                        matches.append('descripcion')
                    else:
                        score += 0.2
                        matches.append('descripcion_producto')
        
        if score > 0:
            # Normalizar a 0-1
            return min(score / 0.5, 1.0)  # Cap at 1.0
        
        return None
    
    def _match_region(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con la región del filtro."""
        if not filter.region:
            return None
        
        filter_region = self._normalize_text(filter.region)
        offer_region = self._normalize_text(offer.region)
        
        if filter_region and offer_region and filter_region in offer_region:
            return 1.0
        
        return None
    
    def _match_comuna(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con la comuna del filtro."""
        if not filter.comuna:
            return None
        
        filter_comuna = self._normalize_text(filter.comuna)
        offer_comuna = self._normalize_text(offer.comuna)
        
        if filter_comuna and offer_comuna and filter_comuna in offer_comuna:
            return 1.0
        
        return None
    
    def _match_organismo(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con el organismo del filtro."""
        if not filter.organismo:
            return None
        
        filter_organismo = self._normalize_text(filter.organismo)
        offer_organismo = self._normalize_text(offer.organismo)
        
        if filter_organismo and offer_organismo and filter_organismo in offer_organismo:
            return 1.0
        
        return None
    
    def _match_tipo_oferta(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con el tipo de oferta del filtro."""
        if not filter.tipo_oferta:
            return None
        
        filter_tipo = self._normalize_text(filter.tipo_oferta)
        offer_tipo = self._normalize_text(offer.tipo_oferta)
        
        if filter_tipo and offer_tipo and filter_tipo in offer_tipo:
            return 1.0
        
        return None
    
    def _match_estado(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con el estado del filtro."""
        if not filter.estado:
            return None
        
        filter_estado = self._normalize_text(filter.estado)
        offer_estado = self._normalize_text(offer.estado)
        
        if filter_estado and offer_estado and filter_estado in offer_estado:
            return 1.0
        
        return None
    
    def _match_monto(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si el monto de la oferta está dentro del rango del filtro."""
        # Verificar si el filtro tiene algún criterio de monto
        if filter.monto_min is None and filter.monto_max is None:
            return None
        
        if offer.monto_estimado is None:
            return None
        
        # Parsear monto de la oferta
        offer_monto = self._parse_monto(str(offer.monto_estimado))
        if offer_monto is None:
            return None
        
        # Verificar monto mínimo
        if filter.monto_min is not None:
            if offer_monto < filter.monto_min:
                return None
        
        # Verificar monto máximo
        if filter.monto_max is not None:
            if offer_monto > filter.monto_max:
                return None
        
        # Si pasa ambos filtros, coincide
        return 1.0
    
    def _match_moneda(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la moneda de la oferta coincide con el filtro."""
        if not filter.moneda:
            return None
        
        filter_moneda = self._normalize_text(filter.moneda)
        offer_moneda = self._normalize_text(offer.moneda)
        
        if filter_moneda and offer_moneda and filter_moneda == offer_moneda:
            return 1.0
        
        return None
    
    def _match_utm_range(self, filter: UserFilter, offer: Offer) -> Optional[float]:
        """Verificar si la oferta coincide con el rango UTM del filtro."""
        if not filter.utm_range:
            return None
        
        # Parsear rango UTM del filtro
        utm_range = self._parse_utm_range(filter.utm_range)
        if utm_range is None:
            return None
        
        min_utm, max_utm = utm_range
        
        # Obtener monto de la oferta
        if offer.monto_estimado is None:
            return None
        
        offer_monto = self._parse_monto(str(offer.monto_estimado))
        if offer_monto is None:
            return None
        
        # Verificar si el monto está en el rango
        if min_utm is not None and offer_monto < min_utm:
            return None
        if max_utm is not None and offer_monto > max_utm:
            return None
        
        return 1.0
    
    def match_offer_to_filter(self, offer: Offer, filter: UserFilter) -> Optional[MatchResult]:
        """
        Verificar si una oferta coincide con un filtro.
        
        Args:
            offer: La oferta a verificar
            filter: El filtro del usuario
        
        Returns:
            MatchResult si coincide, None si no
        """
        # Si el filtro está inactivo, no coincide
        if not filter.is_active:
            return None
        
        # Lista de todos los matchers a aplicar
        matchers = [
            ('keyword', self._match_keyword),
            ('region', self._match_region),
            ('comuna', self._match_comuna),
            ('organismo', self._match_organismo),
            ('tipo_oferta', self._match_tipo_oferta),
            ('estado', self._match_estado),
            ('monto', self._match_monto),
            ('moneda', self._match_moneda),
            ('utm_range', self._match_utm_range),
        ]
        
        matched_fields = []
        total_score = 0.0
        active_filters = 0
        
        for field_name, matcher_func in matchers:
            # Verificar si este campo está definido en el filtro
            field_value = getattr(filter, field_name, None)
            
            # Para monto, verificar explícitamente si no es None
            if field_name == 'monto':
                has_monto_filter = (filter.monto_min is not None or filter.monto_max is not None)
                if has_monto_filter:
                    active_filters += 1
                    result = matcher_func(filter, offer)
                    if result is not None:
                        matched_fields.append(field_name)
                        total_score += result
            # Para utm_range, verificar si no es None ni vacío
            elif field_name == 'utm_range':
                if filter.utm_range is not None and filter.utm_range != '':
                    active_filters += 1
                    result = matcher_func(filter, offer)
                    if result is not None:
                        matched_fields.append(field_name)
                        total_score += result
            # Para otros campos, verificar si no es None ni vacío
            elif field_value is not None and field_value != '':
                active_filters += 1
                result = matcher_func(filter, offer)
                if result is not None:
                    matched_fields.append(field_name)
                    total_score += result
        
        # Si no hay filtros activos, considerar como coincidencia
        if active_filters == 0:
            return MatchResult(
                filter=filter,
                offer=offer,
                score=1.0,
                matched_fields=['all'],
            )
        
        # Calcular puntuación final (promedio de todos los matchers aplicados)
        if total_score > 0:
            # La puntuación es la suma de todos los matchers
            return MatchResult(
                filter=filter,
                offer=offer,
                score=min(total_score / active_filters, 1.0),  # Normalizar
                matched_fields=matched_fields,
            )
        
        return None
    
    def match_offers_to_filters(
        self, 
        offers: List[Offer], 
        filters: List[UserFilter]
    ) -> List[MatchResult]:
        """
        Encontrar todas las coincidencias entre una lista de ofertas y filtros.
        
        Args:
            offers: Lista de ofertas a verificar
            filters: Lista de filtros de usuarios
        
        Returns:
            Lista de MatchResult con todas las coincidencias
        """
        results = []
        
        for offer in offers:
            for filter in filters:
                match_result = self.match_offer_to_filter(offer, filter)
                if match_result:
                    results.append(match_result)
        
        return results
    
    def get_matches_for_offer(
        self, 
        offer: Offer, 
        filters: List[UserFilter]
    ) -> List[MatchResult]:
        """
        Obtener todas las coincidencias para una oferta específica.
        
        Args:
            offer: La oferta a verificar
            filters: Lista de filtros de usuarios
        
        Returns:
            Lista de MatchResult para esta oferta
        """
        return [
            match for match in self.match_offers_to_filters([offer], filters)
            if match is not None
        ]
    
    def get_matches_for_filter(
        self, 
        filter: UserFilter, 
        offers: List[Offer]
    ) -> List[MatchResult]:
        """
        Obtener todas las coincidencias para un filtro específico.
        
        Args:
            filter: El filtro a verificar
            offers: Lista de ofertas
        
        Returns:
            Lista de MatchResult para este filtro
        """
        return [
            match for match in self.match_offers_to_filters(offers, [filter])
            if match is not None
        ]


# Instancia global por defecto
_default_matcher: Optional[OfferMatcher] = None


def get_matcher() -> OfferMatcher:
    """Obtener una instancia del matcher."""
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = OfferMatcher()
    return _default_matcher
