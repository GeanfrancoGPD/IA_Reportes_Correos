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


def send_invoice_email(to_email: str, invoice: dict, approve_link: str, reject_link: str):
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada.")

    if not FROM_EMAIL or not _validate_from_field(FROM_EMAIL):
        raise RuntimeError("EMAIL_FROM inválida o no configurada. Use 'Name <email@domain.com>' o 'email@domain.com'.")

    html = Template(EMAIL_TEMPLATE).render(invoice=invoice, approve_link=approve_link, reject_link=reject_link)

    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": f"Revisión de factura {invoice.get('invoice_number','')}",
        "html": html
    }

    # Intentar usar SDK oficial si está disponible
    try:
        from resend import Resend  # puede lanzar ImportError o AttributeError
        resend = Resend(api_key=RESEND_API_KEY)
        result = resend.emails.send(payload)
        return {"ok": True, "provider": "resend-sdk", "result": result}
    except (ImportError, AttributeError) as exc:
        # SDK no disponible o no exporta 'Resend' - caer al fallback HTTP
        import requests
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.post("https://api.resend.com/emails", json=payload, headers=headers)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        if resp.status_code not in (200, 202):
            raise RuntimeError(f"Error enviando email vía Resend: {body}")
        return {"ok": True, "provider": "resend-http", "result": body}
    except Exception as e:
        # cualquier otro error del SDK
        raise RuntimeError(f"Error enviando email via Resend SDK: {e}")
