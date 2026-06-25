"""
Repository para el sistema de alertas.

Proporciona una capa de abstracción para acceder a Google Sheets como backend
de persistencia para el sistema de alertas.

Este módulo es responsable de:
- Leer y escribir usuarios
- Leer y escribir filtros de usuarios
- Gestionar la cola de emails
- Registrar eventos de envío
- Registrar ejecuciones de notificaciones
"""

import os
import json
import base64
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

# Importaciones opcionales para evitar dependencias en pruebas
try:
    from scripts.helpers import (
        get_sheets_client,
        get_sheet_data,
        append_to_sheet,
        append_many_rows,
    )
    HAS_GOOGLE_SHEETS = True
except ImportError:
    HAS_GOOGLE_SHEETS = False

from scripts.alerts.models import (
    User,
    UserFilter,
    Offer,
    EmailQueueItem,
    EmailEvent,
    NotificationRun,
    SHEET_SCHEMAS,
)


class AlertsRepository:
    """
    Repositorio para el sistema de alertas.
    
    Usa Google Sheets como backend de persistencia.
    """
    
    def __init__(self, spreadsheet_id: Optional[str] = None, creds_json: Optional[str] = None):
        """
        Inicializar el repositorio.
        
        Args:
            spreadsheet_id: ID de la hoja de cálculo (opcional, usa env var)
            creds_json: Credenciales JSON (opcional, usa env var)
        """
        self._spreadsheet_id = spreadsheet_id or os.environ.get('GOOGLE_SHEETS_ID')
        self._creds_json = creds_json or os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        self._service = None
    
    def _get_service(self):
        """Obtener el cliente de Google Sheets."""
        if self._service is None:
            self._service = get_sheets_client()
        return self._service
    
    def _get_sheet_data(self, sheet_name: str) -> List[List[str]]:
        """Obtener todos los datos de una hoja."""
        return get_sheet_data(sheet_name)
    
    # ==================== USUARIOS ====================
    
    def get_all_users(self) -> List[User]:
        """Obtener todos los usuarios activos."""
        rows = self._get_sheet_data('users')
        if not rows or len(rows) < 2:
            return []
        
        headers = rows[0]
        users = []
        for row in rows[1:]:
            if row and len(row) > 0:
                try:
                    user = User.from_sheet_row(row, headers)
                    users.append(user)
                except Exception as e:
                    print(f"[WARNING] Error parseando usuario en fila {row}: {e}")
                    continue
        return users
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtener un usuario por su ID."""
        users = self.get_all_users()
        for user in users:
            if user.user_id == user_id:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtener un usuario por su email."""
        users = self.get_all_users()
        for user in users:
            if user.email.lower() == email.lower():
                return user
        return None
    
    def get_user_by_unsub_token(self, token: str) -> Optional[User]:
        """Obtener un usuario por su token de desuscripción."""
        users = self.get_all_users()
        for user in users:
            if user.unsub_token == token:
                return user
        return None
    
    def create_user(self, user: User) -> User:
        """Crear un nuevo usuario."""
        row = [
            user.user_id,
            user.email,
            user.unsub_token,
            'TRUE' if user.is_active else 'FALSE',
            user.created_at or datetime.now().isoformat(),
            user.updated_at or '',
            user.last_notification or '',
        ]
        append_to_sheet('users', row)
        return user
    
    def update_user(self, user: User) -> bool:
        """
        Actualizar un usuario.
        
        Nota: Google Sheets no tiene UPDATE directo, por lo que necesitamos
        buscar y reemplazar la fila. Esto es una limitación de la API.
        
        Por ahora, solo actualizamos el campo is_active a FALSE para desuscribir.
        """
        # Para desuscripción, marcamos como inactivo
        if not user.is_active:
            rows = self._get_sheet_data('users')
            if not rows or len(rows) < 2:
                return False
            
            headers = rows[0]
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > 0 and row[0] == user.user_id:
                    # Actualizar la fila: solo cambiamos is_active a FALSE
                    new_row = list(row)
                    if len(new_row) > 3:
                        new_row[3] = 'FALSE'
                    
                    service = self._get_service()
                    service.spreadsheets().values().update(
                        spreadsheetId=self._spreadsheet_id,
                        range=f'users!A{i}:Z{i}',
                        valueInputOption='RAW',
                        body={'values': [new_row]}
                    ).execute()
                    return True
        
        return False
    
    # ==================== FILTROS DE USUARIO ====================
    
    def get_all_filters(self) -> List[UserFilter]:
        """Obtener todos los filtros."""
        rows = self._get_sheet_data('user_filters')
        if not rows or len(rows) < 2:
            return []
        
        headers = rows[0]
        filters = []
        for row in rows[1:]:
            if row and len(row) > 0:
                try:
                    user_filter = UserFilter.from_sheet_row(row, headers)
                    filters.append(user_filter)
                except Exception as e:
                    print(f"[WARNING] Error parseando filtro en fila {row}: {e}")
                    continue
        return filters
    
    def get_filters_by_user(self, user_id: str) -> List[UserFilter]:
        """Obtener todos los filtros de un usuario."""
        all_filters = self.get_all_filters()
        return [f for f in all_filters if f.user_id == user_id]
    
    def get_filter_by_id(self, filter_id: str) -> Optional[UserFilter]:
        """Obtener un filtro por su ID."""
        all_filters = self.get_all_filters()
        for f in all_filters:
            if f.filter_id == filter_id:
                return f
        return None
    
    def create_filter(self, user_filter: UserFilter) -> UserFilter:
        """Crear un nuevo filtro."""
        row = [
            user_filter.filter_id,
            user_filter.user_id,
            user_filter.filter_name,
            user_filter.keyword or '',
            user_filter.region or '',
            user_filter.comuna or '',
            user_filter.organismo or '',
            user_filter.tipo_oferta or '',
            str(user_filter.monto_min) if user_filter.monto_min is not None else '',
            str(user_filter.monto_max) if user_filter.monto_max is not None else '',
            user_filter.moneda or '',
            user_filter.estado or '',
            user_filter.utm_range or '',
            user_filter.send_frequency,
            'TRUE' if user_filter.is_active else 'FALSE',
            user_filter.created_at or datetime.now().isoformat(),
        ]
        append_to_sheet('user_filters', row)
        return user_filter
    
    def delete_filter(self, filter_id: str) -> bool:
        """
        Eliminar un filtro.
        
        Nota: Google Sheets no tiene DELETE directo. Para simplificar,
        marcamos el filtro como inactivo.
        """
        user_filter = self.get_filter_by_id(filter_id)
        if user_filter:
            user_filter.is_active = False
            # Actualizar en la hoja
            rows = self._get_sheet_data('user_filters')
            if not rows or len(rows) < 2:
                return False
            
            headers = rows[0]
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > 0 and row[0] == filter_id:
                    new_row = list(row)
                    if len(new_row) > 13:  # is_active está en índice 13
                        new_row[13] = 'FALSE'
                    
                    service = self._get_service()
                    service.spreadsheets().values().update(
                        spreadsheetId=self._spreadsheet_id,
                        range=f'user_filters!A{i}:Z{i}',
                        valueInputOption='RAW',
                        body={'values': [new_row]}
                    ).execute()
                    return True
        return False
    
    # ==================== COLA DE EMAILS ====================
    
    def create_queue_item(self, item: EmailQueueItem) -> EmailQueueItem:
        """Crear un item en la cola de emails."""
        row = [
            item.queue_id,
            item.user_id,
            item.filter_id,
            item.email,
            item.subject,
            item.body_html,
            item.body_text,
            item.status,
            str(item.attempt_count),
            item.created_at or datetime.now().isoformat(),
            item.sent_at or '',
            item.error_message or '',
        ]
        append_to_sheet('email_queue', row)
        return item
    
    def create_queue_items_batch(self, items: List[EmailQueueItem]) -> List[EmailQueueItem]:
        """Crear múltiples items en la cola de una sola vez."""
        if not items:
            return []
        
        rows = []
        for item in items:
            row = [
                item.queue_id,
                item.user_id,
                item.filter_id,
                item.email,
                item.subject,
                item.body_html,
                item.body_text,
                item.status,
                str(item.attempt_count),
                item.created_at or datetime.now().isoformat(),
                item.sent_at or '',
                item.error_message or '',
            ]
            rows.append(row)
        
        append_many_rows('email_queue', rows)
        return items
    
    def get_pending_queue_items(self, limit: int = 100) -> List[EmailQueueItem]:
        """Obtener items de la cola en estado pending."""
        rows = self._get_sheet_data('email_queue')
        if not rows or len(rows) < 2:
            return []
        
        headers = rows[0]
        items = []
        for row in rows[1:]:
            if row and len(row) > 0:
                try:
                    item = EmailQueueItem.from_sheet_row(row, headers)
                    if item.status == 'pending' and len(items) < limit:
                        items.append(item)
                except Exception as e:
                    print(f"[WARNING] Error parseando queue item en fila {row}: {e}")
                    continue
        return items
    
    def update_queue_item_status(self, queue_id: str, status: str, 
                                  sent_at: Optional[str] = None, 
                                  error_message: Optional[str] = None) -> bool:
        """Actualizar el estado de un item en la cola."""
        rows = self._get_sheet_data('email_queue')
        if not rows or len(rows) < 2:
            return False
        
        headers = rows[0]
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 0 and row[0] == queue_id:
                new_row = list(row)
                # status está en índice 7
                if len(new_row) > 7:
                    new_row[7] = status
                # sent_at está en índice 10
                if len(new_row) > 10 and sent_at:
                    new_row[10] = sent_at
                # error_message está en índice 11
                if len(new_row) > 11 and error_message:
                    new_row[11] = error_message
                
                service = self._get_service()
                service.spreadsheets().values().update(
                    spreadsheetId=self._spreadsheet_id,
                    range=f'email_queue!A{i}:Z{i}',
                    valueInputOption='RAW',
                    body={'values': [new_row]}
                ).execute()
                return True
        return False
    
    def increment_queue_item_attempts(self, queue_id: str) -> bool:
        """Incrementar el contador de intentos de un item en la cola."""
        rows = self._get_sheet_data('email_queue')
        if not rows or len(rows) < 2:
            return False
        
        headers = rows[0]
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > 0 and row[0] == queue_id:
                new_row = list(row)
                # attempt_count está en índice 8
                if len(new_row) > 8:
                    try:
                        new_row[8] = str(int(new_row[8]) + 1)
                    except:
                        new_row[8] = '1'
                
                service = self._get_service()
                service.spreadsheets().values().update(
                    spreadsheetId=self._spreadsheet_id,
                    range=f'email_queue!A{i}:Z{i}',
                    valueInputOption='RAW',
                    body={'values': [new_row]}
                ).execute()
                return True
        return False
    
    # ==================== EVENTOS DE EMAIL ====================
    
    def create_email_event(self, event: EmailEvent) -> EmailEvent:
        """Crear un evento de email."""
        row = [
            event.event_id,
            event.queue_id,
            event.user_id,
            event.filter_id,
            event.event_type,
            event.timestamp or datetime.now().isoformat(),
            event.details or '',
        ]
        append_to_sheet('email_events', row)
        return event
    
    # ==================== EJECUCIONES DE NOTIFICACIÓN ====================
    
    def create_notification_run(self, run: NotificationRun) -> NotificationRun:
        """Crear un registro de ejecución de notificaciones."""
        row = [
            run.run_id,
            run.timestamp or datetime.now().isoformat(),
            run.status,
            str(run.new_offers_count),
            str(run.updated_offers_count),
            str(run.deleted_offers_count),
            str(run.matches_found),
            str(run.emails_sent),
            str(run.emails_failed),
            run.error_message or '',
            str(run.duration_seconds),
        ]
        append_to_sheet('notification_runs', row)
        return run
    
    # ==================== OFERTAS ====================
    
    def get_existing_offer_codes(self) -> set:
        """Obtener todos los códigos de ofertas existentes."""
        rows = self._get_sheet_data('ofertas')
        codes = set()
        if rows and len(rows) > 1:
            for row in rows[1:]:
                if row and len(row) > 0:
                    codes.add(str(row[0]).strip())
        return codes
    
    def get_new_offers_since_last_run(self, last_run_timestamp: Optional[str] = None) -> List[Offer]:
        """
        Obtener ofertas nuevas desde la última ejecución.
        
        Esto es útil para encontrar solo las ofertas que deben generar alertas.
        """
        rows = self._get_sheet_data('ofertas')
        if not rows or len(rows) < 2:
            return []
        
        headers = rows[0]
        offers = []
        
        # Si tenemos un timestamp de última ejecución, filtramos por fecha
        # Por ahora, asumimos que todas las ofertas en la hoja son candidatas
        # El filtro real por "nuevas" se hará en el pipeline
        for row in rows[1:]:
            if row and len(row) > 0:
                offer_data = dict(zip(headers, row))
                offer = Offer.from_dict(offer_data)
                offer.is_new = True  # Marcamos como nuevas por defecto
                offers.append(offer)
        
        return offers


# Instancia global por defecto
_default_repository: Optional[AlertsRepository] = None


def get_repository() -> AlertsRepository:
    """Obtener una instancia del repositorio."""
    global _default_repository
    if _default_repository is None:
        _default_repository = AlertsRepository()
    return _default_repository
