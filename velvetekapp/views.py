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

from django.db.models import OuterRef, Subquery

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
    apply_services = Apply.objects.all()
    customer_count = apply_services.values('name').distinct().count()
    technician_count = apply_services.values('service_by').distinct().count()
    total_services = apply_services.count()

    # Prepare context to render the filtered data
    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count,
        'current_filter': filter_type  # Track the active filter
    }
    return render(request, 'admin_dashboard.html', context)

# View to reset the applied services filter and show all tasks
def reset_filter_applied_services(request):
    # Reset the filter, show all applied services
    applied_services = Apply.objects.all()

    # Gather statistics for the dashboard
    customer_count = applied_services.values('name').distinct().count()
    technician_count = applied_services.values('service_by').distinct().count()
    total_services = applied_services.count()

    # Prepare context to render all services
    context = {
        'applied_services': applied_services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count,
        'current_filter': 'all'  # No active filter
    }
    return render(request, 'admin_dashboard.html', context)

def switch_task(request, status=None):
    latest_status_subquery = CurrentStatus.objects.filter(
        apply=OuterRef('pk')
    ).order_by('-date').values('status')[:1]

    # Base queryset: Get all Apply instances (irrespective of the technician)
    services = Apply.objects.all().annotate(
        latest_status=Subquery(latest_status_subquery)
    )

    # Filter services based on the status parameter
    if status and status.lower() != 'all':
        # Ensure the status filter is case-insensitive and exact
        services = services.filter(latest_status__iexact=status)

    # Counts for the cards
    customer_count = Customer.objects.count()
    total_services = Apply.objects.count()
    technician_count = CustomUser.objects.filter(role='technician').count()
    
    context = {
        'applied_services': services,
        'customer_count': customer_count,
        'total_services': total_services,
        'technician_count': technician_count, 
        'current_filter': status
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

        # Check if the customer already exists using all parameters
        customer = Customer.objects.filter(
            contact_number=contact_number,
            whatsapp_number=whatsapp_number,
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
            apply_instance.save()
            return JsonResponse({'success': True,'message': 'Service added successfully!',
                'is_new_customer': is_new_customer,})
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



def add_technician(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        # Validation checks
        if not username or not email or not password:
            return JsonResponse({"success": False, "error": "All fields are required."}, status=400)

        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({"success": False, "error": "Username already exists. Please choose a different one."}, status=400)

        # Create the technician user
        technician = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='technician',
            is_staff=True
        )
        technician.save()

        return JsonResponse({"success": True, "message": "Technician added successfully!"})

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

def extra_work_admin(request, apply_id):
    try:
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')

    fuel_charges = FuelCharge.objects.filter(apply=apply_instance)
    food_allowances = FoodAllowance.objects.filter(apply=apply_instance)
    items_purchased = ItemPurchased.objects.filter(apply=apply_instance)
    vendors_info = VendorInfo.objects.filter(apply=apply_instance)
    current_status_entries = CurrentStatus.objects.filter(apply=apply_instance)

    context = {
        'apply_instance': apply_instance,
        'fuel_charges': fuel_charges,
        'food_allowances': food_allowances,
        'items_purchased': items_purchased,
        'vendors_info': vendors_info,
        'current_status_entries': current_status_entries,
    }
    return render(request, 'extra_work_admin.html', context)

def view_fuelcharge_details(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)
    fuel_details = FuelCharge.objects.filter(apply=apply_instance)

    context = {
        'apply_instance': apply_instance,
        'fuel_details': fuel_details
    }

    return render(request, 'view_fuelcharge.html', context)

def view_food_allowance_details(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)
    food_allowances = FoodAllowance.objects.filter(apply=apply_instance)

    context = {
        'apply_instance': apply_instance,
        'food_allowances': food_allowances
    }

    return render(request, 'view_food_allowance.html', context)

def view_item_purchased_details(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)
    items = ItemPurchased.objects.filter(apply=apply_instance)

    context = {
        'apply': apply_instance,
        'items': items,
    }
    return render(request, 'view_item_purchased.html', context)

def view_vendor_info_details(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)
    vendors = VendorInfo.objects.filter(apply=apply_instance)

    context = {
        'apply': apply_instance,
        'vendors': vendors,
    }

    return render(request, 'view_vendor_info.html', context)

def view_current_status_details(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)
    statuses = CurrentStatus.objects.filter(apply=apply_instance)

    context = {
        'apply': apply_instance,
        'statuses': statuses,
    }

    return render(request, 'view_current_status.html', context)

def add_customer(request):
    if request.method == "POST":
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
        Customer.objects.create(
            name=name,
            address=address,
            contact_number=contact_number,
            whatsapp_number=whatsapp_number,
            referred_by=referred_by,
        )

        return JsonResponse({"success": True, "message": "Customer added successfully!"})

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

# def add_customer(request):
#     if 'term' in request.GET:
#         term = request.GET.get('term', '').strip()
#         qs = Customer.objects.filter(contact_number__istartswith=term)
#         contact_numbers = [contact.contact_number for contact in qs]
#         return JsonResponse(contact_numbers, safe=False)

#     if request.method == "POST":
#         name = request.POST.get('name', '').strip()
#         address = request.POST.get('address', '').strip()
#         contact_number = request.POST.get('contact_number', '').strip()
#         whatsapp_number = request.POST.get('whatsapp_number', '').strip()
#         reffered_by = request.POST.get('reffered_by', '').strip()

#         # Validation checks
#         if not name or not contact_number:
#             messages.error(request, "Name and Contact Number are required.")
#             return render(request, 'add_customer.html')

#         if Customer.objects.filter(contact_number=contact_number).exists():
#             messages.error(request, "A customer with this contact number already exists.")
#             return render(request, 'add_customer.html')

#         # Create the new customer
#         Customer.objects.create(
#             name=name,
#             address=address,
#             contact_number=contact_number,
#             whatsapp_number=whatsapp_number,
#             reffered_by=reffered_by,
#         )

#         messages.success(request, "Customer added successfully!")
#         # Redirect to admin dashboard
#         return redirect('admin_dashboard')  # Replace 'admin_dashboard' with the actual name of the URL pattern for the admin dashboard

#     return render(request, 'add_customer.html')

def update_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        contact_number = request.POST.get('contact_number', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        referred_by = request.POST.get('referred_by', '').strip()

        if not name or not contact_number:
            messages.error(request, "Name and Contact Number are required.")
            return render(request, 'update_customer.html', {'customer': customer})

        if Customer.objects.filter(contact_number=contact_number).exclude(id=customer.id).exists():
            messages.error(request, "A customer with this contact number already exists.")
            return render(request, 'update_customer.html', {'customer': customer})

        customer.name = name
        customer.address = address
        customer.contact_number = contact_number
        customer.whatsapp_number = whatsapp
        customer.reffered_by = referred_by
        customer.save()

        messages.success(request, "Customer updated successfully!")
        return redirect('new_customer')  

    return render(request, 'update_customer.html', {'customer': customer})

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

def apply_for_service(request):
    details = None
    users = CustomUser.objects.all()  

    if 'contact_number' in request.GET:
        contact_number = request.GET.get('contact_number', '').strip()
        try:
            details = Customer.objects.get(contact_number=contact_number)
        except Customer.DoesNotExist:
            messages.error(request, "No customer found with this contact number.Please add customer.")
            return redirect('apply_for_service')

    if request.method == "POST":
        contact_number = request.POST.get('contact_number')
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
            customer = Customer.objects.get(contact_number=contact_number)
            service_by_user = CustomUser.objects.get(id=service_by_id)

            new_application = Apply.objects.create(
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

            whatsapp_number = customer.whatsapp_number
            if whatsapp_number:
                message = f"Dear {customer.name}, your application for '{work_type}' has been successfully submitted. Thank you for choosing our service."
                encoded_message = urllib.parse.quote(message)
                whatsapp_url = f"https://whatsapimanagment.onrender.com/send-message?phoneNumber={whatsapp_number}&messageBody={encoded_message}"

                try:
                    response = requests.get(whatsapp_url)
                    if response.status_code == 200:
                        messages.success(request, "Application submitted and WhatsApp message sent successfully!")
                    else:
                        messages.error(request, f"Application submitted, but failed to send WhatsApp message. Status Code: {response.status_code}")
                except requests.RequestException as e:
                    messages.error(request, f"Application submitted, but error sending WhatsApp message: {e}")
            else:
                messages.warning(request, "Application submitted successfully, but WhatsApp number is not available.")

            return redirect('apply_for_service')

        except Customer.DoesNotExist:
            messages.error(request, "Invalid customer contact number.")
        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid service provider.")

    context = {
        'details': details,
        'users': users,
    }
    return render(request, 'apply_for_service.html', context)

def view_applied_services(request):
    dict_services = {
        'applied_services': Apply.objects.all()
    }
    return render(request, 'display_applied_services.html',dict_services)

def update_applied_service(request, service_id):
    applied_service = get_object_or_404(Apply, id=service_id)
    users = CustomUser.objects.all()  # Fetch all users for the dropdown

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
            messages.error(request, "Invalid user selected for service.")
            return redirect('update_applied_service', service_id=service_id)

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

        messages.success(request, "Applied service updated successfully!")
        return redirect('admin_dashboard')

    context = {
        'applied_service': applied_service,
        'users': users,  # Pass users for the dropdown
    }
    return render(request, 'update_applied_service.html', context)

def delete_applied_service(request, service_id):
    if request.method == "POST":
        try:
            Apply.objects.get(id=service_id).delete()
            return redirect('admin_dashboard')  
        except Apply.DoesNotExist:
            return redirect('admin_dashboard')


