#!/usr/bin/env python3
"""
Script para inicializar Google Sheets con los headers correctos.

Uso:
    python -m scripts.init_google_sheets
"""

import json
import os
import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.helpers import get_sheets_client


def ensure_headers():
    """Asegurar que Google Sheets tenga los headers correctos"""
    
    try:
        service = get_sheets_client()
        spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
        
        if not spreadsheet_id:
            print("[ERROR] GOOGLE_SHEETS_ID no configurado")
            return False
        
        # Headers esperados para cada hoja
        sheets_config = {
            'ofertas': [
                'codigo_externo',
                'nombre',
                'descripcion',
                'descripcion_producto',
                'organismo',
                'estado',
                'region',
                'comuna',
                'tipo_oferta',
                'moneda',
                'monto_estimado',
                'fecha_publicacion',
                'fecha_cierre',
                'link',
                'raw_json',
                'created_at',
                'updated_at',
                'scraped_at',
                'dias_que_quedan',
            ],
            'users': [
                'user_id',
                'email',
                'unsub_token',
                'is_active',
                'created_at',
                'last_alert_sent',
                'metadata'
            ],
            'user_filters': [
                'filter_id',
                'user_id',
                'filter_name',
                'filter_json',
                'is_active',
                'created_at',
                'updated_at',
                'last_matched_at'
            ],
            'notification_runs': [
                'run_id',
                'executed_at',
                'status',
                'total_new_offers',
                'total_updated_offers',
                'total_deleted_offers',
                'total_matches',
                'total_alerts_sent',
                'error_message',
                'duration_seconds'
            ],
            'temp_emails_queue': [
                'queue_id',
                'user_id',
                'filter_id',
                'matching_offers',
                'created_at',
                'sent_at',
                'status'
            ]
        }
        
        all_good = True
        
        for sheet_name, expected_headers in sheets_config.items():
            print(f"\n[INFO] Validando hoja '{sheet_name}'...")
            
            try:
                # Obtener la primera fila (headers)
                response = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f'{sheet_name}!A1:Z1'
                ).execute()
                
                current_headers = response.get('values', [[]])[0]
                
                if not current_headers:
                    print(f"  [WARN] Hoja vacía. Insertando headers...")
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'{sheet_name}!A1:Z1',
                        valueInputOption='RAW',
                        body={'values': [expected_headers]}
                    ).execute()
                    print(f"  [OK] Headers insertados")
                    
                elif current_headers != expected_headers:
                    print(f"  [WARN] Headers incorrectos!")
                    print(f"    Esperado: {expected_headers[:5]}...")
                    print(f"    Actual  : {current_headers[:5]}...")
                    print(f"  [WARN] Por favor, actualiza manualmente o ejecuta:")
                    print(f"        - Abre https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
                    print(f"        - En la hoja '{sheet_name}', reemplaza la primera fila con:")
                    print(f"        {chr(9).join(expected_headers)}")
                    all_good = False
                else:
                    print(f"  [OK] Headers correctos")
                    
            except Exception as e:
                print(f"  [ERROR] Error al validar: {e}")
                all_good = False
        
        if all_good:
            print("\n[SUCCESS] Todas las hojas están correctamente configuradas!")
        else:
            print("\n[WARN] Algunas hojas necesitan correcciones manuales")
        
        return all_good
        
    except Exception as e:
        print(f"[ERROR] Error al conectar con Google Sheets: {e}")
        print("Asegúrate de que GOOGLE_SHEETS_ID y GOOGLE_SERVICE_ACCOUNT_JSON estén configurados")
        return False


if __name__ == '__main__':
    success = ensure_headers()
    sys.exit(0 if success else 1)
