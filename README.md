# Oferta Pública Chile Tracker - Arquitectura v2

Sistema serverless para monitorear licitaciones públicas de Chile con alertas personalizadas por email.

**🎯 Stack Tech:**
- Frontend: GitHub Pages (HTML/JS)
- Backend: Vercel Functions (Node.js)
- Scraper: GitHub Actions (Python, cada 6h)
- BD: Google Sheets (centralizada)
- Alertas: Mailgun (10k/mes gratis)

**✨ Características:**
- Actualización automática cada 6 horas
- Filtros personalizados por usuario
- Alertas por email inmediatas
- Desuscripción simple (link en email)
- Limpieza automática de datos (>30 días)
- Web pública + datos de usuarios privados
- Zero costo

---

## 📋 Plan de Implementación

### [Paso 1: Schema Google Sheets](docs/PASO_1_SCHEMA_SHEETS.md) ← AQUÍ ESTAMOS
- [ ] Crear documento Google Sheets
- [ ] Diseñar 5 hojas (ofertas, users, user_filters, notification_runs, temp_emails_queue)
- [ ] Documentar schema y relaciones

### Paso 2: Google Cloud Setup
- [ ] Crear proyecto Google Cloud
- [ ] Habilitar APIs
- [ ] Generar credenciales

### Paso 3: Vercel Functions (Backend)
- [ ] Endpoints para registro, filtros, desuscripción
- [ ] Conectar a Google Sheets API

### Paso 4: Python Script Migration
- [ ] Adaptarscripts/update_offers.py para Sheets
- [ ] Implementar lógica de alertas
- [ ] Agregar limpieza de datos

### Paso 5: GitHub Actions Workflow
- [ ] Crear workflow para ejecutar cada 6 horas
- [ ] Jobs: scraping + alertas

### Paso 6: Frontend Deploy
- [ ] GitHub Pages con formularios (registro, filtros)
- [ ] Adaptarendpoints API

### Paso 7: Testing & Deploy
- [ ] Flujo completo (registro → alerta)
- [ ] Validar datos

---

## 🚀 Primeros Pasos

### 1️⃣ Crear Google Sheets

1. Ir a [Google Sheets](https://sheets.google.com)
2. Nuevo → Spreadsheet → Nombrar "ScrapMercadoPublico-BD"
3. Crear las siguientes hojas: `ofertas`, `users`, `user_filters`, `notification_runs`, `temp_emails_queue`
4. Copiar headers de [docs/PASO_1_SCHEMA_SHEETS.md](docs/PASO_1_SCHEMA_SHEETS.md)

### 2️⃣ Guardar SPREADSHEET_ID

En la URL del Sheets, verás algo como:
```
https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
```

Guarda ese ID (lo necesitaremos en Paso 2).

### 3️⃣ Próximo: Paso 2 (Google Cloud)

Cuando termines el setup del Sheets, continuaremos con:
- Crear proyecto Google Cloud
- Generar credenciales
- Guardar en GitHub Secrets

---

## 📁 Estructura del Proyecto

```
ScrapMercadoPublico/
├── docs/
│   ├── PASO_1_SCHEMA_SHEETS.md         ← Diseño BD
│   ├── PASO_2_GOOGLE_CLOUD.md          ← Google Cloud setup
│   ├── PASO_3_VERCEL_SETUP.md          ← Backend
│   └── ...
├── app/static/
│   ├── index.html                      ← Frontend (mejorado)
│   ├── app.js
│   └── styles.css
├── scripts/
│   └── update_offers.py                ← Será adaptado para Sheets
├── vercel-functions/                   ← NUEVO: Backend (Paso 3)
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
