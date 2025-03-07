from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
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
from django.template.loader import render_to_string
import urllib.parse



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

def add_service(request): 
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        contact_number = request.POST.get('contact_number')
        whatsapp_number = request.POST.get('whatsapp_number')
        referred_by = request.POST.get('referred_by')

        customer = Customer.objects.filter(contact_number=contact_number, whatsapp_number=whatsapp_number).first()
        is_new_customer = False

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

            apply_instance.photos_of_item = ",".join(image_paths)
            apply_instance.save()

            if not apply_instance.current_status_entries.exists():
                CurrentStatus.objects.create(
                    date=apply_instance.estimated_date if apply_instance.estimated_date else timezone.now(),
                    technician_name=request.user.username,  # Use assigned technician
                    status="Assigned",
                    apply=apply_instance,
                    customer_name=apply_instance.name,
                    issue=apply_instance.issue,
                )

            service_by = form.cleaned_data.get('service_by')
            work_type = form.cleaned_data.get('work_type', 'N/A')
            item_name_or_number = form.cleaned_data.get('item_name_or_number', 'N/A')
            issue = form.cleaned_data.get('issue', 'N/A')
            estimated_date = form.cleaned_data.get('estimated_date', 'N/A')
            estimated_price = form.cleaned_data.get('estimated_price', 'N/A')

            def safe_str(value):
                return str(value) if value else "Not Provided"

            service_by_name = safe_str(service_by.username if isinstance(service_by, CustomUser) else "N/A")
            technician_whatsapp = safe_str(service_by.whatsapp_number if isinstance(service_by, CustomUser) else "")
            customer_whatsapp_number = safe_str(customer.whatsapp_number).replace("+", "").strip()


            estimated_date = form.cleaned_data.get('estimated_date')
            estimated_date = estimated_date.strftime("%Y-%m-%d") if estimated_date else "N/A"

            # WhatsApp API Configuration
            ACCESS_TOKEN = "EAAbTzSfoZCw0BOy8x7iLmtjI9vwnVU52GSp40vxnYWCZAoFBZCuBkhmGhSP4r2yOJaxSVXJw5gFuc0GUhFd47eNlpnIFhI51Ml8L4ZCyfokLTH1jowNtxkZBwkvPxdeYBZAEKES4Oycek2N6YINUyaZBmJO82TMKTDa4YYqyQbu8ELaU6UONEZAMGC56wgb1faeVwkRlcwS5ydeuJdm9YwZDZD"
            PHONE_NUMBER_ID = "374854242373692"
            TEMPLATE_NAME = "new_service_message"

            def send_whatsapp_message(phone_number):
                if phone_number:
                    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                    headers = {
                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                        "Content-Type": "application/json"
                    }

                    CUSTOM_TEXT = [
                        {"type": "text", "text": service_by_name},
                        {"type": "text", "text": item_name_or_number},
                        {"type": "text", "text": issue},
                        {"type": "text", "text": estimated_date},
                        {"type": "text", "text": estimated_price},
                    ]

                    payload = {
                        "messaging_product": "whatsapp",
                        "to": phone_number,
                        "type": "template",
                        "template": {
                            "name": TEMPLATE_NAME,
                            "language": {"code": "en"},
                            "components": [
                                {"type": "body", "parameters": CUSTOM_TEXT}
                            ]
                        }
                    }

                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(payload))
                        print(f"WhatsApp response for {phone_number}:", response.status_code, response.json())
                        return response.status_code == 200
                    except requests.RequestException as e:
                        print(f"Error sending WhatsApp to {phone_number}: {e}")
                        return False

            # Send WhatsApp to customer
            customer_msg_sent = send_whatsapp_message(customer_whatsapp_number)

            # Send WhatsApp to technician
            technician_msg_sent = send_whatsapp_message(technician_whatsapp)

            if customer_msg_sent and technician_msg_sent:
                messages.success(request, "Service request submitted. WhatsApp messages sent successfully!")
            elif customer_msg_sent:
                messages.warning(request, "Service request submitted. WhatsApp message sent to customer, but failed for technician.")
            elif technician_msg_sent:
                messages.warning(request, "Service request submitted. WhatsApp message sent to technician, but failed for customer.")
            else:
                messages.warning(request, "Service request submitted, but WhatsApp messages failed.")

            return JsonResponse({'success': True, 'message': 'Service added successfully!', 'is_new_customer': is_new_customer})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})

    return render(request, 'admin_dashboard.html')

def search_customer(request):
    query = request.GET.get('q', '').strip()  
    if query:
        normalized_query = query.replace('+91', '')

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

import logging
logger = logging.getLogger(__name__)

def update_current_status(request, apply_id):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        # Debugging: Log incoming data
        logger.info(f"Received POST data: {request.POST}")

        # Get the Apply object
        apply = get_object_or_404(Apply, id=apply_id)

        # Extract status and date
        new_status = request.POST.get('status')
        status_date = request.POST.get('date')

        if not new_status or not status_date:
            return JsonResponse({"error": "Missing 'status' or 'date' in request"}, status=400)

        # Convert 'now' to current date
        status_date = now().date() if status_date.lower() == 'now' else status_date
        technician_name = request.user.username

        # Get latest status entry
        latest_status = apply.current_status_entries.order_by('-date').first()

        if latest_status:
            # Update latest entry
            latest_status.status = new_status
            latest_status.date = status_date
            latest_status.technician_name = technician_name
            latest_status.save()
        else:
            # Create a new entry if none exists
            CurrentStatus.objects.create(
                apply=apply,
                date=status_date,
                technician_name=technician_name,
                status=new_status,
                customer_name=apply.name if apply.name else "Unknown",
                issue=apply.issue if apply.issue else "No issue specified"
            )

        # Update Apply model
        apply.status = new_status
        apply.save()

        # ✅ WhatsApp Integration
        ACCESS_TOKEN = "EAAbTzSfoZCw0BOy8x7iLmtjI9vwnVU52GSp40vxnYWCZAoFBZCuBkhmGhSP4r2yOJaxSVXJw5gFuc0GUhFd47eNlpnIFhI51Ml8L4ZCyfokLTH1jowNtxkZBwkvPxdeYBZAEKES4Oycek2N6YINUyaZBmJO82TMKTDa4YYqyQbu8ELaU6UONEZAMGC56wgb1faeVwkRlcwS5ydeuJdm9YwZDZD"
        PHONE_NUMBER_ID = "374854242373692"
        TEMPLATE_NAME = "new_service_message"

        def safe_str(value):
            return str(value) if value else "Not Provided"

        # Get customer & technician WhatsApp numbers
        customer_whatsapp_number = safe_str(apply.customer.whatsapp_number).replace("+", "").strip() if apply.customer else ""
        technician_whatsapp = safe_str(request.user.whatsapp_number).replace("+", "").strip()

        def send_whatsapp_message(phone_number):
            if not phone_number:
                return False  # Skip sending if no number is available

            url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }

            CUSTOM_TEXT = [
                {"type": "text", "text": apply.name if apply.name else "No Name"},
                {"type": "text", "text": apply.issue if apply.issue else "No Issue"},
                {"type": "text", "text": new_status},
                {"type": "text", "text": status_date},
                {"type": "text", "text": technician_name},
            ]

            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": TEMPLATE_NAME,
                    "language": {"code": "en"},
                    "components": [
                        {"type": "body", "parameters": CUSTOM_TEXT}
                    ]
                }
            }

            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                response_data = response.json()
                logger.info(f"WhatsApp API Response for {phone_number}: {response.status_code}, {response_data}")

                if response.status_code != 200:
                    logger.error(f"WhatsApp API error: {response_data}")
                return response.status_code == 200
            except requests.RequestException as e:
                logger.error(f"Error sending WhatsApp to {phone_number}: {e}")
                return False

        #  Send WhatsApp Messages
        customer_msg_sent = send_whatsapp_message(customer_whatsapp_number) if customer_whatsapp_number else False
        technician_msg_sent = send_whatsapp_message(technician_whatsapp) if technician_whatsapp else False

        #  Generate success messages
        if customer_msg_sent and technician_msg_sent:
            messages.success(request, "Status updated. WhatsApp messages sent successfully!")
        elif customer_msg_sent:
            messages.warning(request, "Status updated. WhatsApp message sent to customer, but failed for technician.")
        elif technician_msg_sent:
            messages.warning(request, "Status updated. WhatsApp message sent to technician, but failed for customer.")
        else:
            messages.warning(request, "Status updated, but WhatsApp messages failed.")

        #  Return Response
        return JsonResponse({"success": True, "status": new_status})

    except Exception as e:
        logger.error(f"Error updating status: {e}")
        return JsonResponse({"error": str(e)}, status=400)


def update_customer(request, customer_id):
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            new_contact_number = request.POST.get('contact_number', customer.contact_number)

            if Customer.objects.filter(contact_number=new_contact_number).exclude(id=customer_id).exists():
                return JsonResponse({"success": False, "error": "This contact number is already in use!"}, status=400)

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
    apply_instance = get_object_or_404(Apply, id=apply_id)
    technician_name = request.user.get_full_name() or request.user.username
    current_date = now().date()  # Get today's date

    if request.method == "POST":
        technician_name = request.POST.get('technician_name') or technician_name
        date = request.POST.get('date') or current_date  # Use current date if empty
        purpose = request.POST.get('purpose')
        kilometers = request.POST.get('kilometers')
        review = request.POST.get('review')  # Get review from form

        if not all([technician_name, date, purpose, kilometers]):
            messages.error(request, "All fields are required except cost and review.")
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
                review=review,  # Save review
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
        'technician_name': technician_name,
        'current_date': current_date  # Pass current date to template
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

    technician_name = request.user.get_full_name() or request.user.username
    current_date = now().date()  # Get today's date

    if request.method == "POST":
        technician_name = request.POST.get('technician_name') or technician_name
        date = request.POST.get('date') or current_date  # Default to today's date if empty
        purpose = request.POST.get('purpose')
        cost = request.POST.get('cost')
        review = request.POST.get('review')  # Get review input

        if not all([technician_name, date, purpose, cost]):
            messages.error(request, "All fields are required except review.")
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
                review=review,  # Save review
                customer_name=customer_name,
                issue=issue
            )
            messages.success(request, "Food allowance added successfully!")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('food_allowance', apply_id=apply_id)

        return redirect('food_allowance', apply_id=apply_id)

    food_allowances = FoodAllowance.objects.filter(apply=apply_instance)

    context = {
        'apply': apply_instance,
        'food_allowances': food_allowances,
        'technician_name': technician_name,
        'current_date': current_date  # Pass current date to template
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
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')  

    current_date = now().date()  # Get today's date

    if request.method == "POST":
        date = request.POST.get('date') or current_date  # Default to today's date if empty
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        bill_photo = request.FILES.get('bill_photo')
        review = request.POST.get('review')  # Get review input

        if not all([date, item_name, price, bill_photo]):
            messages.error(request, "All fields are required except review.")
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
                review=review,  # Save review
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
        'items': items,
        'current_date': current_date  
    }
    return render(request, 'item_purchased.html', context)
  
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
    current_date = now().date()  # Get today's date

    if request.method == "POST":
        date = request.POST.get('date') or current_date  # Default to today's date if empty
        vendor_name = request.POST.get('vendor_name')
        vendor_bill_photo = request.FILES.get('vendor_bill_photo')
        vendor_eta = request.POST.get('vendor_eta')
        vendor_cost = request.POST.get('vendor_cost')
        review = request.POST.get('review')  # Get review input

        if not all([date, vendor_name, vendor_bill_photo, vendor_eta, vendor_cost]):
            messages.error(request, "All fields are required except review.")
            return redirect('vendor_info', apply_id=apply_id)

        try:
            customer_name = apply_instance.name  
            issue = apply_instance.issue  

            VendorInfo.objects.create(
                apply=apply_instance,
                date=date,
                vendor_name=vendor_name,
                vendor_bill_photo=vendor_bill_photo,
                vendor_eta=vendor_eta,
                vendor_cost=vendor_cost,
                review=review,  # Save review
                customer_name=customer_name,
                issue=issue
            )
            messages.success(request, "Vendor info successfully added!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('vendor_info', apply_id=apply_id)

        return redirect('vendor_info', apply_id=apply_id)

    vendors = VendorInfo.objects.filter(apply=apply_instance)

    context = {
        'apply': apply_instance,
        'vendors': vendors,
        'current_date': current_date  # Pass current date to the template
    }
    return render(request, 'vendor_info.html', context)
   
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