"""
wallet/urls.py

Hamyon URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/wallet/", include("wallet.urls")),

To'liq URL'lar:
    GET /api/wallet/me/            -- Joriy balans (IsDriver)
    GET /api/wallet/transactions/  -- Tranzaksiyalar tarixi (IsDriver)
"""

from django.urls import path

from .views import TransactionListView, WalletMeView

app_name = "wallet"

urlpatterns = [
    path("me/",           WalletMeView.as_view(),       name="wallet-me"),
    path("transactions/", TransactionListView.as_view(), name="transactions"),
]