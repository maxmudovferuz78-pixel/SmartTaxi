from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET

@require_GET
def login_view(request): return render(request, 'auth/login.html')

@require_GET
def driver_dashboard(request): return render(request, 'driver/dashboard.html')
@require_GET
def driver_orders(request): return render(request, 'driver/orders.html')
@require_GET
def driver_wallet(request): return render(request, 'driver/wallet.html')
@require_GET
def driver_profile(request): return render(request, 'driver/profile.html')

@require_GET
def passenger_dashboard(request): return render(request, 'passenger/dashboard.html')
@require_GET
def passenger_orders(request): return render(request, 'passenger/orders.html')
@require_GET
def passenger_profile(request): return render(request, 'passenger/profile.html')

@require_GET
def admin_dashboard(request): return render(request, 'admin/dashboard.html')
@require_GET
def admin_drivers(request): return render(request, 'admin/drivers.html')
@require_GET
def admin_orders(request): return render(request, 'admin/orders.html')
@require_GET
def admin_tariffs(request): return render(request, 'admin/tariffs.html')

@require_GET
def index(request): return redirect('/auth/login/')
