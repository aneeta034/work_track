from django.shortcuts import render,redirect,get_object_or_404
from velvetekapp.models import Apply,Customer
from loginapp.models import CustomUser
from django.contrib import messages
from django.http import JsonResponse
from .models import Apply,FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus
import urllib
import requests
from django.core.management.base import BaseCommand
import json

# Create your views here.

def update_current_status(request, apply_id):
    if request.method == 'POST':
        status_entry = get_object_or_404(CurrentStatus, id=apply_id)
        status_entry.date = request.POST.get('date')
        status_entry.status = request.POST.get('status')
        
        status_entry.technician_name = request.user.username  

        status_entry.save()
        return redirect('technician_dashboard')
    
# def update_current_status(request, apply_id):
#     if request.method == 'POST':
#         try:
#             # Since apply_id is now coming from the URL, no need to extract it from the request body
#             status = json.loads(request.body).get('status')  # Get the status from the request body

#             # Ensure the status is a valid one
#             if status not in ['Pending', 'Assigned', 'Completed']:
#                 return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

#             # Fetch the CurrentStatus object based on apply_id
#             current_status = get_object_or_404(CurrentStatus, apply_id=apply_id)

#             # Update the status field
#             current_status.status = status
#             current_status.save()

#             return JsonResponse({'success': True, 'message': 'Status updated successfully'})
#         except Exception as e:
#             return JsonResponse({'success': False, 'message': str(e)}, status=500)

#     return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

    


    

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
            reffered_by = request.POST.get('reffered_by', '').strip()

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
                reffered_by=reffered_by,
            )

            return JsonResponse({"success": True, "message": "Customer added successfully!"})
    return JsonResponse({"success": False, "error": "Invalid request method."}, status=405)

# def technician_add_customer(request):
#     if request.method == "POST":
#         name = request.POST.get('name', '').strip()
#         address = request.POST.get('address', '').strip()
#         contact_number = request.POST.get('contact_number', '').strip()
#         whatsapp = request.POST.get('whatsapp_number', '').strip()
#         referred_by = request.POST.get('reffered_by', '').strip()

#         if not name or not contact_number:
#             messages.error(request, "Name and Contact Number are required.")
#             return redirect('technician_new_customer')

#         if Customer.objects.filter(contact_number=contact_number).exists():
#             messages.error(request, "A customer with this contact number already exists.")
#             return redirect('technician_new_customer')

#         try:
#             Customer.objects.create(
#                 name=name,
#                 address=address,
#                 contact_number=contact_number,
#                 whatsapp_number=whatsapp,
#                 reffered_by=referred_by,
#             )
#             messages.success(request, "Customer added successfully!")
#         except Exception as e:
#             messages.error(request, f"An error occurred: {str(e)}")

#         return redirect('technician_new_customer')

#     return redirect('technician_new_customer')

def technician_new_customer(request):
    customers = Customer.objects.all()
    return render(request, 'technician_add_customer.html', {'customers': customers})

def update_customer(request, customer_id):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, id=customer_id)
        customer.name = request.POST.get('name', customer.name)
        customer.address = request.POST.get('address', customer.address)
        customer.contact_number = request.POST.get('contact_number', customer.contact_number)
        customer.whatsapp_number = request.POST.get('whatsapp_number', customer.whatsapp_number)
        customer.reffered_by = request.POST.get('reffered_by', customer.reffered_by)
        customer.save()
        messages.success(request, "Customer updated successfully!")
    return redirect('technician_new_customer')

def extra_work_technician(request, apply_id):
    try:
        apply_instance = Apply.objects.get(id=apply_id)
    except Apply.DoesNotExist:
        messages.error(request, "Apply instance not found.")
        return redirect('apply_list')

    return render(request, 'extra_work_tech.html', {'apply_instance': apply_instance})

def add_fuel_charge(request, service_id):
    service = get_object_or_404(Apply, id=service_id)

    if request.method == 'POST':
        technician_name = request.user.username  # Get technician's username
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        kilometers = request.POST.get('kilometers')
        cost = request.POST.get('cost')

        # Create a FuelCharge instance and associate it with the Apply instance
        fuel_charge = FuelCharge.objects.create(
            technician_name=technician_name,
            date=date,
            purpose=purpose,
            kilometers=kilometers,
            cost=cost,
            apply=service
        )

        return JsonResponse({'status': 'success', 'message': 'Fuel charge added successfully!'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def update_fuelcharge(request, fuel_id):
    fuel = get_object_or_404(FuelCharge, id=fuel_id)

    if request.method == "POST":
        technician_name = request.POST.get('technician_name')
        date = request.POST.get('date')
        purpose = request.POST.get('purpose')
        kilometers = request.POST.get('kilometers')
        cost = request.POST.get('cost')

        if not all([technician_name, date, purpose, kilometers, cost]):
            messages.error(request, "All fields are required.")
            return redirect('update_fuelcharge', fuel_id=fuel_id)

        try:
            fuel.technician_name = technician_name
            fuel.date = date
            fuel.purpose = purpose
            fuel.kilometers = kilometers
            fuel.cost = cost
            fuel.save()

            messages.success(request, "Fuel charge updated successfully!")
            return redirect('fuelcharge', apply_id=fuel.apply.id)  
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('update_fuelcharge', fuel_id=fuel_id)

    return render(request, 'update_fuelcharge.html', {'fuel': fuel})

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

def food_allowance(request, apply_id):
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
            return render(request, 'update_food_allowance.html', {'food': food})

        try:
            food.technician_name = technician_name
            food.date = date
            food.purpose = purpose
            food.cost = cost
            food.save()

            messages.success(request, "Food allowance updated successfully!")
            return redirect('food_allowance', apply_id=food.apply.id)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'update_food_allowance.html', {'food': food})

    return render(request, 'update_food_allowance.html', {'food': food})

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

def update_item_purchased(request, item_id):
    item = get_object_or_404(ItemPurchased, id=item_id)
    
    if request.method == "POST":
        date = request.POST.get('date')
        item_name = request.POST.get('item_name')
        price = request.POST.get('price')
        bill_photo = request.FILES.get('bill_photo')  
        
        if not all([date, item_name, price]):
            messages.error(request, "All fields except bill photo are required.")
            return render(request, 'update_item_purchased.html', {'item': item})

        try:
            item.date = date
            item.item_name = item_name
            item.price = price

            if bill_photo:
                item.bill_photo = bill_photo

            item.save()
            messages.success(request, "Item purchased updated successfully!")
            return redirect('item_purchased', apply_id=item.apply.id)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'update_item_purchased.html', {'item': item})

    return render(request, 'update_item_purchased.html', {'item': item}) 

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
        date = request.POST.get('date')
        vendor_name = request.POST.get('vendor_name')
        vendor_bill_photo = request.FILES.get('vendor_bill_photo')
        vendor_eta = request.POST.get('vendor_eta')
        vendor_cost = request.POST.get('vendor_cost')

        if not all([date, vendor_name, vendor_bill_photo, vendor_eta, vendor_cost]):
            messages.error(request, "All fields are required.")
            return redirect('vendorinfo', apply_id=apply_id)

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
            return render(request, 'update_vendor_info.html', {'vendor': vendor})

        try:
            vendor.date = date
            vendor.vendor_name = vendor_name
            vendor.vendor_eta = vendor_eta
            vendor.vendor_cost = vendor_cost

            if vendor_bill_photo:
                vendor.vendor_bill_photo = vendor_bill_photo

            vendor.save()
            messages.success(request, "Vendor info updated successfully!")
            return redirect('vendor_info', apply_id=vendor.apply.id)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return render(request, 'update_vendor_info.html', {'vendor': vendor})

    return render(request, 'update_vendor_info.html', {'vendor': vendor})

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

# def current_status(request, apply_id):
#     apply_instance = get_object_or_404(Apply, id=apply_id)

#     technician_name = request.user.get_full_name() or request.user.username

#     if request.method == "POST":
#         date = request.POST.get('date')
#         technician_name = request.POST.get('technician_name', technician_name)
#         status = request.POST.get('status')

#         if not all([date, technician_name, status]):
#             messages.error(request, "All fields are required.")
#             return redirect('current_status', apply_id=apply_id)

#         try:
#             customer_name = apply_instance.name
#             issue = apply_instance.issue

#             CurrentStatus.objects.create(
#                 apply=apply_instance,
#                 date=date,
#                 technician_name=technician_name,
#                 status=status,
#                 customer_name=customer_name,
#                 issue=issue,
#             )
#             messages.success(request, "Current status successfully added!")
#         except Exception as e:
#             messages.error(request, f"Error: {str(e)}")
#             return redirect('current_status', apply_id=apply_id)

#         return redirect('current_status', apply_id=apply_id)

#     status = CurrentStatus.objects.filter(apply=apply_instance)
#     context = {
#         'apply': apply_instance,
#         'status': status,
#         'technician_name': technician_name,
#     }
#     return render(request, 'current_status.html', context)


    
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