"""
payments/urls.py

To'lov URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/payments/", include("payments.urls")),

To'liq URL'lar:
    POST /api/payments/payme/    -- Payme webhook   (AllowAny + Basic Auth)
    POST /api/payments/click/    -- Click webhook   (AllowAny + sign imzo)
    POST /api/payments/topup/    -- To'ldirish link (IsDriver)
    GET  /api/payments/history/  -- To'lov tarixi   (IsDriver)
    GET  /api/payments/          -- Barchasi         (IsOperator)
"""

from django.urls import path

from .views import (
    AllPaymentsView,
    ClickWebhookView,
    PaymentHistoryView,
    PaymeWebhookView,
    TopupInitView,
)

app_name = "payments"

urlpatterns = [
    path("",         AllPaymentsView.as_view(),    name="all-payments"),
    path("payme/",   PaymeWebhookView.as_view(),   name="payme-webhook"),
    path("click/",   ClickWebhookView.as_view(),   name="click-webhook"),
    path("topup/",   TopupInitView.as_view(),       name="topup-init"),
    path("history/", PaymentHistoryView.as_view(),  name="payment-history"),
]