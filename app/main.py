# app/main.py
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import db, models, ocr, nlp, email_service, utils
from .schemas import InvoiceCreateResponse, InvoiceStatus

# --- Configuración de directorios ---
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- App FastAPI ---
app = FastAPI(title="Invoice Processor")

# Templates y archivos estáticos
templates = Jinja2Templates(directory="app/templates")
if not (Path("app/static").exists()):
    Path("app/static").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Inicializar base de datos (crea tablas si no existen)
db.init_db()

# Dependencia para obtener sesión DB
def get_db():
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ----------------------------
# Endpoint: subir factura (API)
# ----------------------------
@app.post("/invoices/upload", response_model=InvoiceCreateResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    notify_to: Optional[str] = Form(None),
    db_session: Session = Depends(get_db),
):
    """
    Subir factura vía API (multipart). Opcional: notify_to = email del aprobador.
    """
    # Guardar archivo
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # OCR
    raw_text = ""
    if file.filename.lower().endswith(".pdf"):
        try:
            raw_text = ocr.pdf_to_text(str(file_path))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error PDF->texto: {e}")
    else:
        raw_text = ocr.image_to_text(str(file_path))

    # NLP / extracción de campos
    extracted = nlp.extract_fields(raw_text)

    # Crear Invoice en BD
    inv = models.Invoice(
        provider_name=extracted.get("provider_name"),
        invoice_number=extracted.get("invoice_number"),
        issue_date=extracted.get("issue_date"),
        due_date=extracted.get("due_date"),
        total_amount=extracted.get("total_amount"),
        taxes=extracted.get("taxes"),
        raw_text=raw_text,
        extracted=extracted,
        state=models.InvoiceState.IN_PROCESS,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)

    # Registrar historial inicial
    hist = models.InvoiceHistory(
        invoice_id=inv.id,
        from_state="",
        to_state=inv.state.value,
        comment="Creada y procesada automáticamente",
    )
    db_session.add(hist)
    db_session.commit()

    # Enviar notificación si se proporcionó email
    if notify_to:
        approve_token = utils.sign_payload({"id": inv.id, "action": "approve"})
        reject_token = utils.sign_payload({"id": inv.id, "action": "reject"})
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        approve_link = f"{base_url}/action/{approve_token}"
        reject_link = f"{base_url}/action/{reject_token}"
        try:
            email_service.send_invoice_email(
                notify_to,
                {
                    "invoice_number": inv.invoice_number,
                    "provider_name": inv.provider_name,
                    "issue_date": inv.issue_date,
                    "due_date": inv.due_date,
                    "total_amount": inv.total_amount,
                    "taxes": inv.taxes,
                },
                approve_link,
                reject_link,
            )
        except Exception as e:
            # No romper la creación si falla el email, solo loguear
            print("Email error:", e)

    return {"id": inv.id, "state": inv.state.value}


# -----------------------------------
# Endpoint: consultar factura y estado
# -----------------------------------
@app.get("/invoices/{invoice_id}", response_model=InvoiceStatus)
def get_invoice(invoice_id: int, db_session: Session = Depends(get_db)):
    inv = db_session.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    history = [
        {"from": h.from_state, "to": h.to_state, "timestamp": str(h.timestamp), "comment": h.comment}
        for h in inv.history
    ]
    return {"id": inv.id, "state": inv.state.value, "extracted": inv.extracted, "history": history}


# -------------------------------------------------------
# Endpoints para acciones desde links en el email (aprob.)
# -------------------------------------------------------
@app.get("/action/{token}", response_class=HTMLResponse)
def action_get(token: str):
    """
    Enlace intermedio: valida token y redirige al flujo correspondiente.
    """
    try:
        payload = utils.unsign_payload(token)
    except Exception:
        return HTMLResponse("<h3>Enlace inválido o expirado</h3>", status_code=400)
    action = payload.get("action")
    if action == "approve":
        return RedirectResponse(f"/action/confirm/{token}")
    elif action == "reject":
        return RedirectResponse(f"/action/reject_form/{token}")
    else:
        return HTMLResponse("<h3>Acción desconocida</h3>", status_code=400)


@app.get("/action/confirm/{token}", response_class=HTMLResponse)
def action_confirm(token: str, db_session: Session = Depends(get_db)):
    """
    Ejecuta la aprobación y registra el historial.
    """
    try:
        payload = utils.unsign_payload(token)
    except Exception:
        return HTMLResponse("<h3>Enlace inválido</h3>", status_code=400)
    if payload.get("action") != "approve":
        return HTMLResponse("<h3>Acción inválida</h3>", status_code=400)

    inv = db_session.query(models.Invoice).get(payload.get("id"))
    if not inv:
        return HTMLResponse("<h3>Factura no encontrada</h3>", status_code=404)

    prev = inv.state.value
    inv.state = models.InvoiceState.APPROVED
    db_session.add(inv)
    db_session.commit()
    db_session.add(
        models.InvoiceHistory(invoice_id=inv.id, from_state=prev, to_state=inv.state.value, comment="Aprobado vía email")
    )
    db_session.commit()
    return HTMLResponse(f"<h3>Factura {inv.invoice_number or inv.id} aprobada. Gracias.</h3>")


@app.get("/action/reject_form/{token}", response_class=HTMLResponse)
def reject_form(token: str):
    """
    Muestra formulario para capturar motivo de rechazo (desde link del email).
    """
    html = f"""
    <html><body>
      <h3>Rechazar factura</h3>
      <form action="/action/reject_confirm" method="post">
        <input type="hidden" name="token" value="{token}" />
        <label>Motivo del rechazo:</label><br/>
        <textarea name="comment" rows="6" cols="60"></textarea><br/>
        <button type="submit">Enviar rechazo</button>
      </form>
    </body></html>
    """
    return HTMLResponse(html)


@app.post("/action/reject_confirm", response_class=HTMLResponse)
def reject_confirm(token: str = Form(...), comment: str = Form(...), db_session: Session = Depends(get_db)):
    """
    Procesa el rechazo: actualiza estado y registra comentario.
    """
    try:
        payload = utils.unsign_payload(token)
    except Exception:
        return HTMLResponse("<h3>Enlace inválido</h3>", status_code=400)
    if payload.get("action") != "reject":
        return HTMLResponse("<h3>Acción inválida</h3>", status_code=400)

    inv = db_session.query(models.Invoice).get(payload.get("id"))
    if not inv:
        return HTMLResponse("<h3>Factura no encontrada</h3>", status_code=404)

    prev = inv.state.value
    inv.state = models.InvoiceState.REJECTED
    db_session.add(inv)
    db_session.commit()
    db_session.add(models.InvoiceHistory(invoice_id=inv.id, from_state=prev, to_state=inv.state.value, comment=comment))
    db_session.commit()
    return HTMLResponse(f"<h3>Factura {inv.invoice_number or inv.id} rechazada. Comentario registrado.</h3>")


# ----------------------------------------------
# Página web simple: subir facturas desde navegador
# ----------------------------------------------
@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request):
    """
    Formulario HTML para que un usuario suba factura y escriba el email del aprobador.
    """
    return templates.TemplateResponse("upload_form.html", {"request": request})


@app.post("/upload", response_class=HTMLResponse)
async def handle_upload(
    request: Request, file: UploadFile = File(...), notify_to: str = Form(...), db_session: Session = Depends(get_db)
):
    """
    Maneja la subida desde la web, procesa y envía notificación al aprobador.
    """
    # Guardar archivo
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # OCR
    raw_text = ""
    if file.filename.lower().endswith(".pdf"):
        try:
            raw_text = ocr.pdf_to_text(str(file_path))
        except Exception as e:
            return HTMLResponse(f"<h3>Error procesando PDF: {e}</h3>", status_code=500)
    else:
        raw_text = ocr.image_to_text(str(file_path))

    # Extracción
    extracted = nlp.extract_fields(raw_text)

    # Insertar invoice
    inv = models.Invoice(
        provider_name=extracted.get("provider_name"),
        invoice_number=extracted.get("invoice_number"),
        issue_date=extracted.get("issue_date"),
        due_date=extracted.get("due_date"),
        total_amount=extracted.get("total_amount"),
        taxes=extracted.get("taxes"),
        raw_text=raw_text,
        extracted=extracted,
        state=models.InvoiceState.IN_PROCESS,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)

    # Historial inicial
    db_session.add(
        models.InvoiceHistory(invoice_id=inv.id, from_state="", to_state=inv.state.value, comment="Creada por formulario web")
    )
    db_session.commit()

    # Enviar email
    approve_token = utils.sign_payload({"id": inv.id, "action": "approve"})
    reject_token = utils.sign_payload({"id": inv.id, "action": "reject"})
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    approve_link = f"{base_url}/action/{approve_token}"
    reject_link = f"{base_url}/action/{reject_token}"
    try:
        email_service.send_invoice_email(
            notify_to,
            {
                "invoice_number": inv.invoice_number,
                "provider_name": inv.provider_name,
                "issue_date": inv.issue_date,
                "due_date": inv.due_date,
                "total_amount": inv.total_amount,
                "taxes": inv.taxes,
            },
            approve_link,
            reject_link,
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Factura creada (id={inv.id}) pero fallo envío email: {e}</h3>")

    return HTMLResponse(f"<h3>Factura creada (id={inv.id}). Email enviado a {notify_to}.</h3>")


# --------------------------------------
# Endpoint: webhook para decisiones externas
# --------------------------------------
@app.post("/webhooks/decision")
async def webhook_decision(request: Request, db_session: Session = Depends(get_db)):
    """
    Espera JSON en el body:
    {
      "invoice_id": 123,
      "action": "approve" | "reject",
      "comment": "opcional",
      "source": "resend"  # opcional
    }
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Payload JSON inválido o ausente"}, status_code=400)

    invoice_id = payload.get("invoice_id")
    action = payload.get("action")
    comment = payload.get("comment", "")
    source = payload.get("source", "webhook")

    if not invoice_id or action not in ("approve", "reject"):
        return JSONResponse({"status": "error", "message": "Payload inválido"}, status_code=400)

    inv = db_session.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        return JSONResponse({"status": "error", "message": "Invoice not found"}, status_code=404)

    prev = inv.state.value
    if action == "approve":
        inv.state = models.InvoiceState.APPROVED
        note = f"Aprobado vía webhook ({source})"
    else:
        inv.state = models.InvoiceState.REJECTED
        note = f"Rechazado vía webhook ({source}): {comment}"

    db_session.add(inv)
    db_session.commit()
    db_session.add(models.InvoiceHistory(invoice_id=inv.id, from_state=prev, to_state=inv.state.value, comment=comment or note))
    db_session.commit()

    # Opcional: registrar webhook log si definiste WebhookLog en models.py
    try:
        if hasattr(models, "WebhookLog"):
            wl = models.WebhookLog(source=source, payload=payload, processed="ok")
            db_session.add(wl)
            db_session.commit()
    except Exception:
        pass

    return {"status": "ok", "invoice_id": invoice_id, "new_state": inv.state.value}



@app.get("/action/reject_form/{token}", response_class=HTMLResponse)
def reject_form(request: Request, token: str):
    # Verifica que el token sea válido
    try:
        utils.unsign_payload(token)
    except Exception:
        return HTMLResponse("<h3>Enlace inválido o expirado</h3>", status_code=400)

    return templates.TemplateResponse("reject_form.html", {"request": request, "token": token})