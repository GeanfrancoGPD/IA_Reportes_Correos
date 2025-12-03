# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base
import enum

class InvoiceState(str, enum.Enum):
    IN_PROCESS = "En Proceso"
    APPROVED = "Aprobado"
    REJECTED = "Rechazado"

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True, index=True)
    issue_date = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)
    taxes = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    extracted = Column(JSON, nullable=True)  # structured dict
    state = Column(Enum(InvoiceState), default=InvoiceState.IN_PROCESS)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    history = relationship("InvoiceHistory", back_populates="invoice")

class InvoiceHistory(Base):
    __tablename__ = "invoice_history"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    from_state = Column(String)
    to_state = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    comment = Column(Text, nullable=True)
    invoice = relationship("Invoice", back_populates="history")

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=True)         # p.ej. "resend"
    payload = Column(JSON, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(String, default="pending")  # pending/ok/error
    error = Column(Text, nullable=True)
