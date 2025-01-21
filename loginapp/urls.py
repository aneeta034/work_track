from django.urls import path
from .views import login_view, logout_view,admin_dashboard, technician_dashboard

urlpatterns = [
    path('', login_view, name='login_view'),
    path('logout/', logout_view, name='logout'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('technician-dashboard/', technician_dashboard, name='technician_dashboard'),
]
