import json
import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def get_sheets_client():
    """Obtener cliente de Google Sheets API"""
    creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON no configurado")
    
    # Decodificar base64 si es necesario
    import base64
    try:
        creds_dict = json.loads(base64.b64decode(creds_json))
    except:
        creds_dict = json.loads(creds_json)
    
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    return build('sheets', 'v4', credentials=creds)

def append_to_sheet(sheet_name, values):
    """Agregar fila a una hoja"""
    service = get_sheets_client()
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
    
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A:Z',
        valueInputOption='RAW',
        body={'values': [values]}
    ).execute()

def append_many_rows(sheet_name, rows):
    """Agregar múltiples filas en una sola request"""
    
    if not rows:
        return
    
    service = get_sheets_client()
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
    
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A:Z',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': rows}
    ).execute()

def get_sheet_data(sheet_name):
    """Obtener todos los datos de una hoja"""
    service = get_sheets_client()
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A:Z'
    ).execute()
    
    return result.get('values', [])

def clean_old_offers(days=30):
    """Eliminar ofertas sin actualización > N días (por defecto 30)
    
    Nota: Google Sheets no tiene una forma simple de borrar filas específicas.
    Esta función retorna las ofertas que deberian ser borradas para que
    GitHub Actions las elimine con un script custom si es necesario.
    """
    try:
        rows = get_sheet_data('ofertas')
        if not rows or len(rows) < 2:
            return 0
        
        headers = rows[0]
        if 'updated_at' not in headers:
            return 0
            
        updated_at_idx = headers.index('updated_at')
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        count_to_delete = 0
        for row in rows[1:]:
            if len(row) > updated_at_idx and row[updated_at_idx]:
                if row[updated_at_idx] < cutoff_date:
                    count_to_delete += 1
        
        return count_to_delete
    except Exception as e:
        print(f"[ERROR] Error al contar ofertas viejas: {str(e)}")
        return 0


def update_offer_in_sheet(codigo_externo, updated_values):
    """Actualizar una oferta existente en Google Sheets
    
    Nota: Google Sheets API no tiene UPDATE directo.
    Se recomienda usar gspread o implementar con batchUpdate.
    Por ahora, simplemente registramos que debería actualizarse.
    """
    try:
        rows = get_sheet_data('ofertas')
        headers = rows[0]
        codigo_idx = headers.index('codigo_externo')
        
        for i, row in enumerate(rows[1:], start=2):
            if len(row) > codigo_idx and row[codigo_idx] == codigo_externo:
                # Encontrada la fila
                return i  # Retorna la fila que debería actualizarse
        
        return None  # No encontrada
    except Exception as e:
        print(f"[ERROR] Error al buscar oferta: {str(e)}")
        return None