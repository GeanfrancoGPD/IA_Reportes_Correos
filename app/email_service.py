# app/email_service.py
import os
from jinja2 import Template

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("EMAIL_FROM")  # Ej: "Facturación <noreply@facturacion.example.com>"

EMAIL_TEMPLATE = """
<!doctype html>
<html>
  <body style="font-family: Arial, sans-serif;">
    <h2>Factura: {{ invoice.invoice_number or "N/A" }}</h2>
    <p><strong>Proveedor:</strong> {{ invoice.provider_name or "N/A" }}</p>
    <p>Fecha emisión: {{ invoice.issue_date }}</p>
    <p>Fecha vencimiento: {{ invoice.due_date }}</p>
    <p>Total: {{ invoice.total_amount }}</p>
    <p>Impuestos: {{ invoice.taxes }}</p>
    <p>
      <a href="{{ approve_link }}" style="padding:10px 12px;background:#27ae60;color:white;border-radius:6px;text-decoration:none;">Aprobar</a>
      <a href="{{ reject_link }}" style="padding:10px 12px;background:#e74c3c;color:white;border-radius:6px;text-decoration:none;">Rechazar</a>
    </p>
  </body>
</html>
"""

def _validate_from_field(from_value: str) -> bool:
    from email.utils import parseaddr
    import re
    if not from_value:
        return False
    name, addr = parseaddr(from_value)
    if not addr:
        return False
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", addr))


def send_invoice_email(to_email: str, invoice: dict, approve_link: str, reject_link: str, from_email: str | None = None):
    """
    Envía un email usando el SDK de Resend si está disponible.
    - to_email: destinatario
    - invoice: dict con datos de la factura
    - approve_link, reject_link: URLs para los botones
    - from_email: opcional, sobrescribe EMAIL_FROM de la env
    """
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada. Establece la variable de entorno RESEND_API_KEY.")

    # Prioriza el from_email pasado como argumento; si no está, usa la env.
    actual_from = from_email or FROM_EMAIL
    if not actual_from or not _validate_from_field(actual_from):
        raise RuntimeError("EMAIL_FROM inválida o no configurada. Use 'Name <email@domain.com>' o pase from_email al llamar la función.")

    # Renderizar HTML
    html = Template(EMAIL_TEMPLATE).render(invoice=invoice, approve_link=approve_link, reject_link=reject_link)

    params = {
        "from": actual_from,
        "to": [to_email],
        "subject": f"Revisión de factura {invoice.get('invoice_number','')}",
        "html": html
    }

    # Intentar usar SDK oficial (estilo mostrado en tu ejemplo)
    try:
        import resend
        # usar la API key como en tu snippet
        resend.api_key = RESEND_API_KEY

        # la llamada puede ser: resend.Emails.send(params) dependiendo de la versión del SDK
        # algunas versiones retornan un objeto/resp; devolvemos ese resultado
        email_resp = resend.Emails.send(params)
        return {"ok": True, "provider": "resend-sdk", "result": email_resp}

    except ImportError:
        # SDK no instalado: usar fallback HTTP
        import requests
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.post("https://api.resend.com/emails", json=params, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        if resp.status_code not in (200, 202):
            # Reenvía el mensaje de error tal cual (por ejemplo: dominio no verificado)
            raise RuntimeError(f"Error enviando email vía Resend: {body}")
        return {"ok": True, "provider": "resend-http", "result": body}

    except Exception as e:
        # Otros errores del SDK (p. ej. validación)
        raise RuntimeError(f"Error enviando email via Resend SDK: {e}")
