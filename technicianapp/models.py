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
    review = models.CharField(max_length=255,null=True,blank=True)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='fuel_charges', blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()


class FoodAllowance(models.Model):
    technician_name = models.CharField(max_length=100)
    date = models.DateField()
    purpose = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    review = models.CharField(max_length=255,null=True,blank=True)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='food_allowances',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()


class ItemPurchased(models.Model):
    date = models.DateField()
    item_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    bill_photo = models.ImageField(upload_to='itempurchased')
    review = models.CharField(max_length=255,null=True,blank=True)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='itempurchased',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()



class VendorInfo(models.Model):
    date = models.DateField()
    vendor_name = models.CharField(max_length=200)
    vendor_bill_photo = models.ImageField(upload_to='vendorinfo')
    vendor_eta = models.DateField()
    vendor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    review = models.CharField(max_length=255,null=True,blank=True)
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE,related_name='vendors',blank=True,null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()

class CurrentStatus(models.Model):
    date = models.DateField()
    technician_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=50, 
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Assigned', 'Assigned')],
        default='Assigned'
    )
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE, related_name='current_status_entries', blank=True, null=True)
    customer_name = models.CharField(max_length=225)
    issue = models.TextField()

    def save(self, *args, **kwargs):
        """ When a new status is added, update the Apply model """
        super().save(*args, **kwargs)
        if self.apply:
            self.apply.update_status()

    def __str__(self):
        return f"{self.apply.name if self.apply else 'No Apply'} - {self.status}"

    
