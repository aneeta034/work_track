from django.urls import path
from . import views
urlpatterns = [
     path('add-technician/', views.add_technician, name='add_technician'),
    path('technicians/',views.list_technicians, name='list_technicians'),
    path('additional/work/<int:apply_id>/',views.extra_work_admin,name='extra_work_admin'),
    path('customer/add/',views.add_customer,name='add_customer'),
    path('customer/update/<int:customer_id>/',views.update_customer,name='update_customer'),
    path('customer/delete/<int:customer_id>/',views.delete_customer,name='delete_customer'),
    path('customer/new/',views.new_customer,name='new_customer'),
    path('apply-for-service/',views.apply_for_service,name='apply_for_service'),
    path('update-applied-service/<int:service_id>/',views.update_applied_service,name='update_applied_service'),
    path('delete-applied-service/<int:service_id>/',views.delete_applied_service,name='delete_applied_service'),
    path('switch_task/', views.switch_task, name='switch_task'),
    path('switch_task/<str:status>/', views.switch_task, name='switch_task_filter'),
     path('filter-applied-services/', views.filter_applied_services, name='filter_applied_services'),
    path('reset-filter-applied-services/', views.reset_filter_applied_services, name='reset_filter_applied_services'),
    path('add_service/', views.add_service, name='add_service'),
    path('search_customer/', views.search_customer, name='search_customer'),
    path('get_users/', views.get_users, name='get_users'),
    path('export-applied-services/<str:status>/', views.export_applied_services, name='export_applied_services'),

]