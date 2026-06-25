"""
Renderer para el sistema de alertas.

Este módulo es responsable de generar el contenido HTML y texto plano
para los emails de alerta. Es completamente independiente del backend
y puede ser testeado sin dependencias externas.
"""

from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass
from datetime import datetime

from scripts.alerts.models import Offer, User, UserFilter


# Protocolo para el renderer (permite inyección de dependencias para testing)
class TemplateRenderer(Protocol):
    """Interfaz para el renderer de plantillas."""
    
    def render_new_offers_email(
        self,
        user: User,
        filter: UserFilter,
        offers: List[Offer],
        unsub_url: str,
        max_offers: int = 10,
    ) -> Dict[str, str]:
        """Renderizar email de nuevas ofertas."""
        ...
    
    def render_summary_email(
        self,
        user: User,
        filters: List[UserFilter],
        matches_count: int,
        unsub_url: str,
    ) -> Dict[str, str]:
        """Renderizar email de resumen."""
        ...


@dataclass
class EmailTemplate:
    """Definición de una plantilla de email."""
    subject_template: str
    html_template: str
    text_template: str


class EmailRenderer:
    """
    Renderer de emails para el sistema de alertas.
    
    Genera contenido HTML y texto plano para emails de alerta.
    """
    
    # Plantilla HTML para email de nuevas ofertas
    NEW_OFFERS_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nuevas Ofertas - {filter_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: #fff;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 2px solid #0066cc;
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #0066cc;
            margin: 0;
            font-size: 24px;
        }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .offer {{
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
            background-color: #fff;
        }}
        .offer:hover {{
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .offer h3 {{
            margin: 0 0 8px 0;
            color: #0066cc;
            font-size: 16px;
        }}
        .offer .code {{
            display: inline-block;
            background-color: #f0f0f0;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .offer .detail {{
            margin: 4px 0;
            font-size: 14px;
        }}
        .offer .detail strong {{
            color: #555;
        }}
        .offer .link {{
            display: inline-block;
            margin-top: 8px;
            padding: 8px 16px;
            background-color: #0066cc;
            color: #fff !important;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }}
        .offer .link:hover {{
            background-color: #0052a3;
        }}
        .footer {{
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #999;
            text-align: center;
        }}
        .unsubscribe {{
            margin-top: 16px;
            font-size: 12px;
            color: #999;
            text-align: center;
        }}
        .unsubscribe a {{
            color: #999;
            text-decoration: underline;
        }}
        .count {{
            background-color: #0066cc;
            color: #fff;
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            margin-bottom: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Nuevas Ofertas de Mercado Público</h1>
        </div>
        
        <div class="meta">
            <strong>Filtro:</strong> {filter_name}<br>
            <strong>Fecha:</strong> {date}
        </div>
        
        <div class="count">
            {offers_count} nuevas ofertas que coinciden con tu filtro
        </div>
        
        {offers_html}
        
        <div class="footer">
            <p>ScrapMercadoPublico - Sistema de Alertas Automáticas</p>
        </div>
        
        <div class="unsubscribe">
            <p>¿No deseas recibir más alertas para este filtro? 
            <a href="{unsub_url}">Desuscribirse</a></p>
            <p><small>O visita <a href="{manage_url}">tu página de gestión de alertas</a> para administrar todas tus alertas.</small></p>
        </div>
    </div>
</body>
</html>
"""

    # Plantilla de texto plano
    NEW_OFFERS_TEXT_TEMPLATE = """Nuevas Ofertas de Mercado Público

Filtro: {filter_name}
Fecha: {date}

{offers_count} nuevas ofertas que coinciden con tu filtro:

{offers_text}

---
ScrapMercadoPublico - Sistema de Alertas Automáticas

¿No deseas recibir más alertas? Desuscríbete aquí: {unsub_url}
O visita {manage_url} para administrar todas tus alertas.
"""

    def __init__(self, base_url: str = "https://scrapper-mercado-publico-cl.vercel.app"):
        """
        Inicializar el renderer.
        
        Args:
            base_url: URL base para enlaces de desuscripción y gestión
        """
        self.base_url = base_url.rstrip('/')
    
    def _escape_html(self, text: str) -> str:
        """Escapar caracteres HTML."""
        if not text:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    def _format_monto(self, monto: Optional[float], moneda: Optional[str] = None) -> str:
        """Formatear monto para display."""
        if monto is None:
            return 'No especificado'
        
        # Formatear con separadores de miles
        monto_str = f"{monto:,.0f}"
        if moneda:
            return f"{moneda} {monto_str}"
        return monto_str
    
    def _format_date(self, date_str: Optional[str]) -> str:
        """Formatear fecha para display."""
        if not date_str:
            return 'No especificado'
        
        try:
            # Intentar parsear ISO date
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        except:
            return date_str
    
    def _generate_offer_html(self, offer: Offer) -> str:
        """Generar HTML para una oferta individual."""
        link = offer.link or f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion={offer.codigo_externo}"
        
        html = f'''<div class="offer">
            <h3>{self._escape_html(offer.nombre)}</h3>
            <span class="code">{self._escape_html(offer.codigo_externo)}</span>
            '''
        
        if offer.organismo:
            html += f'<div class="detail"><strong>Organismo:</strong> {self._escape_html(offer.organismo)}</div>'
        
        if offer.region:
            html += f'<div class="detail"><strong>Región:</strong> {self._escape_html(offer.region)}</div>'
        
        if offer.comuna:
            html += f'<div class="detail"><strong>Comuna:</strong> {self._escape_html(offer.comuna)}</div>'
        
        if offer.tipo_oferta:
            html += f'<div class="detail"><strong>Tipo:</strong> {self._escape_html(offer.tipo_oferta)}</div>'
        
        if offer.monto_estimado is not None:
            html += f'<div class="detail"><strong>Monto Estimado:</strong> {self._format_monto(offer.monto_estimado, offer.moneda)}</div>'
        
        if offer.fecha_cierre:
            html += f'<div class="detail"><strong>Fecha de Cierre:</strong> {self._format_date(offer.fecha_cierre)}</div>'
        
        if offer.descripcion:
            desc = offer.descripcion[:200] + '...' if len(offer.descripcion) > 200 else offer.descripcion
            html += f'<div class="detail"><strong>Descripción:</strong> {self._escape_html(desc)}</div>'
        
        html += f'<a href="{self._escape_html(link)}" class="link" target="_blank" rel="noopener noreferrer">Ver en Mercado Público →</a>'
        html += '</div>'
        
        return html
    
    def _generate_offer_text(self, offer: Offer) -> str:
        """Generar texto plano para una oferta individual."""
        link = offer.link or f"http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion={offer.codigo_externo}"
        
        text = f"\n\n--- Oferta: {offer.nombre} ---\n"
        text += f"Código: {offer.codigo_externo}\n"
        
        if offer.organismo:
            text += f"Organismo: {offer.organismo}\n"
        
        if offer.region:
            text += f"Región: {offer.region}\n"
        
        if offer.comuna:
            text += f"Comuna: {offer.comuna}\n"
        
        if offer.tipo_oferta:
            text += f"Tipo: {offer.tipo_oferta}\n"
        
        if offer.monto_estimado is not None:
            text += f"Monto: {self._format_monto(offer.monto_estimado, offer.moneda)}\n"
        
        if offer.fecha_cierre:
            text += f"Cierre: {self._format_date(offer.fecha_cierre)}\n"
        
        if offer.descripcion:
            desc = offer.descripcion[:200] + '...' if len(offer.descripcion) > 200 else offer.descripcion
            text += f"Descripción: {desc}\n"
        
        text += f"Enlace: {link}\n"
        
        return text
    
    def render_new_offers_email(
        self,
        user: User,
        filter: UserFilter,
        offers: List[Offer],
        max_offers: int = 10,
    ) -> Dict[str, str]:
        """
        Renderizar email de nuevas ofertas.
        
        Args:
            user: Usuario destinatario
            filter: Filtro que generó las coincidencias
            offers: Lista de ofertas que coincidieron
            max_offers: Máximo número de ofertas a incluir (default: 10)
        
        Returns:
            Dict con keys 'subject', 'html', 'text'
        """
        # Limitar a max_offers
        offers = offers[:max_offers]
        offers_count = len(offers)
        total_matches = len(offers)  # Podría ser más si hay más coincidencias
        
        # Generar HTML de las ofertas
        offers_html = ''
        for offer in offers:
            offers_html += self._generate_offer_html(offer)
        
        # Generar texto de las ofertas
        offers_text = ''
        for offer in offers:
            offers_text += self._generate_offer_text(offer)
        
        # URL de desuscripción (usar el token del usuario)
        unsub_url = f"{self.base_url}/api/unsubscribe?token={user.unsub_token}"
        manage_url = f"{self.base_url}/alerts?token={user.unsub_token}"
        
        # Formatear fecha
        date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Subject
        subject = f"📧 {offers_count} nuevas ofertas para: {filter.filter_name}"
        
        # HTML
        html = self.NEW_OFFERS_HTML_TEMPLATE.format(
            filter_name=self._escape_html(filter.filter_name),
            date=date,
            offers_count=offers_count,
            offers_html=offers_html,
            unsub_url=unsub_url,
            manage_url=manage_url,
        )
        
        # Text
        text = self.NEW_OFFERS_TEXT_TEMPLATE.format(
            filter_name=filter.filter_name,
            date=date,
            offers_count=offers_count,
            offers_text=offers_text,
            unsub_url=unsub_url,
            manage_url=manage_url,
        )
        
        return {
            'subject': subject,
            'html': html,
            'text': text,
        }
    
    def render_multiple_filters_email(
        self,
        user: User,
        filter_matches: Dict[UserFilter, List[Offer]],
        max_offers_per_filter: int = 10,
    ) -> Dict[str, str]:
        """
        Renderizar email con múltiples filtros.
        
        Agrupa las ofertas por filtro y genera un email consolidado.
        
        Args:
            user: Usuario destinatario
            filter_matches: Diccionario {filtro: [ofertas]}
            max_offers_per_filter: Máximo de ofertas por filtro
        
        Returns:
            Dict con keys 'subject', 'html', 'text'
        """
        total_offers = sum(len(offers) for offers in filter_matches.values())
        
        # Generar HTML
        html_parts = []
        text_parts = []
        
        for filter, offers in filter_matches.items():
            offers = offers[:max_offers_per_filter]
            
            if not offers:
                continue
            
            # Header para este filtro
            html_parts.append(f'<h2 style="color: #0066cc; margin-top: 24px; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px;">📌 {self._escape_html(filter.filter_name)}</h2>')
            html_parts.append(f'<p><small>{len(offers)} ofertas que coinciden</small></p>')
            
            for offer in offers:
                html_parts.append(self._generate_offer_html(offer))
            
            # Text
            text_parts.append(f"\n\n=== Filtro: {filter.filter_name} ===")
            text_parts.append(f"({len(offers)} ofertas)")
            for offer in offers:
                text_parts.append(self._generate_offer_text(offer))
        
        # Subject
        subject = f"📧 {total_offers} nuevas ofertas en tus alertas"
        
        # URL de desuscripción
        unsub_url = f"{self.base_url}/api/unsubscribe?token={user.unsub_token}"
        manage_url = f"{self.base_url}/alerts?token={user.unsub_token}"
        date = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # HTML completo
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Nuevas Ofertas - ScrapMercadoPublico</title>
</head>
<body>
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
        <div style="background-color: #fff; border-radius: 8px; padding: 24px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="border-bottom: 2px solid #0066cc; padding-bottom: 16px; margin-bottom: 20px;">
                <h1 style="color: #0066cc; margin: 0; font-size: 24px;">📧 Nuevas Ofertas de Mercado Público</h1>
            </div>
            
            <div style="color: #666; font-size: 14px; margin-bottom: 20px;">
                <strong>Fecha:</strong> {date}<br>
                <strong>Total de ofertas:</strong> {total_offers}
            </div>
            
            {''.join(html_parts)}
            
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #999; text-align: center;">
                <p>ScrapMercadoPublico - Sistema de Alertas Automáticas</p>
            </div>
            
            <div style="margin-top: 16px; font-size: 12px; color: #999; text-align: center;">
                <p>¿No deseas recibir más alertas? 
                <a href="{unsub_url}" style="color: #999; text-decoration: underline;">Desuscribirse</a></p>
                <p><small>O visita <a href="{manage_url}" style="color: #999; text-decoration: underline;">tu página de gestión de alertas</a> para administrar todas tus alertas.</small></p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        # Text completo
        text = f"""Nuevas Ofertas de Mercado Público

Fecha: {date}
Total de ofertas: {total_offers}

{''.join(text_parts)}

---
ScrapMercadoPublico - Sistema de Alertas Automáticas

¿No deseas recibir más alertas? Desuscríbete aquí: {unsub_url}
O visita {manage_url} para administrar todas tus alertas.
"""
        
        return {
            'subject': subject,
            'html': html,
            'text': text,
        }
    
    def create_unsubscribe_page_content(
        self,
        user: User,
        filters: List[UserFilter],
    ) -> str:
        """
        Crear contenido HTML para la página de gestión de alertas.
        
        Esta página muestra todas las alertas del usuario y permite desuscribirse.
        
        Args:
            user: Usuario
            filters: Lista de filtros del usuario
        
        Returns:
            HTML completo de la página
        """
        filters_html = ''
        for filter in filters:
            filters_html += f'''
            <div style="border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0 0 8px 0; color: #0066cc;">{self._escape_html(filter.filter_name)}</h3>
                        <p style="margin: 0; color: #666; font-size: 14px;">
                            {' | '.join([
                                f'Región: {filter.region}' if filter.region else '',
                                f'Keyword: {filter.keyword}' if filter.keyword else '',
                                f'Tipo: {filter.tipo_oferta}' if filter.tipo_oferta else '',
                            ])}
                        </p>
                    </div>
                    <a href="{self.base_url}/api/unsubscribe?token={user.unsub_token}&filter_id={filter.filter_id}" 
                       style="background-color: #dc3545; color: #fff; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-size: 14px;"
                       onclick="return confirm('¿Estás seguro de que quieres eliminar este filtro?')">
                        Eliminar
                    </a>
                </div>
            </div>
            '''
        
        # Si no hay filtros
        if not filters:
            filters_html = '<p style="color: #999; text-align: center;">No tienes filtros de alerta activos.</p>'
        
        html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mis Alertas - ScrapMercadoPublico</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: #fff;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 2px solid #0066cc;
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #0066cc;
            margin: 0;
        }}
        .filters-section {{
            margin-top: 24px;
        }}
        .filters-section h2 {{
            color: #0066cc;
            margin-bottom: 16px;
        }}
        .unsubscribe-all {{
            margin-top: 24px;
            text-align: center;
        }}
        .unsubscribe-all a {{
            background-color: #dc3545;
            color: #fff;
            padding: 12px 24px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-block;
        }}
        .user-info {{
            background-color: #f0f0f0;
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .user-info p {{
            margin: 4px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Mis Alertas de Mercado Público</h1>
        </div>
        
        <div class="user-info">
            <p><strong>Usuario:</strong> {self._escape_html(user.user_id)}</p>
            <p><strong>Fecha de registro:</strong> {self._format_date(user.created_at) if user.created_at else 'No especificado'}</p>
        </div>
        
        <div class="filters-section">
            <h2>Tus Filtros de Alertas</h2>
            <p style="color: #666; margin-bottom: 16px;">
                Recibirás notificaciones por email cuando aparezcan nuevas ofertas que coincidan con estos filtros.
            </p>
            
            {filters_html}
        </div>
        
        <div class="unsubscribe-all">
            <p style="color: #666; margin-bottom: 12px;">¿Quieres desuscribirte de todas las alertas?</p>
            <a href="{self.base_url}/api/unsubscribe?token={user.unsub_token}" 
               onclick="return confirm('¿Estás seguro de que quieres desuscribirte de TODAS las alertas?')">
                Desuscribirse de Todas las Alertas
            </a>
        </div>
    </div>
</body>
</html>
"""
        
        return html


# Instancia global por defecto
_default_renderer: Optional[EmailRenderer] = None


def get_renderer(base_url: Optional[str] = None) -> EmailRenderer:
    """Obtener una instancia del renderer."""
    global _default_renderer
    if _default_renderer is None:
        _default_renderer = EmailRenderer(base_url)
    return _default_renderer
