from django.shortcuts import render,redirect,get_object_or_404
from velvetekapp.models import Apply,Customer
from loginapp.models import CustomUser
from django.contrib import messages
from .models import Apply,FuelCharge,FoodAllowance,ItemPurchased,VendorInfo,CurrentStatus


# Create your views here.
def technician_add_service(request):
    details = None
    users = CustomUser.objects.all()

    # Handle GET request
    if 'contact_number' in request.GET:
        contact_number = request.GET.get('contact_number', '').strip()
        try:
            details = Customer.objects.get(contact_number=contact_number)
        except Customer.DoesNotExist:
            messages.error(request, "No customer found with this contact number.")
            return redirect('technician_add_service')

    # Handle POST request
    if request.method == "POST":
        contact_number = request.POST.get('contact_number')
        work_type = request.POST.get('work_type')
        item_name_or_number = request.POST.get('item_name_or_number')
        issue = request.POST.get('issue', '')
        photos_of_item = request.FILES.get('photos_of_item')
        estimation_document = request.FILES.get('estimation_document')
        estimated_price = request.POST.get('estimated_price', '')
        estimated_date = request.POST.get('estimated_date', '')
        any_other_comments = request.POST.get('any_other_comments', '')
        service_by_id = request.POST.get('service_by')

        if not contact_number or not work_type or not item_name_or_number:
            messages.error(request, "Please fill in all required fields.")
            return redirect('technician_add_service')

        try:
            customer = get_object_or_404(Customer, contact_number=contact_number)
            service_by_user = get_object_or_404(CustomUser, id=service_by_id)

            Apply.objects.create(
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
            messages.success(request, "Application submitted successfully!")
            return redirect('technician_add_service')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    context = {
        'details': details,
        'users': users,
    }
    return render(request, 'technician_add_service.html', context)

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

def current_status(request, apply_id):
    apply_instance = get_object_or_404(Apply, id=apply_id)

    technician_name = request.user.get_full_name() or request.user.username

    if request.method == "POST":
        date = request.POST.get('date')
        technician_name = request.POST.get('technician_name', technician_name)
        status = request.POST.get('status')

        if not all([date, technician_name, status]):
            messages.error(request, "All fields are required.")
            return redirect('current_status', apply_id=apply_id)

        try:
            customer_name = apply_instance.name
            issue = apply_instance.issue

            CurrentStatus.objects.create(
                apply=apply_instance,
                date=date,
                technician_name=technician_name,
                status=status,
                customer_name=customer_name,
                issue=issue,
            )
            messages.success(request, "Current status successfully added!")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('current_status', apply_id=apply_id)

        return redirect('current_status', apply_id=apply_id)

    status = CurrentStatus.objects.filter(apply=apply_instance)
    context = {
        'apply': apply_instance,
        'status': status,
        'technician_name': technician_name,
    }
    return render(request, 'current_status.html', context)

def update_current_status(request, status_id):
    status = get_object_or_404(CurrentStatus, id=status_id)

    if request.method == "POST":
        status.date = request.POST.get('date')
        status.technician_name = request.POST.get('technician_name')
        status.status = request.POST.get('status')
        status.save()

        return redirect('current_status', apply_id=status.apply.id)

    return render(request, 'update_current_status.html', {'status': status})

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

    return render(request, 'pending_task.html', {
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