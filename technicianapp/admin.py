from django.contrib import admin
from .models import FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus


# Register your models here.
class FuelChargeAdmin(admin.ModelAdmin):
    list_display=('id','customer_name','issue','technician_name','date','purpose','kilometers','cost')
admin.site.register(FuelCharge, FuelChargeAdmin)

class FoodAllowanceAdmin(admin.ModelAdmin):
    list_display=('id','customer_name','issue','technician_name','date','purpose','cost')
admin.site.register(FoodAllowance, FoodAllowanceAdmin)

class ItemPurchasedAdmin(admin.ModelAdmin):
    list_display=('id','customer_name','issue','date','item_name','price','bill_photo')
admin.site.register(ItemPurchased, ItemPurchasedAdmin)


class VendorInfodAdmin(admin.ModelAdmin):
    list_display=('id','customer_name','issue','date','vendor_name','vendor_bill_photo','vendor_eta','vendor_cost')
admin.site.register(VendorInfo, VendorInfodAdmin)

class CurrentStatusdAdmin(admin.ModelAdmin):
    list_display=('id','date','technician_name','status')
admin.site.register(CurrentStatus, CurrentStatusdAdmin)

