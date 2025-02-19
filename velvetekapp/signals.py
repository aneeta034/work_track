from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer, Apply

@receiver(post_save, sender=Customer)
def update_apply_on_customer_change(sender, instance, **kwargs):
    """
    Automatically updates the Apply model whenever the Customer model is updated.
    Matches Apply records based on contact_number and updates them.
    """
    Apply.objects.filter(contact_number=instance.contact_number).update(
        name=instance.name,
        address=instance.address,
        contact_number=instance.contact_number,
        whatsapp_number=instance.whatsapp_number,
        referred_by=instance.referred_by,
        customer=instance  # Ensuring Apply has the correct Customer foreign key
    )
