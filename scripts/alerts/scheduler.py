"""
Scheduler para el sistema de alertas.

Este módulo integra todos los componentes del sistema de alertas:
- Repository (Google Sheets)
- Matcher (lógica de coincidencias)
- Renderer (plantillas de email)
- Delivery (envío de emails)

Proporciona una interfaz simple para ejecutar el pipeline completo
desde el script de scraping.
"""

import asyncio
import time
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from scripts.alerts.models import (
    User,
    UserFilter,
    Offer,
    EmailQueueItem,
    EmailEvent,
    NotificationRun,
)
from scripts.alerts.matcher import OfferMatcher, MatchResult, get_matcher
from scripts.alerts.renderer import EmailRenderer, get_renderer
from scripts.alerts.delivery import EmailDelivery, get_delivery

# Importación opcional del repositorio
try:
    from scripts.alerts.repository import AlertsRepository, get_repository
    HAS_REPOSITORY = True
except ImportError:
    HAS_REPOSITORY = False


class AlertsScheduler:
    """
    Scheduler del sistema de alertas.
    
    Coordina el flujo completo de:
    1. Obtener ofertas nuevas
    2. Comparar con filtros de usuarios
    3. Generar emails para coincidencias
    4. Agregar a la cola de emails
    5. Enviar emails (opcional, puede ser asíncrono)
    """
    
    def __init__(
        self,
        repository: Optional[AlertsRepository] = None,
        matcher: Optional[OfferMatcher] = None,
        renderer: Optional[EmailRenderer] = None,
        delivery: Optional[EmailDelivery] = None,
        base_url: str = "https://scrapper-mercado-publico-cl.vercel.app",
    ):
        """
        Inicializar el scheduler.
        
        Args:
            repository: Repositorio de datos (default: usa Google Sheets)
            matcher: Matcher de ofertas (default: nuevo matcher)
            renderer: Renderer de emails (default: nuevo renderer)
            delivery: Servicio de delivery (default: nuevo delivery)
            base_url: URL base para enlaces en emails
        """
        self.repository = repository or get_repository()
        self.matcher = matcher or get_matcher()
        self.renderer = renderer or get_renderer(base_url)
        self.delivery = delivery or get_delivery()
        self.base_url = base_url
    
    def _generate_queue_items(
        self,
        matches: List[MatchResult],
        users: Dict[str, User],
    ) -> List[EmailQueueItem]:
        """
        Generar items de la cola de emails a partir de coincidencias.
        
        Agrupa las coincidencias por usuario y filtro, y genera un email
        consolidado por usuario.
        
        Args:
            matches: Lista de coincidencias
            users: Diccionario {user_id: User}
        
        Returns:
            Lista de EmailQueueItem
        """
        # Agrupar coincidencias por usuario y filtro
        user_filter_matches: Dict[str, Dict[str, List[Offer]]] = {}
        
        for match in matches:
            user_id = match.filter.user_id
            filter_id = match.filter.filter_id
            
            if user_id not in user_filter_matches:
                user_filter_matches[user_id] = {}
            if filter_id not in user_filter_matches[user_id]:
                user_filter_matches[user_id][filter_id] = []
            
            user_filter_matches[user_id][filter_id].append(match.offer)
        
        # Generar items de cola
        queue_items = []
        
        for user_id, filter_matches in user_filter_matches.items():
            user = users.get(user_id)
            if not user or not user.is_active:
                continue
            
            # Para cada filtro del usuario que tenga coincidencias
            for filter_id, offers in filter_matches.items():
                # Obtener el filtro
                filter = None
                for f in matches:
                    if f.filter.filter_id == filter_id:
                        filter = f.filter
                        break
                
                if not filter or not filter.is_active:
                    continue
                
                # Renderizar email
                email_content = self.renderer.render_new_offers_email(
                    user=user,
                    filter=filter,
                    offers=offers[:10],  # Solo 10 ofertas por filtro
                    max_offers=10,
                )
                
                # Crear item de cola
                queue_item = EmailQueueItem(
                    queue_id=f"q_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{user_id}_{filter_id}",
                    user_id=user_id,
                    filter_id=filter_id,
                    email=user.email,
                    subject=email_content['subject'],
                    body_html=email_content['html'],
                    body_text=email_content['text'],
                    status='pending',
                    attempt_count=0,
                    created_at=datetime.now().isoformat(),
                )
                queue_items.append(queue_item)
        
        return queue_items
    
    def check_new_offers_and_queue_emails(
        self,
        new_offers: List[Offer],
    ) -> Dict[str, int]:
        """
        Verificar ofertas nuevas y agregar emails a la cola.
        
        Este es el método principal del scheduler. Recibe una lista de
        ofertas nuevas (que no existían antes) y:
        1. Obtiene todos los filtros activos de usuarios
        2. Encuentra coincidencias entre ofertas y filtros
        3. Genera items de cola de emails para las coincidencias
        4. Agrega los items a la cola (Google Sheets)
        
        Args:
            new_offers: Lista de ofertas nuevas
        
        Returns:
            Dict con estadísticas:
            {
                'total_offers': N,
                'total_filters': M,
                'matches_found': K,
                'queue_items_created': L,
            }
        """
        stats = {
            'total_offers': len(new_offers),
            'total_filters': 0,
            'matches_found': 0,
            'queue_items_created': 0,
        }
        
        try:
            # Obtener todos los filtros activos
            all_filters = self.repository.get_all_filters()
            active_filters = [f for f in all_filters if f.is_active]
            stats['total_filters'] = len(active_filters)
            
            if not active_filters:
                return stats
            
            # Obtener todos los usuarios activos
            all_users = self.repository.get_all_users()
            active_users = {u.user_id: u for u in all_users if u.is_active}
            
            # Encontrar coincidencias
            matches = self.matcher.match_offers_to_filters(new_offers, active_filters)
            stats['matches_found'] = len(matches)
            
            if not matches:
                return stats
            
            # Generar items de cola
            queue_items = self._generate_queue_items(matches, active_users)
            stats['queue_items_created'] = len(queue_items)
            
            # Agregar a la cola (en lote)
            if queue_items:
                self.repository.create_queue_items_batch(queue_items)
            
            return stats
        
        except Exception as e:
            print(f"[ERROR] Error en check_new_offers_and_queue_emails: {e}")
            raise
    
    async def process_queue(
        self,
        limit: int = 100,
    ) -> Dict[str, int]:
        """
        Procesar la cola de emails pendientes.
        
        Envía los emails que están en la cola en estado 'pending'.
        
        Args:
            limit: Máximo número de items a procesar
        
        Returns:
            Dict con estadísticas:
            {
                'pending': N,
                'sent': M,
                'failed': K,
            }
        """
        stats = {
            'pending': 0,
            'sent': 0,
            'failed': 0,
        }
        
        try:
            # Obtener items pendientes
            pending_items = self.repository.get_pending_queue_items(limit)
            stats['pending'] = len(pending_items)
            
            if not pending_items:
                return stats
            
            # Procesar cada item
            for item in pending_items:
                result = await self.delivery.process_queue_item(item)
                
                if result.success:
                    # Marcar como enviado
                    self.repository.update_queue_item_status(
                        item.queue_id,
                        'sent',
                        sent_at=datetime.now().isoformat(),
                    )
                    stats['sent'] += 1
                    
                    # Registrar evento
                    self.repository.create_email_event(EmailEvent(
                        event_id=f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        queue_id=item.queue_id,
                        user_id=item.user_id,
                        filter_id=item.filter_id,
                        event_type='sent',
                        timestamp=datetime.now().isoformat(),
                        details=f"Message ID: {result.message_id}",
                    ))
                else:
                    # Incrementar intentos
                    self.repository.increment_queue_item_attempts(item.queue_id)
                    
                    # Marcar como fallido si es el último intento
                    if item.attempt_count >= self.delivery.MAX_ATTEMPTS:
                        self.repository.update_queue_item_status(
                            item.queue_id,
                            'failed',
                            error_message=result.error,
                        )
                    
                    stats['failed'] += 1
                    
                    # Registrar evento
                    self.repository.create_email_event(EmailEvent(
                        event_id=f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        queue_id=item.queue_id,
                        user_id=item.user_id,
                        filter_id=item.filter_id,
                        event_type='failed',
                        timestamp=datetime.now().isoformat(),
                        details=f"Error: {result.error}",
                    ))
                
                # Pequeña pausa
                await asyncio.sleep(0.1)
            
            return stats
        
        except Exception as e:
            print(f"[ERROR] Error en process_queue: {e}")
            raise
    
    def run_complete_cycle(
        self,
        new_offers: List[Offer],
        process_queue_now: bool = False,
    ) -> Dict[str, Any]:
        """
        Ejecutar el ciclo completo de alertas.
        
        Este método hace todo:
        1. Verifica ofertas nuevas y genera cola de emails
        2. (Opcional) Procesa la cola de emails
        3. Registra la ejecución
        
        Args:
            new_offers: Lista de ofertas nuevas
            process_queue_now: Si True, procesa la cola inmediatamente (síncrono)
        
        Returns:
            Dict con estadísticas completas
        """
        start_time = time.time()
        
        stats = {
            'new_offers_count': len(new_offers),
            'matches_found': 0,
            'queue_items_created': 0,
            'emails_sent': 0,
            'emails_failed': 0,
            'duration_seconds': 0,
            'status': 'SUCCESS',
            'error_message': None,
        }
        
        try:
            # Paso 1: Verificar ofertas nuevas y generar cola
            check_stats = self.check_new_offers_and_queue_emails(new_offers)
            stats['matches_found'] = check_stats['matches_found']
            stats['queue_items_created'] = check_stats['queue_items_created']
            
            # Paso 2: Procesar cola si se solicita
            if process_queue_now:
                # Ejecutar síncronamente (bloqueante)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    queue_stats = loop.run_until_complete(
                        self.process_queue(limit=stats['queue_items_created'])
                    )
                    stats['emails_sent'] = queue_stats['sent']
                    stats['emails_failed'] = queue_stats['failed']
                finally:
                    loop.close()
            
            stats['duration_seconds'] = int(time.time() - start_time)
            stats['status'] = 'SUCCESS'
            
        except Exception as e:
            stats['status'] = 'ERROR'
            stats['error_message'] = str(e)
            stats['duration_seconds'] = int(time.time() - start_time)
        
        # Registrar la ejecución
        try:
            run = NotificationRun(
                run_id=f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                timestamp=datetime.now().isoformat(),
                status=stats['status'],
                new_offers_count=stats['new_offers_count'],
                updated_offers_count=0,
                deleted_offers_count=0,
                matches_found=stats['matches_found'],
                emails_sent=stats['emails_sent'],
                emails_failed=stats['emails_failed'],
                error_message=stats['error_message'],
                duration_seconds=stats['duration_seconds'],
            )
            self.repository.create_notification_run(run)
        except Exception as e:
            print(f"[WARNING] Error registrando ejecución: {e}")
        
        return stats


# Funciones de conveniencia

_default_scheduler: Optional[AlertsScheduler] = None


def get_scheduler(base_url: Optional[str] = None) -> AlertsScheduler:
    """Obtener una instancia del scheduler."""
    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = AlertsScheduler(base_url=base_url)
    return _default_scheduler


def check_and_queue_new_offers(new_offers: List[Offer]) -> Dict[str, int]:
    """
    Verificar ofertas nuevas y agregar emails a la cola.
    
    Función de conveniencia que usa el scheduler por defecto.
    
    Args:
        new_offers: Lista de ofertas nuevas
    
    Returns:
        Estadísticas del proceso
    """
    scheduler = get_scheduler()
    return scheduler.check_new_offers_and_queue_emails(new_offers)


async def process_pending_emails(limit: int = 100) -> Dict[str, int]:
    """
    Procesar emails pendientes en la cola.
    
    Función de conveniencia asíncrona.
    
    Args:
        limit: Máximo número de items a procesar
    
    Returns:
        Estadísticas del proceso
    """
    scheduler = get_scheduler()
    return await scheduler.process_queue(limit)


def run_complete_alert_cycle(
    new_offers: List[Offer],
    process_queue_now: bool = False,
) -> Dict[str, Any]:
    """
    Ejecutar el ciclo completo de alertas.
    
    Función de conveniencia que usa el scheduler por defecto.
    
    Args:
        new_offers: Lista de ofertas nuevas
        process_queue_now: Si True, procesa la cola inmediatamente
    
    Returns:
        Estadísticas completas
    """
    scheduler = get_scheduler()
    return scheduler.run_complete_cycle(new_offers, process_queue_now)
