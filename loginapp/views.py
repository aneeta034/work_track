from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect,get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from velvetekapp.models import Apply,Customer
from technicianapp.models import CurrentStatus
from .models import CustomUser
from django.contrib import messages
from django.conf import settings
import requests
import urllib
from django.db.models import Sum

from technicianapp.models import FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            print(f"User authenticated: {user.username}, Role: {user.role}")
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'technician':
                return redirect('technician_dashboard')
            else:
                logout(request)
                return render(request, 'login.html', {'error': 'Unauthorized access'})
        else:
            print("Invalid credentials")
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect(reverse('login_view'))

@login_required
def admin_dashboard(request):
    applied_services = Apply.objects.prefetch_related('current_status_entries').all()
    
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()
    service_costs = {}
    for service in Apply.objects.prefetch_related('current_status_entries').all():
        print(service.customer)  # Should print Customer instance or None
        if service.customer:
            print(service.customer.name)


    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count, 
        'MEDIA_URL':settings.MEDIA_URL
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def technician_dashboard(request):
    technician_customers = Apply.objects.filter(service_by=request.user) if request.user.is_authenticated else None
    total_services = technician_customers.count() if technician_customers else 0
    pending_task = CurrentStatus.objects.filter(technician_name=request.user.username, status="Pending").count()
    completed_task = CurrentStatus.objects.filter(technician_name=request.user.username, status="Completed").count()

    details = None
    users = CustomUser.objects.all()

   

    if 'contact_number' in request.GET:
        contact_number = request.GET.get('contact_number', '').strip()
        try:
            details = Customer.objects.get(contact_number=contact_number)
        except Customer.DoesNotExist:
            messages.info(request, "No customer found with this contact number. You can add their details.")

    if request.method == 'POST':
        contact_number = request.POST.get('contact_number')
        name = request.POST.get('name')
        address = request.POST.get('address')
        whatsapp_number = request.POST.get('whatsapp')
        referred_by = request.POST.get('referred_by')

        try:
            customer = Customer.objects.get(contact_number=contact_number)
        except Customer.DoesNotExist:
            customer = Customer.objects.create(
                name=name,
                address=address,
                contact_number=contact_number,
                whatsapp_number=whatsapp_number,
                reffered_by=referred_by,
            )

        work_type = request.POST.get('work_type')
        item_name_or_number = request.POST.get('item_name_or_number')
        issue = request.POST.get('issue', '').strip()
        photos_of_item = request.FILES.get('photos_of_item')
        estimation_document = request.FILES.get('estimation_document')
        estimated_price = request.POST.get('estimated_price', '').strip()
        estimated_date = request.POST.get('estimated_date', '').strip()
        any_other_comments = request.POST.get('any_other_comments', '').strip()
        service_by_id = request.POST.get('service_by')

        try:
            service_by_user = CustomUser.objects.get(id=service_by_id)

            apply_instance = Apply.objects.create(
                customer=customer,
                name=customer.name,
                address=customer.address,
                contact_number=customer.contact_number,
                whatsapp_number=customer.whatsapp_number,
                reffered_by=customer.reffered_by,
                work_type=work_type,
                item_name_or_number=item_name_or_number,
                issue=issue,
                photos_of_item=photos_of_item,
                estimation_document=estimation_document,
                estimated_price=estimated_price,
                estimated_date=estimated_date,
                any_other_comments=any_other_comments,
                service_by=service_by_user,
            )

            CurrentStatus.objects.create(
                date=apply_instance.estimated_date,
                technician_name=service_by_user.username,  
                status="assigned",
                apply=apply_instance,
                customer_name=apply_instance.name,
                issue=apply_instance.issue,
            )

            if customer.whatsapp_number:
                message = f"Dear {customer.name}, your application for '{work_type}' has been successfully submitted and is currently 'assigned'."
                encoded_message = urllib.parse.quote(message)
                whatsapp_url = f"https://whatsapimanagment.onrender.com/send-message?phoneNumber={customer.whatsapp_number}&messageBody={encoded_message}"

                try:
                    response = requests.get(whatsapp_url)
                    if response.status_code == 200:
                        messages.success(request, "Service request submitted and WhatsApp message sent successfully!")
                    else:
                        messages.warning(request, "Service request submitted, but failed to send WhatsApp message.")
                except requests.RequestException as e:
                    messages.warning(request, f"Service request submitted, but error sending WhatsApp message: {e}")
            else:
                messages.success(request, "Service request submitted successfully!")

            return redirect('technician_dashboard')

        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid service provider.")

    


    context = {
        'technician_customers': technician_customers,
        'users': users,
        'details': details,
        'total_services': total_services,
        'pending_task': pending_task,
        'completed_task': completed_task,
        'MEDIA_URL': settings.MEDIA_URL, 
         
    }
    return render(request, 'technician_dashboard.html', context)

