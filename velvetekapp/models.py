from django.db import models
from loginapp.models import CustomUser
from django.utils.timezone import now

from datetime import date

# Create your models here.
class Customer(models.Model):
    name=models.CharField(max_length=255)
    address = models.TextField()
    contact_number = models.CharField(max_length=15,unique=True)
    whatsapp_number = models.CharField(max_length=15)
    referred_by =models.CharField(max_length=255)


class Apply(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,blank=True,null=True)
    name=models.CharField(max_length=255,null=True)
    address = models.TextField(null=True)
    contact_number = models.CharField(max_length=15,null=True)
    whatsapp_number = models.CharField(max_length=15,null=True)
    referred_by =models.CharField(max_length=255,null=True) 
    service_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    WORK_TYPE_CHOICES=[
        ('sale','sale'),('service','service'),
    ]
    work_type=models.CharField(max_length=10,choices=WORK_TYPE_CHOICES,default='sale')
    item_name_or_number = models.CharField(max_length=255,null=True)
    issue = models.TextField(blank=True,null=True) #applicable for 'services'
    photos_of_item =models.ImageField(upload_to='images',null=True, blank=True)#option for 'services'
    estimation_document =models.FileField(upload_to='pdf',null=True,blank=True)    
    estimated_price = models.CharField(max_length=255)
    estimated_date = models.DateField(null=True)
    any_other_comments = models.CharField(max_length=255,null=True,blank=True)
    