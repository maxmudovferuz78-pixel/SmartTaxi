from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('auth/login/', views.login_view, name='login'),

    path('driver/', views.driver_dashboard, name='driver-dashboard'),
    path('driver/orders/', views.driver_orders, name='driver-orders'),
    path('driver/wallet/', views.driver_wallet, name='driver-wallet'),
    path('driver/profile/', views.driver_profile, name='driver-profile'),

    path('passenger/', views.passenger_dashboard, name='passenger-dashboard'),
    path('passenger/orders/', views.passenger_orders, name='passenger-orders'),
    path('passenger/profile/', views.passenger_profile, name='passenger-profile'),

    path('admin-panel/', views.admin_dashboard, name='admin-dashboard'),
    path('admin-panel/drivers/', views.admin_drivers, name='admin-drivers'),
    path('admin-panel/orders/', views.admin_orders, name='admin-orders'),
    path('admin-panel/tariffs/', views.admin_tariffs, name='admin-tariffs'),
]
