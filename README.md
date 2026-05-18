# 🇨🇱 Oferta Pública Chile Tracker - Scraper de Licitaciones

Sistema de scraping y análisis de licitaciones públicas de Chile desde Mercado Público. Descarga en tiempo real, filtra, busca y visualiza ofertas públicas con datos actualizados.

**Status:** ✅ Funcional (alertas por email aún en construcción)

---

## ✨ Características Actuales

✅ **Scraping Automático**
- Descarga ofertas cada 6h desde Mercado Público
- CSV con 16 columnas de datos estructurados
- Detección automática de encoding y formato

✅ **Búsqueda y Filtros Avanzados**
- Filtro por palabra clave
- Filtro por rango UTM (Compra Ágil, LP, etc)
- Filtro por estado, organismo, región, comuna
- Filtro por rango de monto
- Filtro por fecha de publicación y cierre
- **Filtro por días restantes para cierre** (0 a 30 días)

✅ **Visualización**
- Tabla responsive con todas las licitaciones
- Cards para móvil
- Código clickeable → abre en Mercado Público
- Nombres formateados (Compra Ágil en <100 UTM)
- **Fecha de cierre + Días restantes** (ej: "5d" para 5 días)

✅ **Base de Datos**
- SQLite local (app/data/licitaciones.db)
- Schema robusto con migraciones automáticas
- Búsqueda por código, nombre, descripción, producto

⏳ **En Desarrollo** (próximas fases)
- Alertas por email (Mailgun)
- Sistema de suscripción de usuarios
- Filtros guardados por usuario

---

## 🚀 Cómo Reproducir (Guía Rápida)

### Requisitos
- Python 3.9+
- pip/venv
- Git

### 1. Clonar y Setup

```bash
git clone https://github.com/vincentlc/scrapper-mercado-publico-cl.git
cd ScrapMercadoPublico

# Crear venv
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o en Windows:
# .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Ejecutar Scraper Localmente

```bash
# Descargar ofertas desde Mercado Público
python -m scripts.update_offers

# Esto:
# ✓ Descarga CSV de Mercado Público (último zip)
# ✓ Parsea columnas automáticamente
# ✓ Guarda en SQLite (app/data/licitaciones.db)
# ✓ Valida y limpia datos
```

### 3. Ejecutar API Backend

```bash
# Terminal 1: Backend FastAPI
python -m uvicorn app.main:app --reload --port 8000

# Abierto en http://localhost:8000
```

### 4. Ver Frontend

```bash
# Terminal 2: Servir HTML estático
cd docs
python -m http.server 8080

# Abierto en http://localhost:8080
```

### 5. Probar API

```bash
# Obtener ofertas
curl "http://localhost:8000/api/offers?page=1&page_size=20"

# Con filtros
curl "http://localhost:8000/api/offers?keyword=software&region=Metropolitana&page=1"

# Filtrar por días para cierre (5 a 10 días)
curl "http://localhost:8000/api/offers?min_days_to_close=5&max_days_to_close=10"
```

---

## 📊 Estructura de Datos

### Tabla: `offers`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `codigo_externo` | TEXT (PK) | Código único: 681563-8-LE26 |
| `nombre` | TEXT | Nombre de la licitación |
| `descripcion` | TEXT | Descripción de la licitación |
| `descripcion_producto` | TEXT | Descripción del producto/servicio |
| `organismo` | TEXT | Nombre del organismo (municipalidad, etc) |
| `estado` | TEXT | Estado actual (publicada, cerrada, etc) |
| `region` | TEXT | Región de Chile |
| `comuna` | TEXT | Comuna específica |
| `tipo_oferta` | TEXT | Tipo (Compra Ágil, LP, etc) |
| `moneda` | TEXT | Moneda (CLP, UF, etc) |
| `monto_estimado` | REAL | Monto en números |
| `fecha_publicacion` | TEXT | Fecha ISO (2026-05-18T10:30:00) |
| `fecha_cierre` | TEXT | Fecha ISO con hora de cierre |
| `link` | TEXT | URL directa en Mercado Público |
| `raw_json` | TEXT | JSON con datos crudos (backup) |
| `updated_at` | TEXT | Última actualización |

### Respuesta API: /api/offers

```json
{
  "items": [
    {
      "codigo_externo": "681563-8-LE26",
      "nombre": "SERVICIO DE MANTENCION DE AREAS VERDES",
      "nombre_formateado": "SERVICIO DE MANTENCION DE AREAS VERDES (Compra Ágil)",
      "descripcion": "MANTENCION DE AREAS...",
      "descripcion_producto": "Servicios de cuidado...",
      "organismo": "Ilustre Municipalidad de Ránquil",
      "estado": "Publicada",
      "region": "Región del Ñuble",
      "comuna": "Ránquil",
      "tipo_oferta": "Licitación Pública inferior a 100 UTM (Compra Ágil)",
      "moneda": "CLP",
      "monto_estimado": 15000000,
      "fecha_publicacion": "2026-05-18T10:30:00",
      "fecha_cierre": "2026-05-27T15:17:00",
      "dias_para_cierre": 9,
      "link": "http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion=681563-8-LE26",
      "updated_at": "2026-05-18T12:45:30"
    }
  ],
  "total": 4656,
  "page": 1,
  "page_size": 20
}
```

---

## 📝 Endpoints API

### GET `/api/offers`

Obtener ofertas con filtros opcionales.

**Parámetros:**
```
?keyword=software              # Busca en nombre, descripción, producto, código
&tipo_oferta=LP               # Tipo de oferta exacto
&utm_range=lt100              # Rango UTM: lt100, 100_1000, 1000_2000, 2000_5000, gt5000
&estado=Publicada             # Estado exacto
&organismo=Municipalidad      # Organismo exacto
&region=Metropolitana         # Región exacta
&comuna=Santiago              # Comuna exacta
&min_monto=1000000            # Monto mínimo
&max_monto=50000000           # Monto máximo
&start_date=2026-05-01        # Desde publicación (ISO)
&end_date=2026-05-31          # Hasta publicación (ISO)
&start_close_date=2026-05-20  # Desde cierre (ISO)
&end_close_date=2026-06-30    # Hasta cierre (ISO)
&min_days_to_close=5          # Mínimo días para cierre
&max_days_to_close=15         # Máximo días para cierre
&page=1                       # Número página
&page_size=50                 # Registros por página (max 200)
```

**Ejemplo:**
```bash
GET /api/offers?keyword=software&min_days_to_close=3&max_days_to_close=10&page=1
```

### GET `/api/filters/options`

Obtener valores únicos para dropdowns.

**Respuesta:**
```json
{
  "tipo_oferta": ["Licitación Pública...", "Compra Ágil", ...],
  "estado": ["Publicada", "Cerrada", ...],
  "organismo": ["Municipalidad X", "Empresa Y", ...],
  "region": ["Región del Ñuble", "Metropolitana", ...],
  "comuna": ["Santiago", "Ránquil", ...]
}
```

### POST `/api/update-offers`

Ejecutar actualización manual (scrapar ahora).

```bash
curl -X POST http://localhost:8000/api/update-offers
```

---

## 🛠 Scripts Disponibles

```bash
# Descargar y procesar ofertas
python -m scripts.update_offers

# Validar/inicializar Google Sheets (solo si usas Sheets)
python -m scripts.init_google_sheets

# Ejecutar tests
pytest tests/

# Ver logs de última ejecución
tail -f data/update_trace.log
```

---

## 🏗 Arquitectura Actual

```
ScrapMercadoPublico/
├── app/
│   ├── main.py               # FastAPI backend
│   ├── db.py                 # SQLite init + migrations
│   ├── query.py              # Lógica de filtros
│   └── data/
│       └── licitaciones.db   # Base de datos local
│
├── scripts/
│   ├── update_offers.py      # Scraper principal
│   ├── helpers.py            # Utilidades Google Sheets
│   └── init_google_sheets.py # Validador Sheets
│
├── docs/
│   ├── index.html            # Frontend (React-like vanilla JS)
│   ├── app.js                # Lógica frontend
│   ├── styles.css            # Estilos
│   └── register.html         # Registro (preparado, no activo)
│
├── tests/
│   ├── test_api_filters.py
│   └── test_update_offers.py
│
├── vercel-functions/         # Backend serverless (preparado)
│   ├── api/
│   │   └── offers.js
│   └── utils/
│       └── google-sheets.js
│
├── requirements.txt          # Dependencias Python
├── pytest.ini               # Config tests
└── README.md               # Este archivo
```

---

## 🔄 Flujo de Datos

```
Mercado Público (ZIP CSV)
          ↓
  scripts/update_offers.py
    - Descarga ZIP
    - Parsea CSV (detecta encoding/delimitador)
    - Normaliza columnas
    - Valida datos
          ↓
   app/data/licitaciones.db (SQLite)
          ↓
    FastAPI Backend (app/main.py)
    - GET /api/offers (con filtros)
    - GET /api/filters/options
          ↓
  Frontend (docs/app.js)
    - Tabla con datos
    - Filtros interactivos
    - Cards responsivas
```

---

## 📦 Dependencias

```
fastapi==0.115.6
uvicorn==0.24.0
requests==2.31.0
python-dotenv==1.0.0
pytest==7.4.3
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.108.0
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
```bash
# Asegúrate de estar en la carpeta raíz
cd ~/Documents/Code/Cursor/ScrapMercadoPublico
python -m uvicorn app.main:app
```

### "Error: Could not detect CSV header"
```bash
# El formato del CSV de Mercado Público cambió
# Revisa con:
python -c "from scripts.update_offers import download_csv; offers, _ = download_csv(); print(offers[0].keys())"
```

### "Base de datos vacía"
```bash
# Ejecuta scraper:
python -m scripts.update_offers

# Verifica:
sqlite3 app/data/licitaciones.db "SELECT COUNT(*) FROM offers;"
```

---

## ⏳ Próximos Pasos (Alertas por Email)

Actualmente **NO funciona** el sistema de alertas por email. Se está planificando:

1. **Sistema de suscripción** → guardar emails + filtros
2. **Detección de cambios** → nueva oferta coincide filtro
3. **Envío Mailgun** → email con enlace a oferta
4. **Desuscripción** → token único por email

Ver: `PLAN_ALERTAS.md` (próximamente)

---

## 📄 Licencia

MIT

---

## 👤 Autor

Vincent Leclerc - [LinkedIn](https://www.linkedin.com/in/vincent-lec/) - [GitHub](https://github.com/vincentlc)

---

## 🙏 Agradecimientos

- Mercado Público de Chile (datos públicos)
- Comunidad de scraping en Python
│   ├── api/offers.js
│   ├── api/register.js
│   └── ...
├── .github/workflows/
│   └── update-offers.yml               ← NUEVO: GitHub Actions (Paso 5)
├── .gitignore
└── README.md                           ← Este archivo
```

---

## 🔐 Secretos (se configura en Paso 2)

GitHub > Settings > Secrets and variables > Actions:

- `GOOGLE_SHEETS_ID` → ID del documento
- `GOOGLE_SERVICE_ACCOUNT_JSON` → Credenciales JSON (base64)
- `MAILGUN_API_KEY` → Para alertas por email
- `MAILGUN_DOMAIN` → Dominio de Mailgun

---

## 🎯 Próximo Paso

**Haz lo siguiente:**

1. Crea Google Sheets con el schema de [docs/PASO_1_SCHEMA_SHEETS.md](docs/PASO_1_SCHEMA_SHEETS.md)
2. Guarda el SPREADSHEET_ID
3. Commit a Git:
   ```bash
   git add .
   git commit -m "docs: add schema and architecture for v2 (serverless)"
   git push origin main
   ```
4. Avísame cuando esté listo para continuar con Paso 2

---

## 📞 Contacto / Portfolio

- **GitHub:** [vincentlc/scrapper-mercado-publico-cl](https://github.com/vincentlc/scrapper-mercado-publico-cl)
- **LinkedIn:** [vincent-lec](https://www.linkedin.com/in/vincent-lec/)

**Status:** En desarrollo 🚀
