from django.urls import path
from . import views


urlpatterns = [
        path('update-customer/<int:customer_id>/', views.update_customer, name='update_customer'),
        path('additional-work/<int:apply_id>/',views.extra_work_technician,name='extra_work_technician'),
        path('fuelcharge/<int:apply_id>/',views.fuelcharge,name='fuelcharge'),
        path('update_fuelcharge/<int:fuel_id>/',views.update_fuelcharge, name='update_fuelcharge'),
        path('delete-fuelcharge/<int:fuel_id>/', views.delete_fuelcharge, name='delete_fuelcharge'),
        path('foodallowance/<int:apply_id>/',views.foodallowance,name='food_allowance'),
        path('update-food-allowance/<int:food_id>/',views.update_food_allowance,name='update_food_allowance'),
        path('delete-food-allowance/<int:allowance_id>/', views.delete_food_allowance, name='delete_food_allowance'),
        path('item-purchased/<int:apply_id>/',views.item_purchased,name='item_purchased'),
        path('update-item-purchased/<int:item_id>/',views.update_item_purchased,name='update_item_purchased'),
        path('delete-item-purchased/<int:item_id>/', views.delete_item_purchased, name='delete_item_purchased'),
        path('vendor-info/<int:apply_id>/',views.vendor_info,name='vendor_info'),
        path('update-vendor-info/<int:vendor_id>/',views.update_vendor_info,name='update_vendor_info'),
        path('delete-vendor-info/<int:vendor_id>/', views.delete_vendor_info, name='delete_vendor_info'),
        path('update-status/<int:apply_id>/',views.update_current_status,name='update_current_status'),
        path('delete-current-status/<int:status_id>/', views.delete_current_status, name='delete_current_status'),
        path('technician/pending/', views.pending_tasks, name='pending_tasks'),
        path('technician/completed/', views.completed_tasks, name='completed_tasks'),
        path('add_service/', views.add_service, name='add_service'),
        path('search_customer/', views.search_customer, name='search_customer'),
        path('get_users/', views.get_users, name='get_users'),
        path('switch_tasks/', views.switch_tasks, name='switch_tasks'),
        path('switch_tasks/<str:status>/', views.switch_tasks, name='switch_tasks_filter'),
        path("update_service/<int:service_id>/", views.update_service, name="update_service"),
        path("get_service/<int:service_id>/", views.get_service, name="get_service"),
]
