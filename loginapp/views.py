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
    users = CustomUser.objects.all()  

    context = {
        'technician_customers': technician_customers,
        'users': users,
        'total_services': total_services,
        'pending_task': pending_task,
        'completed_task': completed_task,
        'MEDIA_URL': settings.MEDIA_URL, 
         
    }
    return render(request, 'technician_dashboard.html', context)

