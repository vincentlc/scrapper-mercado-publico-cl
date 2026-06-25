"""
Models para el sistema de alertas.

Define las estructuras de datos principales usadas en el sistema de alertas.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class User:
    """Representa un usuario suscrito a alertas."""
    user_id: str
    email: str
    unsub_token: str
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_notification: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para Google Sheets."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'unsub_token': self.unsub_token,
            'is_active': 'TRUE' if self.is_active else 'FALSE',
            'created_at': self.created_at or '',
            'updated_at': self.updated_at or '',
            'last_notification': self.last_notification or '',
        }
    
    @classmethod
    def from_sheet_row(cls, row: List[str], headers: List[str]) -> 'User':
        """Crear User desde una fila de Google Sheets."""
        data = dict(zip(headers, row))
        return cls(
            user_id=data.get('user_id', ''),
            email=data.get('email', ''),
            unsub_token=data.get('unsub_token', ''),
            is_active=(data.get('is_active', '').upper() == 'TRUE'),
            created_at=data.get('created_at', None),
            updated_at=data.get('updated_at', None),
            last_notification=data.get('last_notification', None),
        )


@dataclass
class UserFilter:
    """Representa un filtro de usuario para alertas."""
    filter_id: str
    user_id: str
    filter_name: str
    keyword: Optional[str] = None
    region: Optional[str] = None
    comuna: Optional[str] = None
    organismo: Optional[str] = None
    tipo_oferta: Optional[str] = None
    monto_min: Optional[float] = None
    monto_max: Optional[float] = None
    moneda: Optional[str] = None
    estado: Optional[str] = None
    utm_range: Optional[str] = None
    send_frequency: str = "immediate"  # immediate, daily, weekly
    is_active: bool = True
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para Google Sheets."""
        return {
            'filter_id': self.filter_id,
            'user_id': self.user_id,
            'filter_name': self.filter_name,
            'keyword': self.keyword or '',
            'region': self.region or '',
            'comuna': self.comuna or '',
            'organismo': self.organismo or '',
            'tipo_oferta': self.tipo_oferta or '',
            'monto_min': str(self.monto_min) if self.monto_min is not None else '',
            'monto_max': str(self.monto_max) if self.monto_max is not None else '',
            'moneda': self.moneda or '',
            'estado': self.estado or '',
            'utm_range': self.utm_range or '',
            'send_frequency': self.send_frequency,
            'is_active': 'TRUE' if self.is_active else 'FALSE',
            'created_at': self.created_at or '',
        }
    
    @classmethod
    def from_sheet_row(cls, row: List[str], headers: List[str]) -> 'UserFilter':
        """Crear UserFilter desde una fila de Google Sheets."""
        data = dict(zip(headers, row))
        return cls(
            filter_id=data.get('filter_id', ''),
            user_id=data.get('user_id', ''),
            filter_name=data.get('filter_name', ''),
            keyword=data.get('keyword', None) if data.get('keyword') else None,
            region=data.get('region', None) if data.get('region') else None,
            comuna=data.get('comuna', None) if data.get('comuna') else None,
            organismo=data.get('organismo', None) if data.get('organismo') else None,
            tipo_oferta=data.get('tipo_oferta', None) if data.get('tipo_oferta') else None,
            monto_min=float(data.get('monto_min')) if data.get('monto_min') else None,
            monto_max=float(data.get('monto_max')) if data.get('monto_max') else None,
            moneda=data.get('moneda', None) if data.get('moneda') else None,
            estado=data.get('estado', None) if data.get('estado') else None,
            utm_range=data.get('utm_range', None) if data.get('utm_range') else None,
            send_frequency=data.get('send_frequency', 'immediate'),
            is_active=(data.get('is_active', '').upper() == 'TRUE'),
            created_at=data.get('created_at', None),
        )


@dataclass
class Offer:
    """Representa una oferta de Mercado Público."""
    codigo_externo: str
    nombre: str
    descripcion: Optional[str] = None
    descripcion_producto: Optional[str] = None
    organismo: Optional[str] = None
    estado: Optional[str] = None
    region: Optional[str] = None
    comuna: Optional[str] = None
    tipo_oferta: Optional[str] = None
    moneda: Optional[str] = None
    monto_estimado: Optional[float] = None
    fecha_publicacion: Optional[str] = None
    fecha_cierre: Optional[str] = None
    link: Optional[str] = None
    raw_json: Optional[str] = None
    is_new: bool = False  # Marca si es una oferta nueva (no existía antes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'codigo_externo': self.codigo_externo,
            'nombre': self.nombre,
            'descripcion': self.descripcion or '',
            'descripcion_producto': self.descripcion_producto or '',
            'organismo': self.organismo or '',
            'estado': self.estado or '',
            'region': self.region or '',
            'comuna': self.comuna or '',
            'tipo_oferta': self.tipo_oferta or '',
            'moneda': self.moneda or '',
            'monto_estimado': str(self.monto_estimado) if self.monto_estimado is not None else '',
            'fecha_publicacion': self.fecha_publicacion or '',
            'fecha_cierre': self.fecha_cierre or '',
            'link': self.link or '',
            'raw_json': self.raw_json or '',
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Offer':
        """Crear Offer desde un diccionario."""
        return cls(
            codigo_externo=data.get('codigo_externo', ''),
            nombre=data.get('nombre', ''),
            descripcion=data.get('descripcion', None),
            descripcion_producto=data.get('descripcion_producto', None),
            organismo=data.get('organismo', None),
            estado=data.get('estado', None),
            region=data.get('region', None),
            comuna=data.get('comuna', None),
            tipo_oferta=data.get('tipo_oferta', None),
            moneda=data.get('moneda', None),
            monto_estimado=float(data.get('monto_estimado')) if data.get('monto_estimado') else None,
            fecha_publicacion=data.get('fecha_publicacion', None),
            fecha_cierre=data.get('fecha_cierre', None),
            link=data.get('link', None),
            raw_json=data.get('raw_json', None),
        )


@dataclass
class EmailQueueItem:
    """Representa un item en la cola de emails a enviar."""
    queue_id: str
    user_id: str
    filter_id: str
    email: str
    subject: str
    body_html: str
    body_text: str = ''
    status: str = 'pending'  # pending, sent, failed
    attempt_count: int = 0
    created_at: Optional[str] = None
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para Google Sheets."""
        return {
            'queue_id': self.queue_id,
            'user_id': self.user_id,
            'filter_id': self.filter_id,
            'email': self.email,
            'subject': self.subject,
            'body_html': self.body_html,
            'body_text': self.body_text,
            'status': self.status,
            'attempt_count': str(self.attempt_count),
            'created_at': self.created_at or '',
            'sent_at': self.sent_at or '',
            'error_message': self.error_message or '',
        }
    
    @classmethod
    def from_sheet_row(cls, row: List[str], headers: List[str]) -> 'EmailQueueItem':
        """Crear EmailQueueItem desde una fila de Google Sheets."""
        data = dict(zip(headers, row))
        return cls(
            queue_id=data.get('queue_id', ''),
            user_id=data.get('user_id', ''),
            filter_id=data.get('filter_id', ''),
            email=data.get('email', ''),
            subject=data.get('subject', ''),
            body_html=data.get('body_html', ''),
            body_text=data.get('body_text', ''),
            status=data.get('status', 'pending'),
            attempt_count=int(data.get('attempt_count', 0)),
            created_at=data.get('created_at', None),
            sent_at=data.get('sent_at', None),
            error_message=data.get('error_message', None),
        )


@dataclass
class EmailEvent:
    """Representa un evento de email (log de envíos)."""
    event_id: str
    queue_id: str
    user_id: str
    filter_id: str
    event_type: str  # sent, delivered, bounced, opened, clicked, failed
    timestamp: Optional[str] = None
    details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para Google Sheets."""
        return {
            'event_id': self.event_id,
            'queue_id': self.queue_id,
            'user_id': self.user_id,
            'filter_id': self.filter_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp or '',
            'details': self.details or '',
        }
    
    @classmethod
    def from_sheet_row(cls, row: List[str], headers: List[str]) -> 'EmailEvent':
        """Crear EmailEvent desde una fila de Google Sheets."""
        data = dict(zip(headers, row))
        return cls(
            event_id=data.get('event_id', ''),
            queue_id=data.get('queue_id', ''),
            user_id=data.get('user_id', ''),
            filter_id=data.get('filter_id', ''),
            event_type=data.get('event_type', ''),
            timestamp=data.get('timestamp', None),
            details=data.get('details', None),
        )


@dataclass
class NotificationRun:
    """Representa una ejecución del sistema de notificaciones."""
    run_id: str
    timestamp: Optional[str] = None
    status: str = 'SUCCESS'  # SUCCESS, ERROR, PARTIAL
    new_offers_count: int = 0
    updated_offers_count: int = 0
    deleted_offers_count: int = 0
    matches_found: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    error_message: Optional[str] = None
    duration_seconds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para Google Sheets."""
        return {
            'run_id': self.run_id,
            'timestamp': self.timestamp or '',
            'status': self.status,
            'new_offers_count': str(self.new_offers_count),
            'updated_offers_count': str(self.updated_offers_count),
            'deleted_offers_count': str(self.deleted_offers_count),
            'matches_found': str(self.matches_found),
            'emails_sent': str(self.emails_sent),
            'emails_failed': str(self.emails_failed),
            'error_message': self.error_message or '',
            'duration_seconds': str(self.duration_seconds),
        }
    
    @classmethod
    def from_sheet_row(cls, row: List[str], headers: List[str]) -> 'NotificationRun':
        """Crear NotificationRun desde una fila de Google Sheets."""
        data = dict(zip(headers, row))
        return cls(
            run_id=data.get('run_id', ''),
            timestamp=data.get('timestamp', None),
            status=data.get('status', 'SUCCESS'),
            new_offers_count=int(data.get('new_offers_count', 0)),
            updated_offers_count=int(data.get('updated_offers_count', 0)),
            deleted_offers_count=int(data.get('deleted_offers_count', 0)),
            matches_found=int(data.get('matches_found', 0)),
            emails_sent=int(data.get('emails_sent', 0)),
            emails_failed=int(data.get('emails_failed', 0)),
            error_message=data.get('error_message', None),
            duration_seconds=int(data.get('duration_seconds', 0)),
        )


# Esquemas de Google Sheets esperados
SHEET_SCHEMAS = {
    'users': [
        'user_id', 'email', 'unsub_token', 'is_active', 
        'created_at', 'updated_at', 'last_notification'
    ],
    'user_filters': [
        'filter_id', 'user_id', 'filter_name', 'keyword', 'region', 'comuna',
        'organismo', 'tipo_oferta', 'monto_min', 'monto_max', 'moneda', 'estado',
        'utm_range', 'send_frequency', 'is_active', 'created_at'
    ],
    'email_queue': [
        'queue_id', 'user_id', 'filter_id', 'email', 'subject', 'body_html',
        'body_text', 'status', 'attempt_count', 'created_at', 'sent_at', 'error_message'
    ],
    'email_events': [
        'event_id', 'queue_id', 'user_id', 'filter_id', 'event_type',
        'timestamp', 'details'
    ],
    'notification_runs': [
        'run_id', 'timestamp', 'status', 'new_offers_count', 'updated_offers_count',
        'deleted_offers_count', 'matches_found', 'emails_sent', 'emails_failed',
        'error_message', 'duration_seconds'
    ],
}
