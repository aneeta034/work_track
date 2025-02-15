from technicianapp.models import FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus
from django.shortcuts import render,get_object_or_404, redirect
from .models import Customer,Apply
from django.http import JsonResponse
from django.contrib import messages
from loginapp.models import CustomUser
import urllib
import requests
from django.http import HttpResponseRedirect
from datetime import datetime
from django.core.files.storage import default_storage
from technicianapp.forms import AppliedServiceForm
from django.db.models.functions import Replace
from django.db.models import Value
from django.db.models import Q
import pandas as pd
from django.http import HttpResponse
from django.db.models import OuterRef, Subquery
import pandas as pd
from django.http import HttpResponse
from django.db.models import Q, OuterRef, Subquery
from .models import Apply
from technicianapp.models import CurrentStatus
import urllib.parse
from django.db.models import Sum

def calculate_total_cost(request, service_id):
    """Calculate the total cost for a given service_id and return JSON response."""

    service = get_object_or_404(Apply, id=service_id)

    fuel_total = FuelCharge.objects.filter(apply=service).aggregate(total=Sum('cost'))['total'] or 0
    food_total = FoodAllowance.objects.filter(apply=service).aggregate(total=Sum('cost'))['total'] or 0
    items_total = ItemPurchased.objects.filter(apply=service).aggregate(total=Sum('price'))['total'] or 0
    vendor_total = VendorInfo.objects.filter(apply=service).aggregate(total=Sum('vendor_cost'))['total'] or 0

    total_cost = fuel_total + food_total + items_total + vendor_total

    return JsonResponse({'total_cost': total_cost,'service_id': service_id})

def export_applied_services(request, status):
    # Get the latest status for each Apply instance
    latest_status_subquery = CurrentStatus.objects.filter(
        apply=OuterRef('pk')
    ).order_by('-date').values('status')[:1]

    # Base queryset: Get all Apply instances with the latest status
    applied_services = Apply.objects.all().annotate(
        latest_status=Subquery(latest_status_subquery)
    )

    # Filter by status if not 'all'
    if status.lower() != 'all':
        applied_services = applied_services.filter(latest_status__iexact=status)

    # Get search filters
    filter_type = request.GET.get('filterType', '')
    query = request.GET.get('query', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')

    # Apply search filters
    if filter_type == "date" and query:
        applied_services = applied_services.filter(created_at=query)

    elif filter_type == "month" and query:
        year, month = query.split('-')
        applied_services = applied_services.filter(created_at__year=year, created_at__month=month)

    elif filter_type == "year" and query:
        applied_services = applied_services.filter(created_at__year=query)

    elif filter_type == "dateRange" and start and end:
        applied_services = applied_services.filter(created_at__range=[start, end])

    elif filter_type == "monthRange" and start and end:
        start_year, start_month = start.split('-')
        end_year, end_month = end.split('-')
        applied_services = applied_services.filter(
            Q(created_at__year__gte=start_year, created_at__month__gte=start_month) &
            Q(created_at__year__lte=end_year, created_at__month__lte=end_month)
        )

    elif filter_type == "yearRange" and start and end:
        applied_services = applied_services.filter(created_at__year__gte=start, created_at__year__lte=end)
   
    # Convert to DataFrame
    if not applied_services.exists():
        messages.warning(request, "No data found for the selected filters.")
        return HttpResponse(status=204)  # No content response
    
    df = pd.DataFrame.from_records(
    applied_services.values(
        'id',
        'name', 
        'address', 
        'contact_number', 
        'whatsapp_number', 
        'referred_by', 
        'service_by__username',  # Fetch the username from CustomUser
        'work_type', 
        'item_name_or_number', 
        'issue', 
        'photos_of_item',
        'estimation_document',
        'estimated_price', 
        'estimated_date', 
        'any_other_comments', 
        'created_at',
        'latest_status'
    )
    )
    # Construct a dynamic filename
    filename_parts = ["applied_services"]
    if status.lower() != "all":
        filename_parts.append(status)  # Add status
    if filter_type and query:
        filename_parts.append(f"{filter_type}_{query}")  # e.g., date_2025-02-07
    elif start and end:
        filename_parts.append(f"{filter_type}_{start}_to_{end}")  # e.g., dateRange_2025-02-01_to_2025-02-07
    
    filename = "_".join(filename_parts) + ".xlsx"
    filename = urllib.parse.quote(filename)  # Encode for safe file download

    # Prepare response
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Write to Excel
    df.to_excel(response, index=False)

    return response

def switch_task(request, status=None):
    # Extract search filters
    filter_type = request.GET.get('filterType', '')
    query = request.GET.get('query', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')

    # Get the latest status for each Apply instance
    latest_status_subquery = CurrentStatus.objects.filter(
        apply=OuterRef('pk')
    ).order_by('-date').values('status')[:1]

    # Base queryset: Get all Apply instances
    services = Apply.objects.all().annotate(
        latest_status=Subquery(latest_status_subquery)
    )

    # Apply task status filter
    if status and status.lower() != 'all':
        services = services.filter(latest_status__iexact=status)

    # Apply additional search filters
    if filter_type == "date" and query:
        services = services.filter(created_at=query)

    elif filter_type == "month" and query:
        year, month = query.split('-')
        services = services.filter(
            created_at__year=year, created_at__month=month
        )

    elif filter_type == "year" and query:
        services = services.filter(created_at__year=query)

    elif filter_type == "dateRange" and start and end:
        services = services.filter(created_at__range=[start, end])

    elif filter_type == "monthRange" and start and end:
        start_year, start_month = start.split('-')
        end_year, end_month = end.split('-')

        services = services.filter(
            Q(created_at__year__gte=start_year, created_at__month__gte=start_month) &
            Q(created_at__year__lte=end_year, created_at__month__lte=end_month)
        )

    elif filter_type == "yearRange" and start and end:
        services = services.filter(created_at__year__gte=start, created_at__year__lte=end)

    # Count statistics for the dashboard
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()

    context = {
        'applied_services': services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count,
        'current_filter': status,  # Track the applied status filter
        'search_filter': filter_type  # Track the applied search filter
    }

    return render(request, 'admin_dashboard.html', context)

# Filter applied services based on the filter type
def filter_applied_services(request):
    filter_type = request.GET.get('filterType', 'date')  # Default to 'date'
    query = request.GET.get('query', '')
    start = request.GET.get('start', '')
    end = request.GET.get('end', '')

    # Start with all applied services
    applied_services = Apply.objects.all()

    
    if filter_type == "date" and query:
        # Assuming query is a date in the format 'YYYY-MM-DD'
        applied_services = applied_services.filter(created_at=query)
        
    elif filter_type == "month" and query:
        # Extract year and month from query (e.g., '2025-02')
        year, month = query.split('-')
        applied_services = applied_services.filter(
            created_at__year=year, created_at__month=month
        )
        
    elif filter_type == "year" and query:
        # Filter by year
        applied_services = applied_services.filter(created_at__year=query)
        
    elif filter_type == "dateRange" and start and end:
        # Filter by date range (start and end dates)
        applied_services = applied_services.filter(created_at__range=[start, end])
        
    elif filter_type == "monthRange" and start and end:
        # Extract year and month from start and end (e.g., '2025-02')
        start_year, start_month = start.split('-')
        end_year, end_month = end.split('-')

        # Filter by range based on year and month
        applied_services = applied_services.filter(
            Q(created_at__year__gte=start_year, created_at__month__gte=start_month) &
            Q(created_at__year__lte=end_year, created_at__month__lte=end_month)
        )
        
    elif filter_type == "yearRange" and start and end:
        # Filter by year range
        applied_services = applied_services.filter(created_at__year__gte=start, created_at__year__lte=end)
       
    # Gather statistics for the dashboard
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()

    # Prepare context to render the filtered data
    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count,
        'current_filter': 'all'  # Track the active filter
    }
    return render(request, 'admin_dashboard.html', context)

# View to reset the applied services filter and show all tasks
def reset_filter_applied_services(request):
    # Reset the filter, show all applied services
    applied_services = Apply.objects.all()

    # Gather statistics for the dashboard
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()

    # Prepare context to render all services
    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count,
        'current_filter': 'all'  # No active filter
    }
    return render(request, 'admin_dashboard.html', context)

# View to handle form submission
def add_service(request):

    if request.method == 'POST':
        # Extract customer data from the form
        name = request.POST.get('name')
        address = request.POST.get('address')
        contact_number = request.POST.get('contact_number')
        whatsapp_number = request.POST.get('whatsapp_number')
        referred_by = request.POST.get('referred_by')

        # Check if the customer already exists using  parameters
        customer = Customer.objects.filter(
            contact_number=contact_number,
        ).first()

        is_new_customer = False

        # If the customer doesn't exist, create a new one
        if not customer:
            try:
                customer = Customer.objects.create(
                    name=name,
                    address=address,
                    contact_number=contact_number,
                    whatsapp_number=whatsapp_number,
                    referred_by=referred_by,
                )
                is_new_customer = True
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error creating customer: {str(e)}'})

        form = AppliedServiceForm(request.POST, request.FILES)
        if form.is_valid():
            apply_instance = form.save(commit=False)

            image_paths = []
            for image in request.FILES.getlist('photos_of_item'):
                image_name = default_storage.save(f'upload/{image.name}', image)
                image_paths.append(image_name)
    
            # Save image paths as a comma-separated string
            apply_instance.photos_of_item = ",".join(image_paths)
            apply_instance.customer = customer
            apply_instance.save()
            if customer.whatsapp_number:
                message = f"Dear {customer.name}, your application for '{apply_instance.work_type}' has been successfully submitted and is currently 'assigned'."
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

            return JsonResponse({'success': True, 'message': 'Service added successfully!', 'is_new_customer': is_new_customer})

        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    return render(request, 'admin_dashboard.html')

# View to handle dynamic customer search

def search_customer(request):
    query = request.GET.get('q', '').strip()  # Get the query and remove any leading/trailing spaces

    if query:
        # Normalize the query by removing '+91' if present
        normalized_query = query.replace('+91', '')

        # Normalize the database values and filter
        customers = Customer.objects.annotate(
            normalized_contact_number=Replace('contact_number', Value('+91'), Value(''))
        ).filter(normalized_contact_number__icontains=normalized_query)

        if customers:
            results = [
            {
                'id': customer.id,
                'name': customer.name,
                'address': customer.address,
                'contact_number':customer.contact_number,
                'whatsapp_number': customer.whatsapp_number,
                'referred_by': customer.referred_by
            }
            for customer in customers]
            return JsonResponse({'exists': True, 'results': results})
        else:
            return JsonResponse({'exists': False, 'message': 'Customer not found. Please enter details manually.'})
    else:
        return JsonResponse({'exists': False, 'message': 'No query provided.'})
    
def get_users(request):
    technicians = CustomUser.objects.filter(role='technician').values('id', 'username')
    return JsonResponse(list(technicians), safe=False)

def technician_list(request):
    technicians = CustomUser.objects.filter(role="technician").values("username", "email")
    return JsonResponse({"technicians": list(technicians)})

def add_technician(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        print("Received data:", username, email)  # Debugging

        # Validation
        if not username or not email or not password:
            return JsonResponse({"success": False, "error": "All fields are required."}, status=400)

        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({"success": False, "error": "Username already exists."}, status=400)

        # Create technician
        technician = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='technician',
            is_staff=True
        )
        technician.save()

        print("Technician saved:", technician.username)  # Debugging

        return JsonResponse({
            "success": True,
            "message": "Technician added successfully!",
            "technician": {"username": technician.username, "email": technician.email}
        })

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

def list_technicians(request):
    technicians = CustomUser.objects.filter(role='technician')
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()
    
    context = {
        'technicians': technicians,
        'customer_count': customer_count,
        'total_services': total_services,     
        'technician_count': technician_count, 
    }

    return render(request, 'list_technicians.html',context)
    
def delete_technician(request, technician_id):
    if request.method == "POST":
        technician = get_object_or_404(CustomUser, id=technician_id)

        # Delete the technician
        technician.delete()

        return redirect('list_technicians')  # Redirect after successful deletion

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

def extra_work_admin(request, service_id):
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()
   
    try:
        apply_instance = Apply.objects.get(id=service_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')

    fuel_charges = FuelCharge.objects.filter(apply=apply_instance)
    food_allowances = FoodAllowance.objects.filter(apply=apply_instance)
    items_purchased = ItemPurchased.objects.filter(apply=apply_instance)
    vendors_info = VendorInfo.objects.filter(apply=apply_instance)
    current_status_entries = CurrentStatus.objects.filter(apply=apply_instance)
    cards = []
    if fuel_charges:
        cards.append("fuel")
    if food_allowances:
        cards.append("food")
    if vendors_info:
        cards.append("vendors")
    if items_purchased:
        cards.append("items")

    context = {
        'customer_count': customer_count,
        'total_services': total_services,     
        'technician_count': technician_count, 
        'apply_instance': apply_instance,
        'fuel_charges': fuel_charges,
        'food_allowances': food_allowances,
        'items_purchased': items_purchased,
        'vendors_info': vendors_info,
        'current_status_entries': current_status_entries,
        'fuel_total': fuel_charges.aggregate(total=Sum('cost'))['total'] or 0,
        'food_total': food_allowances.aggregate(total=Sum('cost'))['total'] or 0,
        'items_total': items_purchased.aggregate(total=Sum('price'))['total'] or 0,
        'vendor_total': vendors_info.aggregate(total=Sum('vendor_cost'))['total'] or 0,
        "cards": cards,
    }
    return render(request, 'additional_charges.html', context)



def add_customer(request):
    if request.method == "POST":
        print("Received POST Data:", request.POST.dict())  # Debugging

        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        contact_number = request.POST.get('contact_number', '').strip()
        whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        referred_by = request.POST.get('referred_by', '').strip()

        # Validation checks
        if not name or not contact_number:
            return JsonResponse({"success": False, "error": "Name and Contact Number are required."}, status=400)

        if Customer.objects.filter(contact_number=contact_number).exists():
            return JsonResponse({"success": False, "error": "A customer with this contact number already exists."}, status=400)

        # Create the new customer
        customer = Customer.objects.create(
            name=name,
            address=address,
            contact_number=contact_number,
            whatsapp_number=whatsapp_number,
            referred_by=referred_by,
        )
        customer.save()

        print("Customer Created:", customer)  # Debugging Line
        return JsonResponse({"success": True, "message": "Customer added successfully!"}, status=201)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)


def delete_customer(request, customer_id):
    if request.method == "POST":
        try:
            customer = Customer.objects.get(id=customer_id)
            Apply.objects.filter(contact_number=customer.contact_number).delete()
            customer.delete()
            messages.success(request, "Customer and related services deleted successfully!")
        except Customer.DoesNotExist:
            messages.error(request, "Customer not found.")
        return redirect('new_customer')

def new_customer(request):
    customers=Customer.objects.all()
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()
    
    context = {
        'customers':customers,
        'customer_count': customer_count,
        'total_services': total_services,     
        'technician_count': technician_count, 
    }

    return render(request,'new_customer.html',context)



def view_applied_services(request):
    dict_services = {
        'applied_services': Apply.objects.all()
    }
    return render(request, 'display_applied_services.html',dict_services)



def update_applied_service(request, service_id):
    applied_service = get_object_or_404(Apply, id=service_id)
    
    if request.method == "POST":
        service_by_id = request.POST.get('service_by')  # Get the selected user ID
        work_type = request.POST.get('work_type')
        item_name_or_number = request.POST.get('item_name_or_number')
        issue = request.POST.get('issue', '')
        photos_of_item = request.FILES.get('photos_of_item')
        estimation_document = request.FILES.get('estimation_document')
        estimated_price = request.POST.get('estimated_price', '')
        estimated_date = request.POST.get('estimated_date', '')
        any_other_comments = request.POST.get('any_other_comments', '')

        try:
            service_by_user = CustomUser.objects.get(id=service_by_id)  # Fetch the user object
            applied_service.service_by = service_by_user
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "Invalid user selected for service."}, status=400)

        applied_service.work_type = work_type
        applied_service.item_name_or_number = item_name_or_number
        applied_service.issue = issue
        if photos_of_item:
            applied_service.photos_of_item = photos_of_item
        if estimation_document:
            applied_service.estimation_document = estimation_document
        applied_service.estimated_price = estimated_price
        applied_service.estimated_date = estimated_date
        applied_service.any_other_comments = any_other_comments
        applied_service.save()

        # Return updated data as JSON response
        updated_data = {
            "id": applied_service.id,
            "service_by": applied_service.service_by.username,
            "work_type": applied_service.work_type,
            "item_name_or_number": applied_service.item_name_or_number,
            "issue": applied_service.issue,
            "estimated_price": applied_service.estimated_price,
            "estimated_date": applied_service.estimated_date.strftime('%Y-%m-%d') if applied_service.estimated_date else "",
            "any_other_comments": applied_service.any_other_comments,
        }
        return JsonResponse(updated_data)

    # If it's a GET request, just render the modal form without any processing.
    users = CustomUser.objects.all()
    context = {
        'applied_service': applied_service,
        'users': users,
    }
    return render(request, 'admin_dashboard.html', context)



def delete_applied_service(request, service_id):
    if request.method == "POST":
        try:
            Apply.objects.get(id=service_id).delete()
            return redirect('admin_dashboard')  
        except Apply.DoesNotExist:
            return redirect('admin_dashboard')


