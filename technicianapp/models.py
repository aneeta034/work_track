from django.db import models
from velvetekapp.models import Apply
from django.utils.timezone import now

# Create your models here.


class FuelCharge(models.Model):
    technician_name = models.CharField(max_length=100)
    date = models.DateField()
    purpose = models.TextField()
    kilometers = models.FloatField()
    cost = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='fuel_charges', blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()


class FoodAllowance(models.Model):
    technician_name = models.CharField(max_length=100)
    date = models.DateField()
    purpose = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='food_allowances',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()


class ItemPurchased(models.Model):
    date = models.DateField()
    item_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    bill_photo = models.ImageField(upload_to='itempurchased')
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='itempurchased',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()



class VendorInfo(models.Model):
    date = models.DateField()
    vendor_name = models.CharField(max_length=200)
    vendor_bill_photo = models.ImageField(upload_to='vendorinfo')
    vendor_eta = models.DateField()
    vendor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='vendors',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()

class CurrentStatus(models.Model):
    date = models.DateField()
    technician_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=50, 
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Assigned', 'Assigned')], 
        default='Assigned'  # Default to "Assigned"
    )
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE, related_name='current_status_entries',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()

    def update_status_if_due(self):
        if self.status == "assigned" and self.date < now().date():
            self.status = "pending"
            self.save()
