"""
Delivery para el sistema de alertas.

Este módulo es responsable del envío de emails. Implementa:
- Envío real mediante Mailgun (u otro proveedor)
- Mock para testing sin dependencias externas
- Reintentos y manejo de errores
- Registro de eventos de envío

El módulo está diseñado para ser inyectable, permitiendo usar diferentes
implementaciones (Mailgun, SendGrid, mock, etc.) según el entorno.
"""

import os
import time
from typing import List, Optional, Dict, Any, Protocol, Callable
from datetime import datetime
from dataclasses import dataclass, field

from scripts.alerts.models import User, UserFilter, Offer, EmailQueueItem, EmailEvent


# Protocolo para el cliente de email
class EmailClient(Protocol):
    """Interfaz para clientes de envío de email."""
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str = '',
        from_name: str = 'ScrapMercadoPublico',
        from_email: str = 'noreply@scrapper-mercado-publico-cl.vercel.app',
    ) -> Dict[str, Any]:
        """Enviar un email."""
        ...


@dataclass
class DeliveryResult:
    """Resultado de un intento de envío."""
    success: bool
    queue_id: str
    email: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    retry_after: Optional[float] = None  # Segundos a esperar antes de reintentar
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'success': self.success,
            'queue_id': self.queue_id,
            'email': self.email,
            'message_id': self.message_id,
            'error': self.error,
            'retry_after': self.retry_after,
        }


class MockEmailClient:
    """
    Cliente de email mock para testing.
    
    No envía emails reales, solo simula el comportamiento.
    """
    
    def __init__(self, fail_every_n: int = 0, fail_pattern: Optional[str] = None):
        """
        Inicializar el cliente mock.
        
        Args:
            fail_every_n: Fallar cada N envíos (0 = nunca falla)
            fail_pattern: Patrones de email que deben fallar
        """
        self.fail_every_n = fail_every_n
        self.fail_pattern = fail_pattern
        self.send_count = 0
        self.sent_emails: List[Dict[str, Any]] = []
        self.failed_emails: List[Dict[str, Any]] = []
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str = '',
        from_name: str = 'ScrapMercadoPublico',
        from_email: str = 'noreply@scrapper-mercado-publico-cl.vercel.app',
    ) -> Dict[str, Any]:
        """Enviar email (simulado)."""
        self.send_count += 1
        
        # Verificar si debe fallar
        should_fail = False
        if self.fail_every_n > 0 and self.send_count % self.fail_every_n == 0:
            should_fail = True
        
        if self.fail_pattern and self.fail_pattern in to:
            should_fail = True
        
        if should_fail:
            result = {
                'success': False,
                'message': f'Mock failure: {to}',
                'error': 'Simulated failure',
            }
            self.failed_emails.append({'to': to, 'subject': subject, 'error': 'Simulated failure'})
            return result
        
        # Éxito
        message_id = f"mock_{self.send_count}"
        result = {
            'success': True,
            'message': f'Email sent to {to}',
            'message_id': message_id,
        }
        self.sent_emails.append({'to': to, 'subject': subject, 'message_id': message_id})
        return result
    
    def send_email_sync(self, *args, **kwargs):
        """Versión síncrona de send_email para testing."""
        import asyncio
        return asyncio.run(self.send_email(*args, **kwargs))
    
    def reset(self):
        """Resetear el estado del mock."""
        self.send_count = 0
        self.sent_emails = []
        self.failed_emails = []


class MailgunEmailClient:
    """
    Cliente de email para Mailgun.
    
    Requiere las siguientes variables de entorno:
    - MAILGUN_API_KEY: API key de Mailgun
    - MAILGUN_DOMAIN: Dominio configurado en Mailgun
    """
    
    def __init__(self, api_key: Optional[str] = None, domain: Optional[str] = None):
        """
        Inicializar el cliente de Mailgun.
        
        Args:
            api_key: API key de Mailgun (opcional, usa env var)
            domain: Dominio de Mailgun (opcional, usa env var)
        """
        self.api_key = api_key or os.environ.get('MAILGUN_API_KEY')
        self.domain = domain or os.environ.get('MAILGUN_DOMAIN')
        self._client = None
        
        if not self.api_key:
            raise ValueError("MAILGUN_API_KEY no configurado")
        if not self.domain:
            raise ValueError("MAILGUN_DOMAIN no configurado")
    
    def _get_client(self):
        """Obtener el cliente de Mailgun."""
        if self._client is None:
            try:
                import mailgun
                from mailgun import MailgunClient
                import form_data
                
                # Inicializar cliente
                self._client = MailgunClient(self.api_key)
            except ImportError as e:
                raise RuntimeError("mailgun.js no está instalado. Instálalo con: pip install mailgun") from e
        return self._client
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str = '',
        from_name: str = 'ScrapMercadoPublico',
        from_email: str = 'noreply@scrapper-mercado-publico-cl.vercel.app',
    ) -> Dict[str, Any]:
        """Enviar email mediante Mailgun."""
        try:
            client = self._get_client()
            
            # Enviar email
            response = client.messages.create(
                self.domain,
                {
                    'from': f"{from_name} <{from_email}>",
                    'to': [to],
                    'subject': subject,
                    'html': html,
                    'text': text,
                }
            )
            
            return {
                'success': True,
                'message': f'Email sent to {to}',
                'message_id': response.get('id'),
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error sending email to {to}',
                'error': str(e),
            }


class EmailDelivery:
    """
    Servicio de delivery de emails.
    
    Gestiona el envío de emails desde la cola, con:
    - Reintentos automáticos
    - Registro de eventos
    - Manejo de errores
    """
    
    # Configuración de reintentos
    MAX_ATTEMPTS = 3
    RETRY_DELAYS = [60, 300, 3600]  # Segundos entre reintentos: 1 min, 5 min, 1 hora
    
    def __init__(self, client: Optional[EmailClient] = None):
        """
        Inicializar el servicio de delivery.
        
        Args:
            client: Cliente de email a usar (default: Mailgun si está configurado)
        """
        self.client = client or self._get_default_client()
        self._event_callbacks: List[Callable[[EmailEvent], None]] = []
    
    def _get_default_client(self) -> EmailClient:
        """Obtener el cliente por defecto."""
        try:
            # Intentar usar Mailgun si está configurado
            if os.environ.get('MAILGUN_API_KEY') and os.environ.get('MAILGUN_DOMAIN'):
                return MailgunEmailClient()
        except:
            pass
        
        # Usar mock si no hay configuración
        return MockEmailClient()
    
    def add_event_callback(self, callback: Callable[[EmailEvent], None]):
        """Agregar un callback para eventos de email."""
        self._event_callbacks.append(callback)
    
    def _notify_event(self, event: EmailEvent):
        """Notificar un evento a todos los callbacks."""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"[ERROR] Error en callback de evento: {e}")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str = '',
        queue_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filter_id: Optional[str] = None,
    ) -> DeliveryResult:
        """
        Enviar un email directamente.
        
        Args:
            to: Email destinatario
            subject: Asunto
            html: Cuerpo HTML
            text: Cuerpo texto plano
            queue_id: ID de la cola (opcional)
            user_id: ID de usuario (opcional)
            filter_id: ID de filtro (opcional)
        
        Returns:
            DeliveryResult con el resultado del envío
        """
        try:
            result = await self.client.send_email(
                to=to,
                subject=subject,
                html=html,
                text=text,
            )
            
            if result.get('success'):
                # Registrar evento de envío
                event = EmailEvent(
                    event_id=f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    queue_id=queue_id or '',
                    user_id=user_id or '',
                    filter_id=filter_id or '',
                    event_type='sent',
                    timestamp=datetime.now().isoformat(),
                    details=str(result),
                )
                self._notify_event(event)
                
                return DeliveryResult(
                    success=True,
                    queue_id=queue_id or '',
                    email=to,
                    message_id=result.get('message_id'),
                )
            else:
                # Registrar evento de fallo
                event = EmailEvent(
                    event_id=f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    queue_id=queue_id or '',
                    user_id=user_id or '',
                    filter_id=filter_id or '',
                    event_type='failed',
                    timestamp=datetime.now().isoformat(),
                    details=str(result),
                )
                self._notify_event(event)
                
                return DeliveryResult(
                    success=False,
                    queue_id=queue_id or '',
                    email=to,
                    error=result.get('error', 'Unknown error'),
                )
        except Exception as e:
            return DeliveryResult(
                success=False,
                queue_id=queue_id or '',
                email=to,
                error=str(e),
            )
    
    async def process_queue_item(self, item: EmailQueueItem) -> DeliveryResult:
        """
        Procesar un item de la cola de emails.
        
        Args:
            item: Item de la cola a procesar
        
        Returns:
            DeliveryResult con el resultado
        """
        # Si ya tiene muchos intentos, marcar como fallido
        if item.attempt_count >= self.MAX_ATTEMPTS:
            return DeliveryResult(
                success=False,
                queue_id=item.queue_id,
                email=item.email,
                error='Max attempts reached',
            )
        
        # Enviar email
        result = await self.send_email(
            to=item.email,
            subject=item.subject,
            html=item.body_html,
            text=item.body_text,
            queue_id=item.queue_id,
            user_id=item.user_id,
            filter_id=item.filter_id,
        )
        
        # Actualizar estado según resultado
        if result.success:
            result.retry_after = None
        else:
            # Determinar tiempo de reintento
            result.retry_after = self.RETRY_DELAYS[min(item.attempt_count, len(self.RETRY_DELAYS) - 1)]
        
        return result
    
    async def process_pending_queue(
        self,
        items: List[EmailQueueItem],
        max_concurrent: int = 5,
    ) -> Dict[str, int]:
        """
        Procesar todos los items pendientes en la cola.
        
        Args:
            items: Lista de items pendientes
            max_concurrent: Máximo de envíos concurrentes
        
        Returns:
            Dict con estadísticas: {'sent': N, 'failed': M}
        """
        import asyncio
        
        stats = {'sent': 0, 'failed': 0}
        
        # Procesar items uno por uno para evitar sobrecarga
        for item in items:
            result = await self.process_queue_item(item)
            
            if result.success:
                stats['sent'] += 1
            else:
                stats['failed'] += 1
            
            # Pequeña pausa para evitar rate limiting
            if not result.success and result.retry_after:
                await asyncio.sleep(min(result.retry_after, 10))
            else:
                await asyncio.sleep(0.1)  # Yield para permitir otros tasks
        
        return stats


# Instancia global por defecto
_default_delivery: Optional[EmailDelivery] = None


def get_delivery(client: Optional[EmailClient] = None) -> EmailDelivery:
    """Obtener una instancia del servicio de delivery."""
    global _default_delivery
    if _default_delivery is None:
        _default_delivery = EmailDelivery(client)
    return _default_delivery
