"""
Sistema de Alertas por Email para ScrapMercadoPublico

Este módulo implementa un sistema modular de alertas que:
1. Permite registrar usuarios con email y filtros guardados
2. Compare nuevas ofertas contra esos filtros
3. Envía correos solo a los usuarios que correspondan
4. Mantiene la privacidad del email y evita exponerlo públicamente
5. Es testeable sin depender de Mailgun o Google Sheets reales

Estructura:
- models.py: Definiciones de datos y estructuras
- repository.py: Capa de almacenamiento (Google Sheets)
- matcher.py: Lógica de coincidencia entre ofertas y filtros
- renderer.py: Generación de contenido HTML para emails
- delivery.py: Envío de emails (con Mailgun o mock)
- scheduler.py: Integración con el pipeline de scraping
"""

# Importaciones básicas (siempre disponibles)
from scripts.alerts.models import (
    User,
    UserFilter,
    Offer,
    EmailQueueItem,
    EmailEvent,
    NotificationRun,
)
from scripts.alerts.matcher import OfferMatcher, MatchResult
from scripts.alerts.renderer import EmailRenderer
from scripts.alerts.delivery import EmailDelivery, MockEmailClient, DeliveryResult

# Importaciones opcionales (dependen de Google Sheets)
try:
    from scripts.alerts.repository import AlertsRepository, get_repository
    HAS_REPOSITORY = True
except ImportError:
    HAS_REPOSITORY = False

try:
    from scripts.alerts.scheduler import AlertsScheduler, get_scheduler, check_and_queue_new_offers
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

__all__ = [
    'User', 'UserFilter', 'Offer', 'EmailQueueItem', 'EmailEvent', 'NotificationRun',
    'OfferMatcher', 'MatchResult', 'EmailRenderer', 'EmailDelivery', 'MockEmailClient', 'DeliveryResult',
    'HAS_REPOSITORY', 'HAS_SCHEDULER',
]

# Agregar al __all__ si están disponibles
if HAS_REPOSITORY:
    __all__.extend(['AlertsRepository', 'get_repository'])
if HAS_SCHEDULER:
    __all__.extend(['AlertsScheduler', 'get_scheduler', 'check_and_queue_new_offers'])
