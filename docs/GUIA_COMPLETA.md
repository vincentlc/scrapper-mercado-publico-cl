# 🚀 GUÍA COMPLETA: Migración a Arquitectura Serverless (100% Online)

**Tabla de Contenidos:**
- [Paso 1: Schema Google Sheets](#paso-1-schema-google-sheets)
- [Paso 2: Google Cloud Setup](#paso-2-google-cloud-setup)
- [Paso 3: Vercel Functions (Backend)](#paso-3-vercel-functions-backend)
- [Paso 4: Migración Script Python](#paso-4-migración-script-python)
- [Paso 5: GitHub Actions Workflow](#paso-5-github-actions-workflow)
- [Paso 6: Frontend Deploy](#paso-6-frontend-deploy)
- [Paso 7: Testing & Validación](#paso-7-testing--validación)

---

# PASO 1: Schema Google Sheets

## Descripción
Crear la base de datos centralizada en Google Sheets con 5 hojas para almacenar: ofertas, usuarios, filtros, histórico de ejecuciones y cola de emails.

## Tiempo: 15 minutos

### 1.1 Crear Google Sheets Document

1. Ve a [Google Sheets](https://sheets.google.com)
2. Clic en **"Nuevo"** → **"Spreadsheet"**
3. Nombra: **"ScrapMercadoPublico-BD"**

### 1.2 Crear las 5 Hojas

Por defecto hay "Sheet1". Renómbrala y agrega las otras:

- Renombra a: **`ofertas`**
- Agrega: **`users`**
- Agrega: **`user_filters`**
- Agrega: **`notification_runs`**
- Agrega: **`temp_emails_queue`**

### 1.3 Copiar Headers (Copy & Paste)

Para cada hoja, copia estos headers en celda A1:

#### Hoja: ofertas
```
codigo_externo	nombre	descripcion	descripcion_producto	organismo	estado	region	comuna	tipo_oferta	moneda	monto_estimado	fecha_publicacion	fecha_cierre	link	raw_json	created_at	updated_at	scraped_at
```

#### Hoja: users
```
user_id	email	unsub_token	is_active	created_at	last_alert_sent	metadata
```

#### Hoja: user_filters
```
filter_id	user_id	filter_name	filter_json	is_active	created_at	updated_at	last_matched_at
```

#### Hoja: notification_runs
```
run_id	executed_at	status	total_new_offers	total_updated_offers	total_deleted_offers	total_matches	total_alerts_sent	error_message	duration_seconds
```

#### Hoja: temp_emails_queue
```
queue_id	user_id	filter_id	matching_offers	created_at	sent_at	status
```

### 1.4 Guardar SPREADSHEET_ID

En la URL del Sheets:
```
https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
```

**Copia ese ID** - lo necesitarás en Paso 2.

### ✅ Checklist Paso 1
- [ ] Google Sheets creado
- [ ] 5 hojas creadas y renombradas
- [ ] Headers pegados en cada hoja
- [ ] SPREADSHEET_ID guardado
- [ ] Commit: `git commit -m "docs: confirm PASO 1 complete"`

---

# PASO 2: Google Cloud Setup

## Descripción
Crear credenciales de Google Cloud para que GitHub Actions pueda acceder a Google Sheets.

## Tiempo: 10-15 minutos

### 2.1 Crear Proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Logeate con tu cuenta Google
3. Clic en selector de proyecto (arriba) → **"NEW PROJECT"**
4. Nombra: `ScrapMercadoPublico-API`
5. Clic en **"CREATE"**
6. Espera 1-2 minutos

### 2.2 Habilitar Google Sheets API

1. En la barra de búsqueda superior, busca: **"Google Sheets API"**
2. En resultados, clic en **"Google Sheets API"**
3. Clic en botón azul **"ENABLE"**
4. Espera a que se habilite (~5 seg)

### 2.3 Crear Service Account

1. Ve a **APIs & Services** → **Credentials** (o busca "Service Accounts")
2. Clic en **"Service Accounts"**
3. Clic en **"CREATE SERVICE ACCOUNT"**
4. Rellena:
   - **Service account name:** `scraper-mercado-publico`
   - **Service account ID:** (auto-llenado)
   - **Description:** "Service account para scraping de licitaciones"
5. Clic en **"CREATE AND CONTINUE"**

### 2.4 Otorgar Rol "Editor"

1. En "Grant this service account access to project"
2. Busca y selecciona rol: **"Editor"**
3. Clic en **"CONTINUE"**
4. Clic en **"DONE"**

### 2.5 Generar JSON Key

1. Serás redirigido a "Service Accounts"
2. Clic en el nombre de tu service account: **`scraper-mercado-publico`**
3. Ve a pestaña **"KEYS"**
4. Clic en **"ADD KEY"** → **"Create new key"**
5. Selecciona **"JSON"**
6. Clic en **"CREATE"**
7. **Se descarga automáticamente** un archivo JSON

### 2.6 Compartir Google Sheets con Service Account

1. Abre tu Google Sheets: **"ScrapMercadoPublico-BD"**
2. Clic en **"Share"** (arriba a la derecha)
3. Copia el `client_email` del JSON descargado (busca: `"client_email": "..."`)
4. Pégalo en el campo de email de Share
5. Selecciona **"Editor"** como rol
6. Clic en **"Share"**
7. Si aparece advertencia, clic en **"Share anyway"**

### 2.7 Convertir JSON a Base64

**En Linux/Mac:**
```bash
base64 < /path/to/downloaded/file.json | tr -d '\n'
```

**En Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("C:\path\to\file.json"))
```

Copia la salida.

### 2.8 Guardar Secretos en GitHub

1. Ve a tu repo: https://github.com/vincentlc/scrapper-mercado-publico-cl
2. **Settings** → **Secrets and variables** → **Actions**
3. Clic en **"New repository secret"**
4. Crea dos secretos:

**Secreto 1: GOOGLE_SHEETS_ID**
- Name: `GOOGLE_SHEETS_ID`
- Secret: Tu SPREADSHEET_ID (ej: `1a2b3c4d5e6f...`)

**Secreto 2: GOOGLE_SERVICE_ACCOUNT_JSON**
- Name: `GOOGLE_SERVICE_ACCOUNT_JSON`
- Secret: El base64 del JSON

### ✅ Checklist Paso 2
- [ ] Proyecto Google Cloud creado
- [ ] Google Sheets API habilitada
- [ ] Service Account creada
- [ ] JSON descargado
- [ ] Google Sheets compartido con service account
- [ ] JSON convertido a base64
- [ ] Secretos guardados en GitHub
- [ ] Commit: `git commit -m "docs: confirm PASO 2 complete"`

---

# PASO 3: Vercel Functions (Backend)

## Descripción
Crear API backend serverless en Vercel que maneje: registro de usuarios, gestión de filtros, desuscripción y lectura de ofertas.

## Tiempo: 30-40 minutos

### 3.1 Conectar Repositorio a Vercel

1. Ve a [Vercel](https://vercel.com/)
2. Logeate o crea cuenta
3. Clic en **"New Project"** → **"Import Git Repository"**
4. Selecciona `vincentlc/scraper-mercado-publico-cl`
5. Configura:
   - **Project Name:** `scraper-mercado-publico`
   - **Framework:** Other
   - **Root Directory:** `vercel-functions/`
6. Clic en **"Deploy"**

### 3.2 Crear Estructura de Vercel Functions

En tu repositorio local, crea esta carpeta:

```
vercel-functions/
├── api/
│   ├── offers.js          ← GET /api/offers (público)
│   ├── register.js        ← POST /api/register (nuevo usuario)
│   ├── filters.js         ← POST/GET /api/filters (gestión de filtros)
│   ├── unsubscribe.js     ← GET /api/unsubscribe (desuscribirse)
│   └── utils/
│       ├── google-sheets.js
│       ├── mailgun.js
│       └── auth.js
└── package.json
```

### 3.3 Verificar Dependencias

✅ Ya está configurado en `vercel-functions/package.json`

Vercel automáticamente:
1. Detecta la carpeta `vercel-functions/`
2. Lee `package.json`
3. Instala dependencias
4. Despliega los endpoints en `/api/*`

### 3.4 Verificar Archivos de Utilidad

✅ Ya existen:
- `vercel-functions/api/utils/google-sheets.js` - Cliente de Google Sheets
- `vercel-functions/api/utils/mailgun.js` - Envío de emails
- `vercel-functions/api/utils/auth.js` - Validaciones CORS

### 3.5 Verificar Endpoints

✅ Ya existen los 4 endpoints:
- `offers.js` - GET /api/offers
- `register.js` - POST /api/register  
- `filters.js` - POST/GET /api/filters
- `unsubscribe.js` - GET /api/unsubscribe


### 3.9 Configurar Environment Variables en Vercel

1. Ve a [Vercel Dashboard](https://vercel.com/dashboard)
2. Selecciona tu proyecto: `scraper-mercado-publico`
3. **Settings** → **Environment Variables**
4. Agrega estas variables:

| Variable | Valor |
|----------|-------|
| `GOOGLE_SHEETS_ID` | Tu SPREADSHEET_ID (ej: `1a2b3c...`) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | El JSON codificado en base64 |
| `MAILGUN_API_KEY` | Tu API key de Mailgun |
| `MAILGUN_DOMAIN` | Tu dominio de Mailgun |

5. Clic en **"Save"**
6. Vercel redesplegará automáticamente con las nuevas variables

### ✅ Checklist Paso 3
- [ ] Repositorio importado en Vercel
- [ ] Carpeta `vercel-functions/` detectada
- [ ] Dependencias en `package.json`
- [ ] 4 endpoints implementados (offers, register, filters, unsubscribe)
- [ ] 4 archivos de utilidad creados (google-sheets, mailgun, auth, .gitignore)
- [ ] Deployment inicial completado (URL: `https://scraper-mercado-publico.vercel.app`)
- [ ] Environment variables configuradas en Vercel
- [ ] Commit: `git add vercel-functions && git commit -m "feat: add Vercel Functions backend (PASO 3)"`
- [ ] Push: `git push origin main`

---

# PASO 4: Migración Script Python

## Descripción
Adaptar el script `scripts/update_offers.py` para escribir en Google Sheets, implementar lógica de alertas y limpieza de datos.

## Tiempo: 45-60 minutos

### 4.1 Instalar Dependencias

En `requirements.txt`, agregar:

```
requests==2.31.0
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.2.0
google-api-python-client==2.108.0
mailgun-validator==0.5.0
python-decouple==3.8
gspread==5.12.0
```

Ejecutar:
```bash
pip install -r requirements.txt
```

### 4.2 Crear `scripts/helpers.py`

```python
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

def get_sheet_data(sheet_name):
    """Obtener todos los datos de una hoja"""
    service = get_sheets_client()
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A:Z'
    ).execute()
    
    return result.get('values', [])

def clean_old_offers():
    """Borrar ofertas sin actualización > 30 días"""
    service = get_sheets_client()
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')
    
    rows = get_sheet_data('ofertas')
    headers = rows[0]
    updated_at_idx = headers.index('updated_at')
    
    cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
    rows_to_delete = []
    
    for i, row in enumerate(rows[1:], start=2):  # start=2 porque row 1 es header
        if len(row) > updated_at_idx and row[updated_at_idx] < cutoff_date:
            rows_to_delete.append(i)
    
    # Borrar filas (de atrás hacia adelante para no mover índices)
    for row_idx in reversed(rows_to_delete):
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'deleteDimension': {
                        'range': {
                            'sheetId': get_sheet_id('ofertas'),
                            'dimension': 'ROWS',
                            'startIndex': row_idx - 1,
                            'endIndex': row_idx
                        }
                    }
                }]
            }
        ).execute()
    
    return len(rows_to_delete)
```

### 4.3 Adaptar `scripts/update_offers.py`

```python
# (Al inicio del archivo, agregar)
import os
import json
from datetime import datetime
from scripts.helpers import (
    append_to_sheet, get_sheet_data, clean_old_offers
)

# Modificar la función principal:

def update_offers():
    """Descargar ofertas de Mercado Público y guardar en Google Sheets"""
    
    try:
        print("[INFO] Iniciando actualización de ofertas...")
        
        # 1. Descargar datos (código existente)
        offers_data = download_from_mercado_publico()  # Tu código actual
        
        # 2. Procesar y insertar en Sheets
        new_count = 0
        updated_count = 0
        
        existing_offers = get_sheet_data('ofertas')
        existing_codes = set(row[0] for row in existing_offers[1:])
        
        for offer in offers_data:
            values = [
                offer.get('codigo_externo', ''),
                offer.get('nombre', ''),
                offer.get('descripcion', ''),
                offer.get('descripcion_producto', ''),
                offer.get('organismo', ''),
                offer.get('estado', ''),
                offer.get('region', ''),
                offer.get('comuna', ''),
                offer.get('tipo_oferta', ''),
                offer.get('moneda', ''),
                offer.get('monto_estimado', ''),
                offer.get('fecha_publicacion', ''),
                offer.get('fecha_cierre', ''),
                offer.get('link', ''),
                json.dumps(offer),  # raw_json
                datetime.now().isoformat(),  # created_at
                datetime.now().isoformat(),  # updated_at
                datetime.now().isoformat(),  # scraped_at
            ]
            
            if offer.get('codigo_externo') in existing_codes:
                updated_count += 1
            else:
                new_count += 1
            
            append_to_sheet('ofertas', values)
        
        # 3. Limpiar ofertas viejas (> 30 días)
        deleted_count = clean_old_offers()
        
        # 4. Ejecutar detección de filtros y alertas
        total_matches, total_alerts_sent = check_filters_and_send_alerts()
        
        # 5. Registrar ejecución en notification_runs
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        append_to_sheet('notification_runs', [
            run_id,
            datetime.now().isoformat(),
            'SUCCESS',
            new_count,
            updated_count,
            deleted_count,
            total_matches,
            total_alerts_sent,
            '',  # error_message
            120  # duration_seconds (estimado)
        ])
        
        print(f"[SUCCESS] Update completado:")
        print(f"  - Nuevas ofertas: {new_count}")
        print(f"  - Actualizadas: {updated_count}")
        print(f"  - Borradas (>30 días): {deleted_count}")
        print(f"  - Alertas enviadas: {total_alerts_sent}")
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        # Registrar error en notification_runs
        append_to_sheet('notification_runs', [
            f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            datetime.now().isoformat(),
            'ERROR',
            0, 0, 0, 0, 0,
            str(e),
            0
        ])

def check_filters_and_send_alerts():
    """Buscar coincidencias en filtros y enviar alertas"""
    
    total_matches = 0
    total_alerts_sent = 0
    
    # Obtener usuarios activos y sus filtros
    users = get_sheet_data('users')
    user_filters = get_sheet_data('user_filters')
    offers = get_sheet_data('ofertas')
    
    headers_users = users[0]
    headers_filters = user_filters[0]
    headers_offers = offers[0]
    
    email_idx = headers_users.index('email')
    user_id_idx_u = headers_users.index('user_id')
    
    # Para cada usuario activo
    for user_row in users[1:]:
        if len(user_row) <= email_idx or user_row[email_idx + 2] != 'TRUE':
            continue  # Usuario no activo
        
        user_id = user_row[user_id_idx_u]
        user_email = user_row[email_idx]
        
        # Obtener sus filtros activos
        user_active_filters = [
            row for row in user_filters[1:]
            if len(row) > 1 and row[1] == user_id and len(row) > 4 and row[4] == 'TRUE'
        ]
        
        matching_offers = []
        
        for filter_row in user_active_filters:
            filter_json = json.loads(filter_row[3])  # filter_json está en índice 3
            
            # Buscar ofertas que coincidan
            for offer_row in offers[1:]:
                if apply_filter(offer_row, headers_offers, filter_json):
                    matching_offers.append(offer_row)
                    total_matches += 1
        
        # Si hay coincidencias, enviar email
        if matching_offers:
            send_email_alerts(user_email, matching_offers, headers_offers)
            total_alerts_sent += 1
    
    return total_matches, total_alerts_sent

def apply_filter(offer_row, headers, filter_json):
    """Verificar si una oferta coincide con los criterios del filtro"""
    
    offer_dict = dict(zip(headers, offer_row))
    
    # Keyword (búsqueda full-text)
    if filter_json.get('keyword'):
        keyword = filter_json['keyword'].lower()
        search_fields = ['nombre', 'descripcion', 'descripcion_producto']
        if not any(keyword in offer_dict.get(f, '').lower() for f in search_fields):
            return False
    
    # Filtros de igualdad
    for field in ['estado', 'region', 'tipo_oferta', 'organismo', 'comuna']:
        if filter_json.get(field):
            if offer_dict.get(field) != filter_json[field]:
                return False
    
    # Rangos de monto
    if filter_json.get('min_monto'):
        try:
            if float(offer_dict.get('monto_estimado', 0)) < filter_json['min_monto']:
                return False
        except:
            pass
    
    if filter_json.get('max_monto'):
        try:
            if float(offer_dict.get('monto_estimado', 0)) > filter_json['max_monto']:
                return False
        except:
            pass
    
    return True

def send_email_alerts(user_email, offers, headers):
    """Enviar email con ofertas coincidentes"""
    
    try:
        # Usar Mailgun o Gmail API
        # Implementar según tu configuración
        print(f"[ALERT] Enviando email a {user_email} ({len(offers)} ofertas)")
        # ... código de envío ...
    except Exception as e:
        print(f"[ERROR] Fallo al enviar email: {str(e)}")

if __name__ == '__main__':
    update_offers()
```

### 4.4 Variables de Entorno

Crear archivo `.env` (no versionado):

```
GOOGLE_SHEETS_ID=tu_spreadsheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
MAILGUN_API_KEY=tu_api_key
MAILGUN_DOMAIN=tu_domain
```

### ✅ Checklist Paso 4
- [ ] Dependencias en `requirements.txt`
- [ ] `scripts/helpers.py` creado
- [ ] `scripts/update_offers.py` adaptado
- [ ] `.env` creado (NO versionado)
- [ ] Testeado localmente
- [ ] Commit: `git add scripts/ && git commit -m "feat: adapt Python script for Google Sheets (PASO 4)"`

---

# PASO 5: GitHub Actions Workflow

## Descripción
Crear workflow automático que ejecute el scraper cada 6 horas.

## Tiempo: 20 minutos

### 5.1 Crear Estructura

```
.github/
└── workflows/
    └── update-offers.yml
```

### 5.2 Crear `.github/workflows/update-offers.yml`

```yaml
name: Update Offers (Every 6 hours)

on:
  schedule:
    # Ejecuta cada 6 horas: 00:00, 06:00, 12:00, 18:00 UTC
    - cron: '0 */6 * * *'
  workflow_dispatch:  # Permite ejecución manual

jobs:
  scrape-and-update:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run update-offers script
        env:
          GOOGLE_SHEETS_ID: ${{ secrets.GOOGLE_SHEETS_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
          MAILGUN_API_KEY: ${{ secrets.MAILGUN_API_KEY }}
          MAILGUN_DOMAIN: ${{ secrets.MAILGUN_DOMAIN }}
        run: |
          python -m scripts.update_offers
      
      - name: Commit results (if changes)
        run: |
          git config --global user.email "scraper@github.com"
          git config --global user.name "Scraper Bot"
          git add -A
          git commit -m "data: update offers from Mercado Publico" || echo "No changes"
          git push || echo "No changes to push"
```

### 5.3 Agregar Secretos a GitHub

1. Ve a tu repositorio
2. **Settings** → **Secrets and variables** → **Actions**
3. Agrega (ya deberías tenerlos, sino):
   - `GOOGLE_SHEETS_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `MAILGUN_API_KEY`
   - `MAILGUN_DOMAIN`

### ✅ Checklist Paso 5
- [ ] Archivo `.github/workflows/update-offers.yml` creado
- [ ] Trigger configurado (cada 6 horas)
- [ ] Secretos visibles en GitHub
- [ ] Commit: `git add .github && git commit -m "ci: add GitHub Actions workflow (PASO 5)"`

---

# PASO 6: Frontend Deploy

## Descripción
Deploy de frontend estático en GitHub Pages + actualizar URLs de API.

## Tiempo: 20 minutos

### 6.1 Habilitar GitHub Pages

1. **Settings** → **Pages**
2. **Source:** Selecciona `main` branch y carpeta `/root` (o `/docs`)
3. Clic en **"Save"**

### 6.2 Adaptar Frontend (app/static/)

Actualizar `app/static/app.js`:

```javascript
// Cambiar base URL de API de FastAPI local a Vercel
const API_BASE = 'https://tu-vercel-app.vercel.app';

// GET /api/offers
async function loadOffers() {
  const params = new URLSearchParams({
    keyword: document.getElementById('keyword').value,
    region: document.getElementById('region').value,
    // ... otros filtros
  });
  
  const response = await fetch(`${API_BASE}/api/offers?${params}`);
  const data = await response.json();
  renderOffers(data.offers);
}

// POST /api/register
async function registerUser() {
  const email = prompt('Ingresa tu email:');
  const response = await fetch(`${API_BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  const data = await response.json();
  alert(`Registrado: ${data.user_id}`);
}

// POST /api/filters (crear filtro)
async function saveFilter() {
  const filterName = document.getElementById('savedFilterName').value;
  const filterJson = {
    keyword: document.getElementById('keyword').value,
    region: document.getElementById('region').value,
    // ... otros criterios
  };
  
  const response = await fetch(`${API_BASE}/api/filters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      user_id: localStorage.getItem('user_id'),
      filter_name: filterName,
      filter_json: filterJson
    })
  });
  const data = await response.json();
  console.log('Filtro guardado:', data.filter_id);
}

// GET /api/unsubscribe (desde link en email)
function unsubscribe(token) {
  fetch(`${API_BASE}/api/unsubscribe?token=${token}`)
    .then(r => r.json())
    .then(data => alert(data.message));
}
```

### 6.3 Copiar Frontend a `/docs`

```bash
mkdir -p docs
cp -r app/static/* docs/
```

### 6.4 Agregar Página de Registro

Crear `docs/register.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Registro - Oferta Pública Chile Tracker</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <header>
    <h1>Oferta Pública Chile Tracker</h1>
    <p>Regístrate para recibir alertas personalizadas</p>
  </header>
  
  <main>
    <section class="panel" style="max-width: 500px; margin: 40px auto;">
      <h2>Registro</h2>
      <form id="registerForm">
        <label>
          Email:
          <input type="email" id="email" required />
        </label>
        <div class="actions">
          <button type="submit">Registrarse</button>
        </div>
      </form>
      <div id="result"></div>
    </section>
  </main>
  
  <script>
    const API_BASE = 'https://tu-vercel-app.vercel.app';
    
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value;
      
      try {
        const response = await fetch(`${API_BASE}/api/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await response.json();
        
        if (response.ok) {
          localStorage.setItem('user_id', data.user_id);
          document.getElementById('result').innerHTML = `
            <p style="color: green;">✅ Registrado exitosamente</p>
            <p>Tu ID: ${data.user_id}</p>
            <a href="/">Volver al inicio</a>
          `;
        } else {
          throw new Error(data.error);
        }
      } catch (error) {
        document.getElementById('result').innerHTML = `
          <p style="color: red;">❌ Error: ${error.message}</p>
        `;
      }
    });
  </script>
</body>
</html>
```

### ✅ Checklist Paso 6
- [ ] GitHub Pages habilitado
- [ ] `app/static/app.js` adaptado con API_BASE
- [ ] Frontend copiado a `/docs`
- [ ] Página de registro creada
- [ ] Testear en navegador
- [ ] Commit: `git add docs/ && git commit -m "feat: add frontend to GitHub Pages (PASO 6)"`

---

# PASO 7: Testing & Validación

## Descripción
Validar que todo funciona end-to-end: registro → filtro → alerta.

## Tiempo: 30 minutos

### 7.1 Testing Manual

**Test 1: Registro de Usuario**
```bash
curl -X POST https://tu-vercel-app.vercel.app/api/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```
✅ Debería retornar `user_id` y `unsub_token`

**Test 2: Crear Filtro**
```bash
curl -X POST https://tu-vercel-app.vercel.app/api/filters \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_xxx",
    "filter_name": "Software > 1M",
    "filter_json": {
      "keyword": "software",
      "min_monto": 1000000
    }
  }'
```
✅ Debería retornar `filter_id`

**Test 3: Obtener Ofertas**
```bash
curl 'https://tu-vercel-app.vercel.app/api/offers?keyword=software&region=Metropolitana'
```
✅ Debería retornar lista de ofertas filtradas

**Test 4: Ejecutar Scraper Manualmente**
```bash
# En GitHub Actions:
1. Ve a Actions
2. Selecciona workflow "Update Offers (Every 6 hours)"
3. Clic en "Run workflow" (botón manual)
4. Verifica que se ejecute exitosamente
```
✅ Debería ver logs de scraping en GitHub Actions

**Test 5: Verificar Google Sheets**
1. Abre tu Google Sheets
2. Ve a hoja `ofertas` → Debería haber datos nuevos
3. Ve a hoja `users` → Debería ver el usuario de test
4. Ve a hoja `notification_runs` → Debería haber un registro

✅ Todos los datos correctos

### 7.2 Testing de Alertas

1. Registra un usuario con tu email real
2. Crea un filtro personalizado
3. Ejecuta scraper manualmente en GitHub Actions
4. Espera 30 segundos
5. Verifica que recibas email en tu bandeja

✅ Email recibido con ofertas que coinciden

### 7.3 Testing de Desuscripción

1. En el email de alerta, busca el link de desuscripción
2. Haz clic
3. Verifica que el usuario se marque como inactivo en Google Sheets
4. Ejecuta scraper nuevamente
5. Verifica que NO recibas más emails

✅ Usuario desuscrito exitosamente

### 7.4 Checklist Final

- [ ] Test 1: Registro de usuario (curl o web)
- [ ] Test 2: Crear filtro
- [ ] Test 3: Obtener ofertas
- [ ] Test 4: Scraper manual ejecutado
- [ ] Test 5: Google Sheets actualizado
- [ ] Test 6: Email de alerta recibido
- [ ] Test 7: Desuscripción funcionando

### 7.5 Publicar en Producción

```bash
git tag -a v1.0.0 -m "Release v1.0.0 - Serverless architecture"
git push origin v1.0.0
```

Commit final:
```bash
git commit -m "docs: complete PASO 7 - end-to-end testing

- Manual testing of all endpoints
- Email alert validation
- Unsubscribe flow tested
- All systems integrated and working
- Ready for production"
```

---

## 🎯 ¡COMPLETADO!

✅ Sistema 100% online, serverless, zero costo
✅ Multi-usuario con filtros personalizados
✅ Alertas automáticas por email
✅ Desuscripción simple
✅ Limpieza automática de datos
✅ GitHub Pages como vitrina
✅ Todo versionado en Git

🚀 **Próximos pasos opcionales:**
- [ ] Agregar autenticación (Auth0, Firebase)
- [ ] Crear dashboard de administración
- [ ] Migrar a Firebase Firestore (para >500 usuarios)
- [ ] Agregar soporte para otras fuentes de datos
- [ ] Implementar SaaS con pagos (Stripe)

---

**Documento terminado:** `docs/GUIA_COMPLETA.md`
