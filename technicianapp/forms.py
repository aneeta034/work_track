from django import forms
from .models import FuelCharge
from velvetekapp.models import Apply


class AppliedServiceForm(forms.ModelForm):
    class Meta:
        model = Apply
        fields = [
            'customer', 'name', 'address', 'contact_number', 'whatsapp_number', 'referred_by',
            'service_by', 'work_type', 'item_name_or_number', 'issue', 'photos_of_item',
            'estimation_document', 'estimated_price', 'estimated_date', 'any_other_comments'
        ]
    issue = forms.CharField(widget=forms.Textarea, required=False)
    photos_of_item = forms.CharField(widget=forms.Textarea, required=False)
    estimation_document = forms.FileField(required=False)
    estimated_price = forms.CharField(required=False)
    any_other_comments = forms.CharField(required=False)
    estimated_date = forms.DateField(required=True)
    





