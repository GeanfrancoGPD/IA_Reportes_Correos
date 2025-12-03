# Sistema Automatizado de Procesamiento de Facturas con IA, PostgreSQL y Notificaciones Interactivas (Resend)

Este proyecto implementa un sistema completo para procesar facturas digitales usando OCR e IA, almacenarlas en una base de datos PostgreSQL, gestionarlas mediante estados, y manejar un proceso de aprobación con correos electrónicos interactivos mediante **Resend**.

---

# Características Principales

## Módulo 1: Procesamiento Inteligente de Facturas

- Recepción de imágenes o archivos PDF
- OCR con Python (Tesseract)
- Procesamiento de lenguaje natural para extraer campos clave:
  - Nombre del proveedor
  - Número de factura
  - Fecha de emisión
  - Monto total
  - Impuestos
  - Fecha de vencimiento (opcional)
- Validación de campos
- Conversión de datos no estructurados → JSON estructurado

---

## Módulo 2: Gestión en Base de Datos (PostgreSQL)

- Estados: `En Proceso`, `Aprobado`, `Rechazado`
- Registro de timestamps
- Historial completo de transiciones
- Metadatos del proceso
- Comentarios en rechazos

---

## Módulo 3: Notificaciones Interactivas (Resend)

- Envío de correos HTML con diseño profesional
- Botones interactivos:
  - ✔ Aprobar factura
  - ❌ Rechazar factura (con formulario)
- Procesamiento de respuestas
- Webhook para actualizar estados

---

## Módulo 4: API REST Completa

Endpoints principales:

| Método | Ruta                     | Descripción                        |
| ------ | ------------------------ | ---------------------------------- |
| `POST` | `/invoices/upload`       | Subir una factura para proceso OCR |
| `GET`  | `/invoices/{id}`         | Consultar estado y datos           |
| `POST` | `/webhooks/decision`     | Procesar aprobación/rechazo        |
| `GET`  | `/invoices/{id}/history` | Ver historial                      |

---

# 📁 Estructura del Proyecto

```
project/
│── app/
│   ├── main.py                → App FastAPI principal
│   ├── ocr.py                 → OCR (Tesseract)
│   ├── nlp.py                 → Extracción de campos
│   ├── emailer.py             → Sistema de notificaciones Resend
│   ├── db.py                  → Conexión y motor PostgreSQL
│   ├── models.py              → Tablas SQLAlchemy
│   ├── schemas.py             → Modelos Pydantic
│   ├── workflow.py            → Lógica de aprobación/rechazo
│   └── utils.py               → Funciones auxiliares
│
│── run_demo.py                → Script de demostración completa del flujo
│── requirements.txt           → Dependencias del proyecto
│── README.md                  → Este documento
│── .env.example               → Variables de entorno de plantilla
```

## Modulo 5: Flujo Completo del Sistema

1. Usuario sube una factura (PDF/Imagen)
2. OCR extrae el texto crudo
3. NLP identifica:

- Proveedor
- Número de factura
- Fecha emisión
- Fecha vencimiento
- Impuestos
- Total

4.  Se valida la información
5.  Se almacena en PostgreSQL con estado: “EN_PROCESO”
6.  Se envía correo al aprobador usando Resend
7.  El aprobador pulsa “Aprobar” o “Rechazar + Comentario”
8.  la API recibe el webhook de Resend
9.  La BD actualiza estado y registra historial
10. Se notifica y loguea todo el proceso

## Modulo 6: Crear un entorno virtual

- Windows

```bash
    python -m venv venv
    venv\Scripts\activate
```

- MacOS / Linux:

```bash
    python3 -m venv venv
    source venv/bin/activate
```

### Instalar dependencias

```bash
    pip install -r requirements.txt
```

- Windows

Descargar instalador: https://github.com/UB-Mannheim/tesseract/wiki

- Linux

```bash
sudo apt install tesseract-ocr
```

- macOS

```bash
brew install tesseract
```

## Modulo 7: Creacion de la base de datos

```sql
    CREATE DATABASE invoices_db;
```

### Configurar variables de entorno .env

```ini
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/invoices_db

RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM=tu-correo@tudominio.com
EMAIL_APPROVAL_WEBHOOK=http://localhost:8000/webhooks/decision
```

## Modulo 8: Ejecución del Servidor

Activa el entorno virtual y ejecuta:

```bash
    uvicorn app.main:app --reload
```

API accesible en:

```bash
http://localhost:8000
```

Docs automáticos:

```bash
http://localhost:8000/docs
http://127.0.0.1:8000/upload // ver la pagina web interactiva
```

### Ejecutar la Demo Completa

```bash
python run_demo.py
```

## Modulo 9: Desiciones tecnicas

Decisiones Técnicas

- SQLAlchemy por su flexibilidad y robustez
- FastAPI por su velocidad, validación automática y OpenAPI
- Tesseract OCR por ser open-source y suficientemente preciso
- Resend en lugar de SMTP por:
  - Mejor reputación de envío
  - API más moderna
- Manejo automático de plantillas
- Arquitectura modular para fácil escalabilidad
