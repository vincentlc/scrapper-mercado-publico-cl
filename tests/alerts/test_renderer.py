"""
Pruebas unitarias para el módulo renderer.

Estas pruebas verifican la generación de contenido HTML y texto plano
para emails sin depender de servicios externos.
"""

import pytest
from datetime import datetime
import sys
import os

# Agregar el directorio scripts al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from alerts.models import Offer, User, UserFilter
from alerts.renderer import EmailRenderer


# Fixtures para datos de prueba

@pytest.fixture
def sample_user():
    """Usuario de ejemplo."""
    return User(
        user_id="usr_001",
        email="test@example.com",
        unsub_token="tok_abc123",
        is_active=True,
        created_at=datetime.now().isoformat(),
    )


@pytest.fixture
def sample_filter():
    """Filtro de ejemplo."""
    return UserFilter(
        filter_id="fil_001",
        user_id="usr_001",
        filter_name="Computadores en Santiago",
        keyword="computador",
        region="Metropolitana",
        is_active=True,
    )


@pytest.fixture
def sample_offers():
    """Lista de ofertas de ejemplo."""
    return [
        Offer(
            codigo_externo="001",
            nombre="Compra de Computadores",
            descripcion="Compra de 100 computadores",
            organismo="Ministerio de Educación",
            region="Metropolitana",
            tipo_oferta="Licitación Pública",
            moneda="CLP",
            monto_estimado=100000000.0,
            fecha_cierre=datetime.now().isoformat(),
            link="http://example.com/offer/001",
        ),
        Offer(
            codigo_externo="002",
            nombre="Mantenimiento de Red",
            descripcion="Mantenimiento anual",
            organismo="Ministerio de Educación",
            region="Metropolitana",
            moneda="CLP",
            monto_estimado=50000000.0,
            link="http://example.com/offer/002",
        ),
        Offer(
            codigo_externo="003",
            nombre="Capacitación en TI",
            descripcion="Capacitación para profesionales",
            moneda="CLP",
            monto_estimado=25000000.0,
            link="http://example.com/offer/003",
        ),
    ]


@pytest.fixture
def renderer():
    """Instancia del renderer."""
    return EmailRenderer(base_url="http://localhost:3000")


# Pruebas

class TestEmailRenderer:
    """Pruebas del renderer de emails."""
    
    def test_render_new_offers_email(self, renderer, sample_user, sample_filter, sample_offers):
        """Prueba: renderizar email de nuevas ofertas."""
        result = renderer.render_new_offers_email(
            user=sample_user,
            filter=sample_filter,
            offers=sample_offers,
            max_offers=10,
        )
        
        assert 'subject' in result
        assert 'html' in result
        assert 'text' in result
        
        # Verificar subject
        assert "3 nuevas ofertas" in result['subject']
        assert "Computadores en Santiago" in result['subject']
        
        # Verificar HTML
        assert sample_user.unsub_token in result['html']
        assert "Compra de Computadores" in result['html']
        assert "Mantenimiento de Red" in result['html']
        assert "Capacitación en TI" in result['html']
        
        # Verificar texto plano
        assert "Compra de Computadores" in result['text']
        assert "Mantenimiento de Red" in result['text']
    
    def test_render_max_offers_limit(self, renderer, sample_user, sample_filter, sample_offers):
        """Prueba: limitar a max_offers."""
        result = renderer.render_new_offers_email(
            user=sample_user,
            filter=sample_filter,
            offers=sample_offers,
            max_offers=2,
        )
        
        # Solo deberían aparecer 2 ofertas
        assert "Compra de Computadores" in result['html']
        assert "Mantenimiento de Red" in result['html']
        # La tercera no debería aparecer
        assert "Capacitación en TI" not in result['html']
        
        # Subject debería decir 2 ofertas
        assert "2 nuevas ofertas" in result['subject']
    
    def test_render_empty_offers(self, renderer, sample_user, sample_filter):
        """Prueba: renderizar con lista vacía de ofertas."""
        result = renderer.render_new_offers_email(
            user=sample_user,
            filter=sample_filter,
            offers=[],
            max_offers=10,
        )
        
        assert "0 nuevas ofertas" in result['subject']
    
    def test_render_multiple_filters_email(self, renderer, sample_user, sample_offers):
        """Prueba: renderizar email con múltiples filtros."""
        filter1 = UserFilter(
            filter_id="fil_001",
            user_id="usr_001",
            filter_name="Computadores",
            keyword="computador",
        )
        filter2 = UserFilter(
            filter_id="fil_002",
            user_id="usr_001",
            filter_name="Redes",
            keyword="red",
        )
        
        filter_matches = {
            filter1: [sample_offers[0]],
            filter2: [sample_offers[1]],
        }
        
        result = renderer.render_multiple_filters_email(
            user=sample_user,
            filter_matches=filter_matches,
            max_offers_per_filter=10,
        )
        
        assert 'subject' in result
        assert 'html' in result
        assert 'text' in result
        
        # Debería mencionar ambos filtros
        assert "Computadores" in result['html']
        assert "Redes" in result['html']
    
    def test_unescape_html(self, renderer):
        """Prueba: escape de caracteres HTML."""
        offer = Offer(
            codigo_externo="004",
            nombre="Compra de <script>alert('xss')</script>",
        )
        
        html = renderer._generate_offer_html(offer)
        
        # El script no debería ejecutarse
        assert '<script>' not in html
        assert '&lt;script&gt;' in html
    
    def test_format_monto(self, renderer):
        """Prueba: formateo de monto."""
        # Con moneda
        result = renderer._format_monto(1000000.0, "CLP")
        assert "CLP" in result
        assert "1,000,000" in result
        
        # Sin moneda
        result = renderer._format_monto(1000000.0)
        assert "1,000,000" in result
        
        # None
        result = renderer._format_monto(None)
        assert result == "No especificado"
    
    def test_format_date(self, renderer):
        """Prueba: formateo de fecha."""
        date_str = "2026-06-25T15:30:00"
        result = renderer._format_date(date_str)
        
        # Debería estar en formato dd/mm/yyyy
        assert "/" in result
        assert "2026" in result
    
    def test_format_date_invalid(self, renderer):
        """Prueba: formateo de fecha inválida."""
        result = renderer._format_date("invalid-date")
        assert result == "invalid-date"
    
    def test_format_date_none(self, renderer):
        """Prueba: formateo de fecha None."""
        result = renderer._format_date(None)
        assert result == "No especificado"
    
    def test_create_unsubscribe_page_content(self, renderer, sample_user, sample_filter):
        """Prueba: crear página de gestión de alertas."""
        filters = [sample_filter]
        
        result = renderer.create_unsubscribe_page_content(sample_user, filters)
        
        assert "usr_001" in result
        assert sample_user.unsub_token in result
        assert "Computadores en Santiago" in result
    
    def test_create_unsubscribe_page_empty_filters(self, renderer, sample_user):
        """Prueba: página de gestión con filtros vacíos."""
        result = renderer.create_unsubscribe_page_content(sample_user, [])
        
        assert "No tienes filtros de alerta activos" in result


class TestOfferHtmlGeneration:
    """Pruebas de generación de HTML para ofertas individuales."""
    
    def test_generate_offer_html_complete(self, renderer):
        """Prueba: generar HTML completo para una oferta."""
        offer = Offer(
            codigo_externo="005",
            nombre="Test Offer",
            descripcion="Test description",
            organismo="Test Organismo",
            region="Test Region",
            comuna="Test Comuna",
            tipo_oferta="Test Tipo",
            moneda="CLP",
            monto_estimado=5000000.0,
            fecha_cierre="2026-12-31",
            link="http://example.com/offer/005",
        )
        
        html = renderer._generate_offer_html(offer)
        
        assert "Test Offer" in html
        assert "005" in html
        assert "Test Organismo" in html
        assert "Test Region" in html
        assert "Test Comuna" in html
        assert "Test Tipo" in html
        assert "5,000,000" in html
    
    def test_generate_offer_html_minimal(self, renderer):
        """Prueba: generar HTML con datos mínimos."""
        offer = Offer(
            codigo_externo="006",
            nombre="Minimal Offer",
        )
        
        html = renderer._generate_offer_html(offer)
        
        assert "Minimal Offer" in html
        assert "006" in html
    
    def test_generate_offer_html_no_link(self, renderer):
        """Prueba: generar HTML sin link (debería generar link por defecto)."""
        offer = Offer(
            codigo_externo="007",
            nombre="No Link Offer",
            link=None,
        )
        
        html = renderer._generate_offer_html(offer)
        
        # Debería generar link por defecto a Mercado Público
        assert "mercadopublico.cl" in html


class TestOfferTextGeneration:
    """Pruebas de generación de texto plano para ofertas."""
    
    def test_generate_offer_text_complete(self, renderer):
        """Prueba: generar texto completo para una oferta."""
        offer = Offer(
            codigo_externo="008",
            nombre="Test Offer",
            descripcion="Test description",
            organismo="Test Organismo",
            region="Test Region",
            moneda="CLP",
            monto_estimado=5000000.0,
            link="http://example.com/offer/008",
        )
        
        text = renderer._generate_offer_text(offer)
        
        assert "Test Offer" in text
        assert "008" in text
        assert "Test Organismo" in text
        assert "Test Region" in text
        assert "5,000,000" in text
    
    def test_generate_offer_text_long_description(self, renderer):
        """Prueba: texto con descripción larga (debería truncarse)."""
        long_desc = "a" * 300  # Descripción muy larga
        offer = Offer(
            codigo_externo="009",
            nombre="Long Desc Offer",
            descripcion=long_desc,
        )
        
        text = renderer._generate_offer_text(offer)
        
        # Debería truncarse a 200 caracteres + "..."
        assert "..." in text
        assert len(text) < len(long_desc) + 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
