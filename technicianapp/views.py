from django.shortcuts import render,redirect,get_object_or_404
from velvetekapp.models import Apply,Customer
from loginapp.models import CustomUser
from django.contrib import messages
from django.http import JsonResponse
from technicianapp.models import FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus
import urllib
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
import json
from django.core.files.storage import default_storage
from .forms import AppliedServiceForm
from django.db.models.functions import Replace
from django.db.models import Value
from django.db.models import OuterRef, Subquery
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.utils import timezone
from django.utils.timezone import now
import os


def get_service(request, service_id):
    service = get_object_or_404(Apply, id=service_id)
    apply_instance = get_object_or_404(Apply, id=service_id)
    
    # Get stored photo file paths
    existing_photos = apply_instance.get_photos()
    existing_photos = [request.build_absolute_uri(f'/media/{photo}') for photo in existing_photos]


    service_data = {
        "contact_number": service.contact_number,
        "name": service.name,
        "address": service.address,
        "whatsapp_number": service.whatsapp_number,
        "referred_by": service.referred_by,
        "service_by": service.service_by.username,
        "work_type": service.work_type,
        "item_name_or_number": service.item_name_or_number,
        "issue": service.issue,
        "photos_of_item": existing_photos,
        "estimation_document": service.estimation_document.url if service.estimation_document else None,
        "estimated_price": service.estimated_price,
        "estimated_date": service.estimated_date.strftime("%Y-%m-%d") if service.estimated_date else "",
        "any_other_comments": service.any_other_comments,
    }

    return JsonResponse(service_data)

def update_service(request, service_id):
    if request.method == "POST":
        service = get_object_or_404(Apply, id=service_id)
       

        service.work_type = request.POST.get("work_type", service.work_type)
        service.item_name_or_number = request.POST.get("item_name_or_number", service.item_name_or_number)
        service.issue = request.POST.get("issue", service.issue)
        service.estimated_price = request.POST.get("estimated_price", service.estimated_price)
        service.estimated_date = request.POST.get("estimated_date", service.estimated_date)
        service.any_other_comments = request.POST.get("any_other_comments", service.any_other_comments)

        # ✅ Handle Estimation Document Upload
        if "estimation_document" in request.FILES:
            estimation_doc = request.FILES["estimation_document"]
            doc_name = f'pdf/{estimation_doc.name}'
            service.estimation_document = default_storage.save(doc_name, estimation_doc)

        # Handle New Photos
        image_paths = service.photos_of_item.split(",") if service.photos_of_item else []

        # 🔹 Get New Uploaded Files
        for image in request.FILES.getlist('photos_of_item'):
            image_name = default_storage.save(f'upload/{image.name}', image)
            image_paths.append(image_name)

        # 🔹 Handle Removed Files
        removed_files = request.POST.get("removed_files")

        if removed_files:
            try:
                removed_files = json.loads(removed_files)  # Convert JSON string to Python list
                print("Received Removed Files:", removed_files)  # Debugging
                removed_files = {file.replace("http://127.0.0.1:8000/media/", "") for file in removed_files}
                # Remove from list & delete from storage
                image_paths = [img for img in image_paths if img not in removed_files]
                for img in removed_files:
                    if default_storage.exists(img):
                        default_storage.delete(img)
                        print(f"Deleted: {img}")  # Debugging

            except json.JSONDecodeError:
                print("Invalid JSON in removed_files")

        # 🔹 Update the Database
        service.photos_of_item = ",".join(image_paths)
        print("Updated Image Paths:", service.photos_of_item)  # Debugging


        service.save()
        messages.success(request, "Service updated successfully!")  # Flash message in Django

        return JsonResponse({"success": True})
    
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

def switch_tasks(request, status=None):
    # Subquery to get the latest status for each Apply instance
    current_filter = request.GET.get('filter', 'all')
    latest_status_subquery = CurrentStatus.objects.filter(
        apply=OuterRef('pk')
    ).order_by('-date').values('status')[:1]

    # Base queryset: Get all Apply instances for the logged-in technician
    services = Apply.objects.filter(service_by=request.user).annotate(
        latest_status=Subquery(latest_status_subquery)
    )

    # Filter services based on the status parameter
    if status and status.lower() != 'all':
        # Ensure the status filter is case-insensitive and exact
        services = services.filter(latest_status__iexact=status)

    # Counts for the cards
    technician_customers = Apply.objects.filter(service_by=request.user) if request.user.is_authenticated else None
    total_services = technician_customers.count() if technician_customers else 0
    pending_task = CurrentStatus.objects.filter(technician_name=request.user.username, status="Pending").count()
    completed_task = CurrentStatus.objects.filter(technician_name=request.user.username, status="Completed").count()
    
    context = {
        'technician_customers': services,
        'total_services': total_services,
        'pending_task': pending_task,
        'completed_task': completed_task,
        'current_filter':status,
        'MEDIA_URL': settings.MEDIA_URL, 
    }
    return render(request, 'technician_dashboard.html', context)
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
             # Create the current status entry

            if not apply_instance.current_status_entries.exists():
                CurrentStatus.objects.create(
                    date=apply_instance.estimated_date if apply_instance.estimated_date else timezone.now(),
                    technician_name=request.user.username,  # Use assigned technician
                    status="Assigned",
                    apply=apply_instance,
                    customer_name=apply_instance.name,
                    issue=apply_instance.issue,
                )

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

# View to handle dynamic customer searc
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

def update_current_status(request, apply_id):
    if request.method == 'POST':
        try:
            apply = get_object_or_404(Apply, id=apply_id)  

            # Get latest status entry
            latest_status = apply.current_status_entries.order_by('-date').first()

            if latest_status:
                new_status = request.POST.get('status', 'Pending')  # Default to "Pending"
                status_date = request.POST.get('date', now().date())  # Use today's date if none is provided

                latest_status.status = new_status
                latest_status.date = status_date
                latest_status.technician_name = request.user.username  # Assign logged-in user
                latest_status.save()

                # Also update Apply model
                apply.status = new_status
                apply.save()

                return JsonResponse({"success": True, "status": new_status})
            else:
                return JsonResponse({"error": "No existing status entry found"}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
  
def tech_pending_services(request):
    pending_services = CurrentStatus.objects.filter(
        technician_name=request.user.username, status="Pending"
    ).order_by('date')

    context = {
        'pending_services': pending_services,
    }
    return render(request, 'tech_pending_services.html', context)

def technician_add_service(request):
    details = None

    # Check for customer via GET request
    if 'contact_number' in request.GET:
        contact_number = request.GET.get('contact_number', '').strip()
        try:
            details = Customer.objects.get(contact_number=contact_number)
        except Customer.DoesNotExist:
            messages.info(request, "No customer found with this contact number. You can add their details.")

    # Handle POST request
    if request.method == 'POST':
        # Extract customer details from POST data
        contact_number = request.POST.get('contact_number')
        name = request.POST.get('name')
        address = request.POST.get('address')
        whatsapp_number = request.POST.get('whatsapp')
        referred_by = request.POST.get('referred_by')

        # Check if customer exists; if not, create a new one
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

        # Extract service details from POST data
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
            # Fetch the technician handling the service
            service_by_user = CustomUser.objects.get(id=service_by_id)

            # Create the service request
            apply_instance = Apply.objects.create(
                customer=customer,
                name=customer.name,
                address=customer.address,
                contact_number=customer.contact_number,
                whatsapp_number=customer.whatsapp_number,
                referred_by=customer.referred_by,
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

            # Create the current status entry
            if not apply_instance.current_status_entries.exists():
                CurrentStatus.objects.create(
                date=apply_instance.estimated_date,
                technician_name=service_by_user.username,
                status="Assigned",
                apply=apply_instance,
                customer_name=apply_instance.name,
                issue=apply_instance.issue,
    )

            # Send a WhatsApp message if a WhatsApp number is available
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

            return redirect('technician_add_service')

        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid service provider.")

    # Fetch all technicians for the dropdown list
    users = CustomUser.objects.all()

    # Render the form
    return render(request, 'technician_add_service.html', {'details': details, 'users': users})

def technician_add_customer(request):
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

def technician_new_customer(request):
    customers = Customer.objects.all()
    return render(request, 'technician_add_customer.html', {'customers': customers})


def update_customer(request, customer_id):
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            new_contact_number = request.POST.get('contact_number', customer.contact_number)

            # Check if the contact number already exists in another customer
            if Customer.objects.filter(contact_number=new_contact_number).exclude(id=customer_id).exists():
                return JsonResponse({"success": False, "error": "This contact number is already in use!"}, status=400)

            # Update customer details
            customer.name = request.POST.get('name', customer.name)
            customer.address = request.POST.get('address', customer.address)
            customer.contact_number = new_contact_number
            customer.whatsapp_number = request.POST.get('whatsapp', customer.whatsapp_number)
            customer.referred_by = request.POST.get('referred_by', customer.referred_by)
            customer.save()

            return JsonResponse({"success": True, "message": "Customer updated successfully!"})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request!"}, status=400)


def extra_work_technician(request, apply_id):
    try:
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')

    return render(request, 'extra_work_tech.html', {'apply_instance': apply_instance})

def fuelcharge(request, apply_id):
    try:
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')

    technician_name = request.user.get_full_name() or request.user.username

    if request.method == "POST":
        technician_name = request.POST.get('technician_name') or technician_name
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        kilometers = request.POST.get('kilometers')

        if not all([technician_name, date, purpose, kilometers]):
            messages.error(request, "All fields are required except cost.")
            return redirect('fuelcharge', apply_id=apply_id)

        try:
            kilometers = float(kilometers)  
            cost = kilometers * 3  
            customer_name = apply_instance.name
            issue = apply_instance.issue

            FuelCharge.objects.create(
                apply=apply_instance,
                technician_name=technician_name, 
                date=date,
                purpose=purpose,
                kilometers=kilometers,
                cost=cost,  
                customer_name=customer_name,
                issue=issue
            )
            messages.success(request, "Fuel charge added successfully!")
        except ValueError:
            messages.error(request, "Invalid value for kilometers. Please enter a numeric value.")
            return redirect('fuelcharge', apply_id=apply_id)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('fuelcharge', apply_id=apply_id)

        return redirect('fuelcharge', apply_id=apply_id)

    fuel_charges = FuelCharge.objects.filter(apply=apply_instance)

    return render(request, 'fuelcharge.html', {
        'apply': apply_instance,
        'fuel_charges': fuel_charges,
        'technician_name': technician_name  
    })


def update_fuelcharge(request, fuel_id):
    """Update an existing fuel charge entry."""
    fuel = get_object_or_404(FuelCharge, id=fuel_id)

    if request.method == "POST":
        technician_name = request.POST.get('technician_name')
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        kilometers = request.POST.get('kilometers')
        cost = request.POST.get('cost')

        # Ensure all fields are filled
        if not all([technician_name, date, purpose, kilometers, cost]):
            messages.error(request, "All fields are required.")
            return redirect('fuelcharge', apply_id=fuel.apply.id)  

        try:
            fuel.technician_name = technician_name
            fuel.date = date
            fuel.purpose = purpose
            fuel.kilometers = float(kilometers)
            fuel.cost = float(cost)
            fuel.save()

            messages.success(request, "Fuel charge updated successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return redirect('fuelcharge', apply_id=fuel.apply.id)

def delete_fuelcharge(request, fuel_id):
    fuel = get_object_or_404(FuelCharge, id=fuel_id)

    if request.method == "POST":
        try:
            fuel.delete()
            messages.success(request, "Fuel charge deleted successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting: {str(e)}")
        return redirect('fuelcharge', apply_id=fuel.apply.id)  
    messages.error(request, "Invalid request method.")
    return redirect('fuelcharge', apply_id=fuel.apply.id)  

def foodallowance(request, apply_id):
    try:
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')  

    if request.method == "POST":
        technician_name = request.POST.get('technician_name') or request.user.get_full_name() or request.user.username
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        cost = request.POST.get('cost')

        if not all([technician_name, date, purpose, cost]):
            messages.error(request, "All fields are required.")
            return redirect('food_allowance', apply_id=apply_id)

        try:
            customer_name = apply_instance.name 
            issue = apply_instance.issue 

            FoodAllowance.objects.create(
                apply=apply_instance,
                technician_name=technician_name,
                date=date,
                purpose=purpose,
                cost=cost,
                customer_name=customer_name, 
                issue=issue 
            )
            messages.success(request, "Food allowance added successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('food_allowance', apply_id=apply_id)

        return redirect('food_allowance', apply_id=apply_id)

    food_allowances = FoodAllowance.objects.filter(apply=apply_instance)

    # Pass the logged-in user's name as the default value for technician_name
    context = {
        'apply': apply_instance,
        'food_allowances': food_allowances,
        'technician_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'food_allowance.html', context)

def update_food_allowance(request, food_id):
    food = get_object_or_404(FoodAllowance, id=food_id)

    if request.method == "POST":
        technician_name = request.POST.get('technician_name')
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        cost = request.POST.get('cost')

        if not all([technician_name, date, purpose, cost]):
            messages.error(request, "All fields are required.")
            return redirect('food_allowance', apply_id=food.apply.id)  

        try:
            food.technician_name = technician_name
            food.date = date
            food.purpose = purpose
            food.cost = cost
            food.save()

            messages.success(request, "Food allowance updated successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    return redirect('food_allowance', apply_id=food.apply.id)  



def delete_food_allowance(request, allowance_id):
    food_allowance = get_object_or_404(FoodAllowance, id=allowance_id)
    apply_id = food_allowance.apply.id  

    if request.method == "POST":
        try:
            food_allowance.delete()
            messages.success(request, "Food allowance deleted successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting: {str(e)}")
        return redirect('food_allowance', apply_id=apply_id)  

    messages.error(request, "Invalid request method.")
    return redirect('food_allowance', apply_id=apply_id)

def item_purchased(request, apply_id):
    try:
        # Fetch the Apply instance based on apply_id
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')  

    if request.method == "POST":
        date = request.POST.get('date')
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        bill_photo = request.FILES.get('bill_photo')  

        if not all([date, item_name, price, bill_photo]):
            messages.error(request, "All fields are required.")
            return redirect('item_purchased', apply_id=apply_id)

        try:
            customer_name = apply_instance.name  
            issue = apply_instance.issue  

          
            ItemPurchased.objects.create(
                apply=apply_instance,
                date=date,
                item_name=item_name,
                price=price,
                bill_photo=bill_photo,
                customer_name=customer_name, 
                issue=issue  
            )
            messages.success(request, "Item purchased successfully added!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('item_purchased', apply_id=apply_id)

        return redirect('item_purchased', apply_id=apply_id)

    items = ItemPurchased.objects.filter(apply=apply_instance)
    context = {
        'apply': apply_instance,
        'items': items
    }
    return render(request, 'item_purchased.html', context)

def save_item_purchased(request):
    if request.method == "POST":
        date = request.POST.get('date')
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        bill_photo = request.FILES.get('bill_photo')

        item_purchased = ItemPurchased(
            date=date,
            item_name=item_name,
            price=price,
            bill_photo=bill_photo
        )
        item_purchased.save()
        messages.success(request, "Item purchased saved successfully.")
        return redirect('technician_dashboard')

def update_item_purchased(request, item_id):
    item = get_object_or_404(ItemPurchased, id=item_id)
    
    if request.method == "POST":
        date = request.POST.get('date')
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        bill_photo = request.FILES.get('bill_photo')  
        
        if not all([date, item_name, price]):
            messages.error(request, "All fields except bill photo are required.")
            return redirect('item_purchased', apply_id=item.apply.id)

        try:
            item.date = date
            item.item_name = item_name
            item.price = price

            if bill_photo:
                item.bill_photo = bill_photo

            item.save()
            messages.success(request, "Item purchased updated successfully!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    return redirect('item_purchased', apply_id=item.apply.id)

def delete_item_purchased(request, item_id):
    item = get_object_or_404(ItemPurchased, id=item_id)
    apply_id = item.apply.id  
    if request.method == "POST":
        try:
            item.delete()
            messages.success(request, "Item purchased entry deleted successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting: {str(e)}")
        return redirect('item_purchased', apply_id=apply_id) 

    messages.error(request, "Invalid request method.")
    return redirect('item_purchased', apply_id=apply_id)

def vendor_info(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)

    if request.method == "POST":
        # Retrieve form data
        date = request.POST.get('date')
        vendor_name = request.POST.get('vendor_name')
        vendor_bill_photo = request.FILES.get('vendor_bill_photo')
        vendor_eta = request.POST.get('vendor_eta')
        vendor_cost = request.POST.get('vendor_cost')

        # Validate required fields
        if not all([date, vendor_name, vendor_bill_photo, vendor_eta, vendor_cost]):
            messages.error(request, "All fields are required.")
            return redirect('vendor_info', apply_id=apply_id)

        try:
            # Fetch customer_name and issue from Apply instance
            customer_name = apply_instance.name  # Adjust based on Apply model
            issue = apply_instance.issue  # Adjust based on Apply model

            # Save data to the VendorInfo model
            VendorInfo.objects.create(
                apply=apply_instance,
                date=date,
                vendor_name=vendor_name,
                vendor_bill_photo=vendor_bill_photo,
                vendor_eta=vendor_eta,
                vendor_cost=vendor_cost,
                customer_name=customer_name,  # Store customer_name
                issue=issue  # Store issue
            )
            messages.success(request, "Vendor info successfully added!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('vendor_info', apply_id=apply_id)

        return redirect('vendor_info', apply_id=apply_id)

    # Fetch all VendorInfo records for the current Apply instance
    vendors = VendorInfo.objects.filter(apply=apply_instance)
    context = {
        'apply': apply_instance,
        'vendors': vendors,
    }
    return render(request, 'vendor_info.html', context)

def save_vendor_info(request):
    if request.method == "POST":
        date = request.POST.get('date')
        vendor_name = request.POST.get('vendor_name')
        vendor_bill_photo = request.FILES.get('vendor_bill_photo')
        vendor_eta = request.POST.get('vendor_eta')
        vendor_cost = request.POST.get('vendor_cost')

        vendor_info = VendorInfo(
            date=date,
            vendor_name=vendor_name,
            vendor_bill_photo=vendor_bill_photo,
            vendor_eta=vendor_eta,
            vendor_cost=vendor_cost
        )
        vendor_info.save()
        messages.success(request, "Vendor info saved successfully.")
        return redirect('technician_dashboard')
    
    

def update_vendor_info(request, vendor_id):
    vendor = get_object_or_404(VendorInfo, id=vendor_id)
    
    if request.method == "POST":
        date = request.POST.get('date')
        vendor_name = request.POST.get('vendor_name')
        vendor_eta = request.POST.get('vendor_eta')
        vendor_cost = request.POST.get('vendor_cost')
        vendor_bill_photo = request.FILES.get('vendor_bill_photo')  

        if not all([date, vendor_name, vendor_eta, vendor_cost]):
            messages.error(request, "All fields except vendor bill photo are required.")
            return redirect('vendor_info', apply_id=vendor.apply.id)

        try:
            vendor.date = date
            vendor.vendor_name = vendor_name
            vendor.vendor_eta = vendor_eta
            vendor.vendor_cost = vendor_cost

            if vendor_bill_photo:
                vendor.vendor_bill_photo = vendor_bill_photo

            vendor.save()
            messages.success(request, "Vendor info updated successfully!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    return redirect('vendor_info', apply_id=vendor.apply.id)


def delete_vendor_info(request, vendor_id):
    vendor = get_object_or_404(VendorInfo, id=vendor_id)
    apply_id = vendor.apply.id  

    if request.method == "POST":
        try:
            vendor.delete()
            messages.success(request, "Vendor info entry deleted successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting: {str(e)}")
        return redirect('vendor_info', apply_id=apply_id) 

    messages.error(request, "Invalid request method.")
    return redirect('vendor_info', apply_id=apply_id)
    
def delete_current_status(request, status_id):

    current_status = get_object_or_404(CurrentStatus, id=status_id)
    apply_id = current_status.apply.id  

    if request.method == "POST":
        try:
            current_status.delete()
            messages.success(request, "Current status entry deleted successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting: {str(e)}")
        return redirect('current_status', apply_id=apply_id)  

    
    messages.error(request, "Invalid request method.")
    return redirect('current_status', apply_id=apply_id)

def pending_tasks(request):
    pending_tasks = CurrentStatus.objects.filter(
        apply__service_by=request.user, 
        status='Pending'
    )

    return render(request, 'tech_pending_services.html', {
        'pending_tasks': pending_tasks
    })

def completed_tasks(request):
    completed_tasks = CurrentStatus.objects.filter(
        apply__service_by=request.user,
        status='Completed'
    )

    return render(request, 'completed_task.html', {
        'completed_tasks': completed_tasks
    })