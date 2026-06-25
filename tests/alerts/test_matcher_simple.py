"""
Pruebas unitarias para el módulo matcher (versión simple).

Estas pruebas verifican la lógica de coincidencia entre ofertas y filtros
sin depender de Google Sheets ni servicios externos.
"""

import pytest
from datetime import datetime
import sys
import os

# Configurar PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.alerts.models import Offer, UserFilter
from scripts.alerts.matcher import OfferMatcher, MatchResult


# Fixtures

@pytest.fixture
def sample_offer():
    return Offer(
        codigo_externo="12345",
        nombre="Compra de Computadores",
        descripcion="Compra de 100 computadores",
        organismo="Ministerio de Educación",
        region="Metropolitana",
    )


@pytest.fixture
def keyword_filter():
    return UserFilter(
        filter_id="fil_001",
        user_id="usr_001",
        filter_name="Computadores",
        keyword="computador",
        is_active=True,
    )


@pytest.fixture
def region_filter():
    return UserFilter(
        filter_id="fil_002",
        user_id="usr_001",
        filter_name="Santiago",
        region="Metropolitana",
        is_active=True,
    )


@pytest.fixture
def matcher():
    return OfferMatcher()


# Pruebas básicas

class TestMatcherBasic:
    def test_match_keyword(self, matcher, sample_offer, keyword_filter):
        result = matcher.match_offer_to_filter(sample_offer, keyword_filter)
        assert result is not None
        assert result.score > 0
        assert 'keyword' in result.matched_fields
    
    def test_match_region(self, matcher, sample_offer, region_filter):
        result = matcher.match_offer_to_filter(sample_offer, region_filter)
        assert result is not None
        assert 'region' in result.matched_fields
    
    def test_no_match_wrong_region(self, matcher, sample_offer):
        filter = UserFilter(
            filter_id="fil_003",
            user_id="usr_001",
            filter_name="Valparaíso",
            region="Valparaíso",
        )
        result = matcher.match_offer_to_filter(sample_offer, filter)
        assert result is None
    
    def test_inactive_filter_no_match(self, matcher, sample_offer, keyword_filter):
        keyword_filter.is_active = False
        result = matcher.match_offer_to_filter(sample_offer, keyword_filter)
        assert result is None
    
    def test_empty_filter_matches_all(self, matcher, sample_offer):
        empty_filter = UserFilter(
            filter_id="fil_004",
            user_id="usr_001",
            filter_name="Todos",
        )
        result = matcher.match_offer_to_filter(sample_offer, empty_filter)
        assert result is not None
        assert result.score == 1.0


class TestMatcherMonto:
    def test_match_monto_in_range(self, matcher):
        offer = Offer(
            codigo_externo="001",
            nombre="Test",
            monto_estimado=10000000.0,
        )
        filter = UserFilter(
            filter_id="fil_005",
            user_id="usr_001",
            filter_name="Monto Test",
            monto_min=5000000.0,
            monto_max=20000000.0,
        )
        result = matcher.match_offer_to_filter(offer, filter)
        assert result is not None
        assert 'monto' in result.matched_fields
    
    def test_no_match_below_min(self, matcher):
        offer = Offer(
            codigo_externo="002",
            nombre="Test",
            monto_estimado=1000000.0,
        )
        filter = UserFilter(
            filter_id="fil_006",
            user_id="usr_001",
            filter_name="Monto Min",
            monto_min=5000000.0,
        )
        result = matcher.match_offer_to_filter(offer, filter)
        assert result is None
    
    def test_no_match_above_max(self, matcher):
        offer = Offer(
            codigo_externo="003",
            nombre="Test",
            monto_estimado=100000000.0,
        )
        filter = UserFilter(
            filter_id="fil_007",
            user_id="usr_001",
            filter_name="Monto Max",
            monto_max=50000000.0,
        )
        result = matcher.match_offer_to_filter(offer, filter)
        assert result is None


class TestMatcherNormalization:
    def test_case_insensitive(self, matcher):
        offer = Offer(codigo_externo="004", nombre="COMPUTADOR")
        filter = UserFilter(filter_id="fil_008", user_id="usr_001", filter_name="Test", keyword="computador")
        result = matcher.match_offer_to_filter(offer, filter)
        assert result is not None
    
    def test_accent_insensitive(self, matcher):
        offer = Offer(codigo_externo="005", nombre="Computación")
        filter = UserFilter(filter_id="fil_009", user_id="usr_001", filter_name="Test", keyword="computacion")
        result = matcher.match_offer_to_filter(offer, filter)
        assert result is not None
    
    def test_parse_monto_with_dots(self, matcher):
        monto = matcher._parse_monto("1.000.000")
        assert monto == 1000000.0
    
    def test_parse_monto_with_comma(self, matcher):
        monto = matcher._parse_monto("1.000.000,50")
        assert monto == 1000000.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
