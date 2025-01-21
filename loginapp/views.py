from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from velvetekapp.models import Apply,Customer
from technicianapp.models import CurrentStatus

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
    applied_services = Apply.objects.all()
    if not applied_services.exists():
        applied_services = None 

    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    pending_count = CurrentStatus.objects.filter(status='Pending').count()
    completed_count = CurrentStatus.objects.filter(status='Completed').count()


    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'pending_count': pending_count,
        'completed_count': completed_count
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def technician_dashboard(request):
    technician_customers = None

    if request.user.is_authenticated:
        technician_customers = Apply.objects.filter(service_by=request.user)

    context = {
        'details': technician_customers,  
    }
    return render(request, 'technician_dashboard.html', context)