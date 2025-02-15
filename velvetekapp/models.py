from django.db import models
from loginapp.models import CustomUser
from django.utils import timezone
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
    address = models.TextField(null=True,)
    contact_number = models.CharField(max_length=15,null=True)
    whatsapp_number = models.CharField(max_length=15,null=True,)
    referred_by =models.CharField(max_length=255,null=True,) 
    service_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    WORK_TYPE_CHOICES=[
        ('sale','sale'),('service','service'),
    ]
    work_type=models.CharField(max_length=10,choices=WORK_TYPE_CHOICES,default='sale')
    item_name_or_number = models.CharField(max_length=255,null=True)
    issue = models.TextField(blank=True,null=True) #applicable for 'services'
    photos_of_item =models.TextField(null=True, blank=True)
    estimation_document =models.FileField(upload_to='pdf',null=True,blank=True)    
    estimated_price = models.CharField(max_length=255,blank=True,null=True)
    estimated_date = models.DateField(null=True,blank=True)
    any_other_comments = models.CharField(max_length=255,null=True,blank=True)
    created_at = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=50, 
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Assigned', 'Assigned')],
        default='Assigned'
    )

    def update_status(self):
        """ Update status based on the latest CurrentStatus entry """
        latest_status = self.current_status_entries.order_by('-date').first()
        if latest_status:
            self.status = latest_status.status
            self.save()

    def __str__(self):
        return f"{self.name} - {self.status}"

    def __str__(self):
        return self.name

    def str(self):
        return f"{self.nature_of_work.capitalize()} - {self.item_name_or_number}"

    def save_photos(self, photos):
        """Custom method to save multiple photos"""
        photo_paths = []
        for photo in photos:
            # Assuming 'photo' is a file object, you can save it to the file system
            photo_path = 'images/' + photo.name
            with open(photo_path, 'wb') as f:
                f.write(photo.read())
            photo_paths.append(photo_path)

        # Save photo paths as a comma-separated string
        self.photos_of_item = ",".join(photo_paths)
        self.save()

    def get_photos(self):
        """Custom method to retrieve photos as a list"""
        return self.photos_of_item.split(",") if self.photos_of_item else []
