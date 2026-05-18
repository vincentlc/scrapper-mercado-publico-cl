# � GUÍA COMPLETA: ScrapMercadoPublico

**Última actualización:** Mayo 18, 2026  
**Status:** ✅ Funcional (Alertas email en construcción)

---

## 📋 Tabla de Contenidos

1. [Estado Actual](#estado-actual)
2. [Cómo Reproducir](#cómo-reproducir)
3. [Arquitectura](#arquitectura)
4. [Base de Datos](#base-de-datos)
5. [API Endpoints](#api-endpoints)
6. [Frontend](#frontend)
7. [Scripts](#scripts)
8. [Troubleshooting](#troubleshooting)
9. [Plan de Alertas Email](#plan-de-alertas-email)

---

## 🎯 Estado Actual

### ✅ Implementado y Funcionando

**Scraper:**
- ✓ Descarga automática desde Mercado Público (cada 6h vía GitHub Actions)
- ✓ Parseo inteligente de CSV (detecta encoding, delimitador, headers)
- ✓ Normalización de 16 columnas de datos
- ✓ Mapeo automático de columnas variables
- ✓ Deduplicación de ofertas

**Base de Datos:**
- ✓ SQLite con schema robusto
- ✓ Migraciones automáticas
- ✓ índices para búsqueda rápida
- ✓ Limpieza automática (>30 días)

**Backend API:**
- ✓ FastAPI con CORS habilitado
- ✓ GET `/api/offers` con filtros avanzados
- ✓ GET `/api/filters/options` para dropdowns
- ✓ POST `/api/update-offers` para actualización manual
- ✓ Paginación (50-200 registros por página)

**Frontend:**
- ✓ Tabla responsive con todas las ofertas
- ✓ Cards para móvil
- ✓ Código clickeable → abre en Mercado Público
- ✓ Búsqueda por palabra clave
- ✓ 11+ filtros combinables
- ✓ **NUEVO:** Filtro por días para cierre (min/max)
- ✓ **NUEVO:** Nombre formateado (con tipo UTM en <100 UTM)
- ✓ **NUEVO:** Fecha de cierre + Días restantes

### ⏳ En Construcción

- ⏳ Sistema de alertas por email (Mailgun)
- ⏳ Registro de usuarios
- ⏳ Filtros guardados por usuario
- ⏳ Suscripción a alertas

---

## 🚀 Cómo Reproducir

### Requisitos Mínimos

```bash
- Python 3.9+
- pip o conda
- Git
- Conexión a internet
```

### Paso 1: Clonar Proyecto

```bash
git clone https://github.com/vincentlc/scrapper-mercado-publico-cl.git
cd ScrapMercadoPublico
```

### Paso 2: Crear Entorno Virtual

```bash
# Linux / Mac
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### Paso 3: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Ejecutar Scraper (Opcional)

```bash
# Descarga ofertas desde Mercado Público y guarda en SQLite
python -m scripts.update_offers

# Resultado:
# ✓ app/data/licitaciones.db creada
# ✓ ~4600 ofertas descargadas
# ✓ data/update_trace.log con detalles
```

### Paso 5: Iniciar Backend

```bash
# Terminal 1
python -m uvicorn app.main:app --reload --port 8000

# Output:
# Uvicorn running on http://127.0.0.1:8000
```

### Paso 6: Servir Frontend

```bash
# Terminal 2
cd docs
python -m http.server 8080

# Abierto en http://localhost:8080
```

### Paso 7: Usar la Aplicación

1. Abre http://localhost:8080 en tu navegador
2. Busca por palabra clave, filtro, rango UTM
3. Haz clic en un código para ver en Mercado Público

---

## 🏗 Arquitectura

### Componentes

```
┌─────────────────────────────────────────────────────┐
│                  MERCADO PÚBLICO                     │
│            (ZIP CSV actualizado cada 6h)             │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │  scripts/update_offers.py  │
    │  - Descarga ZIP            │
    │  - Parsea CSV              │
    │  - Normaliza datos         │
    │  - Valida & limpia         │
    └────────────┬───────────────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │  app/data/licitaciones.db  │
    │  (SQLite, ~4600 registros) │
    └────────────┬───────────────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │   app/main.py (FastAPI)    │
    │  - GET /api/offers         │
    │  - GET /api/filters        │
    │  - POST /api/update-offers │
    └────────────┬───────────────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │   docs/app.js (Frontend)   │
    │  - Tabla + Cards           │
    │  - Filtros interactivos    │
    │  - Búsqueda en tiempo real │
    └────────────────────────────┘
```

### Stack Tech Actual

| Componente | Tecnología | Descripción |
|-----------|------------|-------------|
| **Scraper** | Python 3.9+ | Descarga y procesa CSV |
| **BD** | SQLite | Almacenamiento local |
| **Backend** | FastAPI 0.115 | API REST |
| **Frontend** | HTML/CSS/JS | Vanilla (sin frameworks) |
| **Hosting** | Local/Vercel | Desarrollo local, deploy en Vercel |

---

## 💾 Base de Datos

### Tabla: `offers`

```sql
CREATE TABLE offers (
    codigo_externo TEXT PRIMARY KEY,
    nombre TEXT,
    descripcion TEXT,
    descripcion_producto TEXT,
    organismo TEXT,
    estado TEXT,
    region TEXT,
    comuna TEXT,
    tipo_oferta TEXT,
    moneda TEXT,
    monto_estimado REAL,
    fecha_publicacion TEXT,
    fecha_cierre TEXT,
    link TEXT,
    raw_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Ejemplo de Registro

```json
{
  "codigo_externo": "681563-8-LE26",
  "nombre": "SERVICIO DE MANTENCION DE AREAS VERDES COMUNA DE RÁNQUIL",
  "descripcion": "EFECTUAR LOS TRABAJOS EN SERVICIOS DE MANTENCION...",
  "descripcion_producto": "Servicios de cuidado de céspedes",
  "organismo": "Ilustre Municipalidad de Ranquil",
  "estado": "Publicada",
  "region": "Región del Ñuble",
  "comuna": "Ránquil",
  "tipo_oferta": "Licitación Pública inferior a 100 UTM (Compra Ágil)",
  "moneda": "CLP",
  "monto_estimado": 15000000,
  "fecha_publicacion": "2026-05-17T22:26:42",
  "fecha_cierre": "2026-05-27T15:17:00",
  "link": "http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion=681563-8-LE26",
  "updated_at": "2026-05-18T12:45:30"
}
```

### Campos Enriquecidos (Frontend)

El backend agrega estos campos calculados:

```json
{
  "nombre_formateado": "SERVICIO DE MANTENCION (Compra Ágil)",
  "dias_para_cierre": 9
}
```

---

## 🔗 API Endpoints

### GET `/api/offers` - Listar ofertas con filtros

**URL:**
```
http://localhost:8000/api/offers?keyword=software&region=Metropolitana&page=1&page_size=20
```

**Parámetros Query:**

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `keyword` | string | Busca en nombre, descripción, producto, código | `software` |
| `tipo_oferta` | string | Tipo exacto | `Licitación Pública...` |
| `utm_range` | string | Rango UTM | `lt100`, `100_1000`, `gt5000` |
| `estado` | string | Estado exacto | `Publicada` |
| `organismo` | string | Organismo exacto | `Municipalidad` |
| `region` | string | Región exacta | `Metropolitana` |
| `comuna` | string | Comuna exacta | `Santiago` |
| `min_monto` | number | Monto mínimo | `1000000` |
| `max_monto` | number | Monto máximo | `50000000` |
| `start_date` | ISO date | Desde publicación | `2026-05-01` |
| `end_date` | ISO date | Hasta publicación | `2026-05-31` |
| `start_close_date` | ISO date | Desde cierre | `2026-05-20` |
| `end_close_date` | ISO date | Hasta cierre | `2026-06-30` |
| `min_days_to_close` | number | Mínimo días para cierre | `5` |
| `max_days_to_close` | number | Máximo días para cierre | `15` |
| `page` | number | Número de página (default: 1) | `1` |
| `page_size` | number | Registros por página (50-200, default: 50) | `100` |

**Respuesta:**

```json
{
  "items": [
    {
      "codigo_externo": "681563-8-LE26",
      "nombre": "SERVICIO DE MANTENCION...",
      "nombre_formateado": "SERVICIO DE MANTENCION (Compra Ágil)",
      "descripcion": "...",
      "organismo": "Ilustre Municipalidad de Ránquil",
      "fecha_cierre": "2026-05-27T15:17:00",
      "dias_para_cierre": 9,
      "link": "http://www.mercadopublico.cl/...",
      ...
    }
  ],
  "total": 4656,
  "page": 1,
  "page_size": 50
}
```

### GET `/api/filters/options` - Valores disponibles para filtros

**URL:**
```
http://localhost:8000/api/filters/options
```

**Respuesta:**

```json
{
  "tipo_oferta": [
    "Licitación Pública inferior a 100 UTM (Compra Ágil)",
    "Licitación Pública igual o superior a 100 UTM e inferior a 1.000 UTM (LP)",
    ...
  ],
  "estado": ["Publicada", "Cerrada", "Suspendida"],
  "organismo": ["Municipalidad X", "Empresa Y", ...],
  "region": ["Región del Ñuble", "Metropolitana", ...],
  "comuna": ["Santiago", "Ránquil", ...]
}
```

### POST `/api/update-offers` - Actualizar ofertas manualmente

**URL:**
```
http://localhost:8000/api/update-offers
```

**Respuesta:**

```json
{
  "new_count": 145,
  "updated_count": 0,
  "deleted_count": 0,
  "total_matches": 0,
  "total_alerts_sent": 0
}
```

---

## 🎨 Frontend

### Características

1. **Búsqueda en tiempo real**
   - Escribe palabra clave
   - Filtra por código, nombre, descripción

2. **Filtros Combinables**
   - Rango UTM (Compra Ágil, LP)
   - Estado, Organismo, Región
   - Fecha de publicación
   - Monto estimado
   - **Días para cierre** (nuevo)

3. **Visualización**
   - Tabla desktop con ordenamiento
   - Cards responsivos para móvil
   - Código clickeable (abre en Mercado Público)
   - Expandable text para descripciones largas
   - **Nombre formateado con tipo UTM**
   - **Fecha de cierre + Días restantes**

### Cómo Usar

```
1. Abre http://localhost:8080
2. Ingresa palabra clave (ej: "software")
3. Selecciona filtros (ej: región, tipo oferta)
4. Ajusta rango de días para cierre (ej: 5-15 días)
5. Haz clic en código para ir a Mercado Público
```

---

## 🔧 Scripts

### `scripts/update_offers.py`

Descarga y procesa ofertas.

```bash
# Uso
python -m scripts.update_offers

# Hace:
# 1. Descarga ZIP de Mercado Público
# 2. Extrae CSV
# 3. Detecta encoding/delimitador
# 4. Parsea y normaliza columnas
# 5. Valida datos
# 6. Inserta en SQLite
# 7. Genera reporte

# Output:
# - app/data/licitaciones.db (creada/actualizada)
# - data/update_trace.log (detalles)
```

### `scripts/init_google_sheets.py`

Valida/inicializa headers en Google Sheets (opcional).

```bash
python -m scripts.init_google_sheets
```

### Tests

```bash
# Ejecutar todos
pytest

# Solo tests de API
pytest tests/test_api_filters.py -v

# Solo tests de scraper
pytest tests/test_update_offers.py -v

# Con cobertura
pytest --cov=app --cov=scripts
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

**Solución:**
```bash
# Asegúrate de estar en directorio raíz
pwd  # debe terminar en "ScrapMercadoPublico"

# Y ejecutar con -m
python -m uvicorn app.main:app --reload
```

### "No module named 'fastapi'"

**Solución:**
```bash
# Instalar dependencias
pip install -r requirements.txt

# Verificar
python -c "import fastapi; print(fastapi.__version__)"
```

### "Error: Could not detect CSV header"

**Solución:**
```bash
# El CSV de Mercado Público cambió formato
# Verifica manualmente:
python << 'EOF'
from scripts.update_offers import download_csv
try:
    offers, filename = download_csv()
    print(f"✓ CSV descargado: {filename}")
    print(f"✓ Registros: {len(offers)}")
    print(f"✓ Columnas: {list(offers[0].keys())}")
except Exception as e:
    print(f"✗ Error: {e}")
EOF
```

### "Base de datos vacía"

**Solución:**
```bash
# 1. Verificar si existe
ls -la app/data/licitaciones.db

# 2. Ejecutar scraper
python -m scripts.update_offers

# 3. Contar registros
sqlite3 app/data/licitaciones.db "SELECT COUNT(*) FROM offers;"
```

### "Port 8000 already in use"

**Solución:**
```bash
# Usar otro puerto
python -m uvicorn app.main:app --port 8001

# O matar proceso existente
lsof -ti :8000 | xargs kill -9
```

---

## 📧 Plan de Alertas Email

### Estado: ⏳ En Construcción

**Por qué no está funcionando:**
- Mailgun API integrada pero sin flujo completo
- Falta sistema de suscripción de usuarios
- Falta detección de nuevas ofertas vs filtro

**Pasos necesarios (ver PLAN_ALERTAS.md):**

1. **Fase 1: Backend de Suscripción**
   - Endpoint POST `/api/subscribe` (email + filtros)
   - Guardar usuarios en BD
   - Generar token de desuscripción

2. **Fase 2: Detección de Cambios**
   - Comparar ofertas nuevas vs filtros guardados
   - Identificar matches
   - Preparar contenido de email

3. **Fase 3: Envío Mailgun**
   - Integrar Mailgun API
   - Enviar email con HTML formateado
   - Registrar estado en BD

4. **Fase 4: Desuscripción**
   - Endpoint GET `/api/unsubscribe/:token`
   - Marcar usuario como inactivo
   - Enviar confirmación

**Próximas acciones:**
- [ ] Crear PLAN_ALERTAS.md detallado
- [ ] Implementar endpoints de suscripción
- [ ] Crear tabla `users` en BD
- [ ] Implementar lógica de matching
- [ ] Integrar Mailgun

---

## 📚 Archivos Importantes

```
ScrapMercadoPublico/
├── README.md                           ← Guía rápida (LEEME PRIMERO)
├── documentation/GUIA_COMPLETA.md      ← Este archivo
├── SOLUCION_DESALINEAMIENTO.md         ← Fix de columnas
├── PLAN_ALERTAS.md                     ← (Próximo a crear)
│
├── app/
│   ├── main.py                         ← FastAPI endpoints
│   ├── db.py                           ← Init BD + migraciones
│   ├── query.py                        ← Lógica de filtros
│   └── data/licitaciones.db           ← Base de datos SQLite
│
├── scripts/
│   ├── update_offers.py                ← Scraper principal
│   ├── helpers.py                      ← Utilidades
│   └── init_google_sheets.py          ← Validador Sheets
│
├── docs/
│   ├── index.html                      ← Frontend
│   ├── app.js                          ← Lógica JS
│   └── styles.css                      ← Estilos
│
├── tests/
│   ├── test_api_filters.py
│   └── test_update_offers.py
│
└── requirements.txt                    ← Dependencias Python
```

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa [Troubleshooting](#troubleshooting)
2. Revisa logs:
   ```bash
   tail -f data/update_trace.log
   ```
3. Abre issue en GitHub
4. Contacta: [LinkedIn](https://www.linkedin.com/in/vincent-lec/)

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
python-decouple==3.8
gspread==5.12.0
```

Ejecutar:
```bash
pip install -r requirements.txt
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
const API_BASE = 'https://scrapper-mercado-publico-cl.vercel.app';

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
