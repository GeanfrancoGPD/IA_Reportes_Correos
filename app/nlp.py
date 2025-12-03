# app/nlp.py
import re
from typing import Dict

# Reglas heurísticas para extraer campos. Puedes extender con spaCy y NER.
date_pattern = r"(\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})"
money_pattern = r"(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2}))"  # simple

def extract_fields(raw_text: str) -> Dict:
    text = raw_text.replace("\r", "\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    joined = "\n".join(lines)

    # Provider name: heuristics — primera línea o líneas antes de palabra "Factura" o "RUC"
    provider = None
    for i, l in enumerate(lines[:6]):
        if re.search(r'factura|invoice|ruc|nit', l, re.I):
            if i>0:
                provider = lines[i-1]
                break
    if not provider and lines:
        provider = lines[0]

    # Invoice number
    inv_no = None
    m = re.search(r'(Factura|Invoice|No\.|Nº|N°)\s*[:#]?\s*([A-Za-z0-9\-_/]+)', joined, re.I)
    if m:
        inv_no = m.group(2)
    else:
        m2 = re.search(r'\bN(?:o|º|°)\s*[:#]?\s*([A-Za-z0-9\-_/]+)', joined, re.I)
        if m2:
            inv_no = m2.group(1)

    # Dates
    issue_date = None
    due_date = None
    dates = re.findall(date_pattern, joined)
    if dates:
        issue_date = dates[0]
        if len(dates) > 1:
            due_date = dates[1]

    # Total amount — buscar líneas con "Total", "Importe", "Amount"
    total = None
    taxes = None
    for l in lines[::-1]:  # from bottom
        if re.search(r'\b(total|importe a pagar|amount due|total a pagar|monto total)\b', l, re.I):
            m = re.search(money_pattern, l)
            if m:
                total = m.group(1)
                break
    # fallback: search any large money
    if not total:
        m = re.findall(money_pattern, joined)
        if m:
            total = m[-1]

    # taxes heuristics
    tmatch = re.search(r'(IVA|IVA[:\s]|Impuesto|Tax)[^0-9\n]*(' + money_pattern + ')', joined, re.I)
    if tmatch:
        taxes = tmatch.group(2)

    return {
        "provider_name": provider,
        "invoice_number": inv_no,
        "issue_date": issue_date,
        "due_date": due_date,
        "total_amount": total,
        "taxes": taxes
    }
