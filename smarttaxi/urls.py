"""
SmartTaxi Frontend URL Configuration

Bu faylni loyihangizning asosiy urls.py ga qo'shing:

    from django.urls import path, include

    urlpatterns = [
        path('', include('frontend.urls')),   # yoki to'g'ridan-to'g'ri shu fayldan
        path('api/', include('your_api.urls')),
        path('admin/', admin.site.urls),
    ]
"""
from django.urls import path
from . import views

urlpatterns = [
    # Root
    path('', views.index, name='index'),

    # Auth
    path('auth/login/', views.login_view, name='login'),

    # Driver panel
    path('driver/',          views.driver_dashboard, name='driver-dashboard'),
    path('driver/orders/',   views.driver_orders,    name='driver-orders'),
    path('driver/wallet/',   views.driver_wallet,    name='driver-wallet'),
    path('driver/profile/',  views.driver_profile,   name='driver-profile'),

    # Passenger panel
    path('passenger/',          views.passenger_dashboard, name='passenger-dashboard'),
    path('passenger/orders/',   views.passenger_orders,    name='passenger-orders'),
    path('passenger/profile/',  views.passenger_profile,   name='passenger-profile'),

    # Admin / Operator panel
    path('admin-panel/',             views.admin_dashboard, name='admin-dashboard'),
    path('admin-panel/drivers/',     views.admin_drivers,   name='admin-drivers'),
    path('admin-panel/orders/',      views.admin_orders,    name='admin-orders'),
    path('admin-panel/tariffs/',     views.admin_tariffs,   name='admin-tariffs'),
]
