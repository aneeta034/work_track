from django.contrib import admin
from .models import Customer,Apply

# Register your models here.
class CustomerAdmin(admin.ModelAdmin):
    list_display=('id','name','address','contact_number','whatsapp_number','reffered_by')
admin.site.register(Customer,CustomerAdmin)

class ApplyAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'address', 'contact_number', 'whatsapp_number', 
        'reffered_by', 'service_by', 'work_type', 'item_name_or_number', 
        'issue', 'photos_of_item', 'estimation_document', 'estimated_price', 
        'estimated_date', 'any_other_comments'
    )

admin.site.register(Apply, ApplyAdmin)