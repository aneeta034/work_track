from django.urls import path
from . import views


urlpatterns = [
        path('pending-task/',views.tech_pending_services,name='tech_pending_services'),
        path('add-customer/',views.technician_add_customer,name='technician_add_customer'),
        path('new-customer/',views.technician_new_customer,name='technician_new_customer'),
        path('update-customer/<int:customer_id>/', views.update_customer, name='update_customer'),
        path('add-service/',views.technician_add_service,name='technician_add_service'),
        path('additional-work/<int:apply_id>/',views.extra_work_technician,name='extra_work_technician'),
        path('save_fuel_charge/', views.save_fuel_charge, name='save_fuel_charge'),
        # path('fuelcharge/<int:apply_id>/',views.fuelcharge,name='fuelcharge'),
        path('update-fuelcharge/<int:fuel_id>/',views.update_fuelcharge,name='update_fuelcharge'),
        path('delete-fuelcharge/<int:fuel_id>/', views.delete_fuelcharge, name='delete_fuelcharge'),
        path('save-food-allowance/', views.save_food_allowance, name='save_food_allowance'),
        path('update-food-allowance/<int:food_id>/',views.update_food_allowance,name='update_food_allowance'),
        path('delete-food-allowance/<int:allowance_id>/', views.delete_food_allowance, name='delete_food_allowance'),
        path('save-item-purchased/', views.save_item_purchased, name='save_item_purchased'),
        path('update-item-purchased/<int:item_id>/',views.update_item_purchased,name='update_item_purchased'),
        path('delete-item-purchased/<int:item_id>/', views.delete_item_purchased, name='delete_item_purchased'),
        path('save-vendor-info/', views.save_vendor_info, name='save_vendor_info'),
        path('update-vendor-info/<int:vendor_id>/',views.update_vendor_info,name='update_vendor_info'),
        path('delete-vendor-info/<int:vendor_id>/', views.delete_vendor_info, name='delete_vendor_info'),
        # path('current-status/<int:apply_id>/',views.current_status,name='current_status'),
        path('update-status/<int:apply_id>/',views.update_current_status,name='update_current_status'),
        path('delete-current-status/<int:status_id>/', views.delete_current_status, name='delete_current_status'),
        path('technician/pending/', views.pending_tasks, name='pending_tasks'),
        path('technician/completed/', views.completed_tasks, name='completed_tasks'),
        path('add_service/', views.add_service, name='add_service'),
        path('search_customer/', views.search_customer, name='search_customer'),
        path('get_users/', views.get_users, name='get_users'),
]
