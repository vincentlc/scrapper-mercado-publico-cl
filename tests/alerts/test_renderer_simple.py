"""
Pruebas unitarias para el módulo renderer (versión simple).
"""

import pytest
from datetime import datetime
import sys
import os

# Configurar PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.alerts.models import Offer, User, UserFilter
from scripts.alerts.renderer import EmailRenderer


@pytest.fixture
def sample_user():
    return User(
        user_id="usr_001",
        email="test@example.com",
        unsub_token="tok_abc123",
        is_active=True,
    )


@pytest.fixture
def sample_filter():
    return UserFilter(
        filter_id="fil_001",
        user_id="usr_001",
        filter_name="Computadores",
        keyword="computador",
    )


@pytest.fixture
def sample_offers():
    return [
        Offer(
            codigo_externo="001",
            nombre="Compra de Computadores",
            descripcion="Compra de 100 computadores",
            organismo="Ministerio de Educación",
            region="Metropolitana",
            moneda="CLP",
            monto_estimado=100000000.0,
            fecha_cierre="2026-12-31",
            link="http://example.com/offer/001",
        ),
        Offer(
            codigo_externo="002",
            nombre="Mantenimiento de Red",
            moneda="CLP",
            monto_estimado=50000000.0,
            link="http://example.com/offer/002",
        ),
    ]


@pytest.fixture
def renderer():
    return EmailRenderer(base_url="http://localhost:3000")


class TestEmailRenderer:
    def test_render_new_offers_email(self, renderer, sample_user, sample_filter, sample_offers):
        result = renderer.render_new_offers_email(
            user=sample_user,
            filter=sample_filter,
            offers=sample_offers,
            max_offers=10,
        )
        
        assert 'subject' in result
        assert 'html' in result
        assert 'text' in result
        assert "2 nuevas ofertas" in result['subject']
        assert "Computadores" in result['subject']
    
    def test_render_max_offers_limit(self, renderer, sample_user, sample_filter, sample_offers):
        result = renderer.render_new_offers_email(
            user=sample_user,
            filter=sample_filter,
            offers=sample_offers,
            max_offers=1,
        )
        
        assert "1 nuevas ofertas" in result['subject']
        assert "Compra de Computadores" in result['html']
        assert "Mantenimiento de Red" not in result['html']
    
    def test_format_monto(self, renderer):
        assert "1,000,000" in renderer._format_monto(1000000.0, "CLP")
        assert "No especificado" == renderer._format_monto(None)
    
    def test_format_date(self, renderer):
        result = renderer._format_date("2026-06-25T15:30:00")
        assert "/" in result
    
    def test_escape_html(self, renderer):
        html = renderer._generate_offer_html(Offer(
            codigo_externo="001",
            nombre="Test <script>alert('xss')</script>",
        ))
        assert '<script>' not in html
        assert '&lt;script&gt;' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
