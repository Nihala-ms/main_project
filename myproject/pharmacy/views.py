import json
from django.utils import timezone
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Medicine, CartItems,User,Brand,Orders,OrderItem,Cart,Products
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from decimal import Decimal
import razorpay
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
import os
import random
from datetime import datetime
import json
import logging
from django.conf import settings
from django.shortcuts import render, redirect, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.db import transaction
import logging


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def pharmacy(request):
    # Get trending products (you can define your own logic for what's trending)
    trending_products = Products.objects.filter(is_trending=True)[:8]  # Example: get 8 trending products
    popular_medicines = Medicine.objects.order_by('?')[:6]  # Get 6 random medicines

    context = {
        'trending_products': trending_products,
        'popular_medicines':popular_medicines
    }
    return render(request, "pharmacy.html", context)

def product_detail(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    
    # Handle add to cart POST request
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please login to add items to your cart.")
            return redirect('pharmacy_auth')  # or your login URL
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItems.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 1}
        )
        
        if not created:
            if product.stock > cart_item.quantity:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Added another {product.name} to your cart.")
            else:
                messages.error(request, f"Cannot add more {product.name} - only {product.stock} available.")
        else:
            messages.success(request, f"{product.name} added to your cart.")
        
        return redirect('product_detail', product_id=product.id)
    
    # Get related products (excluding current product)
    related_products = Products.objects.filter(
        category=product.category
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products
    }
    return render(request, 'product_detail.html', context)

from django.shortcuts import render
from .models import Products

def product_list(request):
    # Get all products that are marked as trending
    trending_products = Products.objects.filter(is_trending=True)
    
    # Get all other products (non-trending)
    products = Products.objects.filter(is_trending=False)
    
    # For testing, if you want to see all products regardless of trending status:
    # all_products = Products.objects.all()
    
    # Get cart items count if user is authenticated
   
    
    context = {
        'trending_products': trending_products,
        'products': products,
    }
    return render(request, 'beauty_section.html', context)

def order_medicine(request):
    medicines = Medicine.objects.all()
    return render(request, 'order_medicine.html', {'medicines': medicines})

def detailed(request, id):
    medicine = get_object_or_404(Medicine, id=id)
    all_medicines = Medicine.objects.exclude(id=medicine.id)

    # Get similar medicines from the same brand and category
    similar_medicines = random.sample(list(all_medicines), min(4, all_medicines.count()))
    
    return render(request, 'detailed.html', {
        'medicine': medicine,
        'similar_medicines': similar_medicines
    })

def search_medicine(request):
    query = request.GET.get('q', '')  # Get the search query from the request
    results = []

    if query:
        results = Medicine.objects.filter(name__icontains=query)  # Case-insensitive search

    return render(request, 'search_results.html', {'results': results, 'query': query})

def beauty_section(request):
    return render(request, 'beauty_section.html')

def beauty(request):
    return render(request, 'beauty.html')


def sign(request):
    return render(request,"pharmacysign.html")
  # Ensure you're using the correct User model


def pharmacy_auth(request):
    # Get the next parameter from the URL, or default to '/pharmacy/cart/'
    next_url = request.GET.get('next', '/pharmacy/cart/')
    
    if request.method == 'POST':
        action = request.POST.get('action')

        # --------------------------------
        # SIGN UP LOGIC
        # --------------------------------
        if action == 'sign_up':
            name = request.POST.get('name').strip()
            email = request.POST.get('email').strip()
            password = request.POST.get('password').strip()

            if not name or not email or not password:
                messages.error(request, 'All fields are required.')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
            else:
                try:
                    user = User.objects.create(
                        name=name,
                        email=email,
                        password=make_password(password),  # Hash password at creation
                    )
                    messages.success(request, 'Account created successfully. Please log in.')
                except Exception as e:
                    messages.error(request, f'Error: {str(e)}')

            return redirect('pharmacy_auth')

        # --------------------------------
        # SIGN IN LOGIC
        # --------------------------------
        elif action == 'sign_in':
            email = request.POST.get('email').strip()
            password = request.POST.get('password').strip()

            if not email or not password:
                messages.error(request, 'Both email and password are required.')
            else:
                try:
                    user = User.objects.get(email=email)
                    if check_password(password, user.password):
                        request.session['user_id'] = user.id  # Store user ID in session
                        messages.success(request, f'Welcome, {user.name}!')

                        # Validate the next URL to prevent open redirects
                        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                            return HttpResponseRedirect(next_url)  # Use HttpResponseRedirect
                        else:
                            return redirect('view_cart')  # Default redirect if `next` is invalid or missing

                    else:
                        messages.error(request, 'Invalid email or password.')
                except User.DoesNotExist:
                    messages.error(request, 'Invalid email or password.')

            return redirect('pharmacy_auth')

    return render(request, 'pharmacysign.html')
def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('pharmacy')


def order_summary(request):
    # Fetch cart items and calculate total price (dummy data used for now)
    cart_items = [
        {"product_name": "Paracetamol", "quantity": 8, "price": 160.00},
    ]
    total_price = sum(item['price'] for item in cart_items)

    return render(request, 'checkout.html', {"cart_items": cart_items, "total_price": total_price})

logger = logging.getLogger(__name__)
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def calculate_cart_totals(cart_items):
    subtotal = Decimal('0')
    for item in cart_items:
        if item.medicine:
            price = item.medicine.effective_price
        elif item.product:
            price = item.product.discount_price or item.product.price
        subtotal += Decimal(price) * Decimal(item.quantity)
    
    delivery_fee = Decimal('0') if subtotal > Decimal('500') else Decimal('50')
    tax_rate = Decimal('2.5')  # 2.5% tax
    tax_amount = subtotal * tax_rate / Decimal('100')
    total = subtotal + delivery_fee + tax_amount
    
    return {
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'total': total
    }

from django.conf import settings
import razorpay
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
import logging

logger = logging.getLogger(__name__)
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def checkout(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.warning(request, "Please login to proceed to checkout")
        return redirect('pharmacy_auth')

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)
        cart_items = CartItems.objects.filter(cart=cart).select_related('medicine', 'product')
        
        if not cart_items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect('view_cart')

        cart_data = calculate_cart_totals(cart_items)
        
        if request.method == "POST":
            form_data = {
                'first_name': request.POST.get("firstName", "").strip(),
                'last_name': request.POST.get("lastName", "").strip(),
                'email': request.POST.get("email", "").strip(),
                'phone': request.POST.get("phone", "").strip(),
                'address': request.POST.get("address", "").strip(),
                'address2': request.POST.get("address2", "").strip(),
                'city': request.POST.get("city", "").strip(),
                'state': request.POST.get("state", "").strip(),
                'zip_code': request.POST.get("zip", "").strip(),
                'country': request.POST.get("country", "").strip(),
            }

            required_fields = ['first_name', 'last_name', 'email', 'phone', 
                             'address', 'city', 'state', 'zip_code', 'country']
            
            if not all(form_data[field] for field in required_fields):
                return JsonResponse({
                    'success': False,
                    'error': 'Please fill in all required fields'
                }, status=400)

            try:
                with transaction.atomic():
                    # Create order with temporary number
                    order = Orders.objects.create(
                        user=user,
                        **form_data,
                        subtotal=cart_data['subtotal'],
                        delivery_fee=cart_data['delivery_fee'],
                        tax=cart_data['tax_amount'],
                        total=cart_data['total'],
                        status='pending',
                        order_number=''  # Will be generated in save()
                    )
                    
                    # Create order items
                    for item in cart_items:
                        if item.medicine:
                            OrderItem.objects.create(
                                order=order,
                                medicine=item.medicine,
                                quantity=item.quantity,
                                price=item.medicine.price
                            )
                            # Update stock
                            item.medicine.stock -= item.quantity
                            item.medicine.save()
                        elif item.product:
                            OrderItem.objects.create(
                                order=order,
                                product=item.product,
                                quantity=item.quantity,
                                price=item.product.discount_price or item.product.price
                            )
                            # Update stock
                            item.product.stock -= item.quantity
                            item.product.save()
                    
                    # Create Razorpay order with user_id in notes
                    amount = int(float(cart_data['total']) * 100)  # Convert to paise
                    razorpay_order = client.order.create({
                        'amount': amount,
                        'currency': 'INR',
                        'payment_capture': '1',
                        'notes': {
                            'order_id': str(order.id),
                            'user_id': str(user.id)  # Critical - include user_id
                        }
                    })
                    
                    # Update order with Razorpay ID
                    order.razorpay_order_id = razorpay_order['id']
                    order.save()
                    
                    return JsonResponse({
                        'success': True,
                        'order_id': str(order.id),
                        'razorpay_order_id': razorpay_order['id'],
                        'amount': amount,
                        'currency': 'INR',
                        'key': settings.RAZORPAY_KEY_ID,
                        'name': "Your Pharmacy",
                        'description': f"Order #{order.id}",
                        'prefill': {
                            'name': f"{form_data['first_name']} {form_data['last_name']}",
                            'email': form_data['email'],
                            'contact': form_data['phone']
                        },
                        'notes': {
                            'address': form_data['address'],
                            'order_id': str(order.id),
                            'user_id': str(user.id)  # Also include in response
                        },
                        'theme': {
                            'color': "#1a237e"
                        }
                    })

            except Exception as e:
                logger.error(f"Order processing failed: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': "Order processing failed. Please try again."
                }, status=500)

        return render(request, "checkout.html", {
            'cart_items': cart_items,
            'cart': cart_data,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'user': user  # Pass user to template
        })

    except (User.DoesNotExist, Cart.DoesNotExist) as e:
        messages.error(request, str(e))
        return redirect('pharmacy')
    
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

def payment_callback(request):
    if request.method == 'POST':
        try:
            # Get all parameters from the request
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            # Get the order details from Razorpay
            razorpay_order = client.order.fetch(razorpay_order_id)
            order_id = razorpay_order['notes']['order_id']
            user_id = razorpay_order['notes']['user_id']  # Get user_id from notes
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            client.utility.verify_payment_signature(params_dict)
            
            # Update order status
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                order = Orders.objects.get(
                    id=order_id,
                    razorpay_order_id=razorpay_order_id,
                    user=user,  # Ensure order belongs to this user
                    status='pending'
                )
                
                # Update order details
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = razorpay_signature
                order.status = 'paid'
                order.save()
                
                # Clear the user's cart
                CartItems.objects.filter(cart__user=user).delete()
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('order_success', kwargs={'order_id': order.id})
                })
                
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return JsonResponse({
                'success': False,
                'error': 'User not found'
            }, status=404)
        except Orders.DoesNotExist:
            logger.error(f"Order not found: {order_id} for user {user_id}")
            return JsonResponse({
                'success': False,
                'error': 'Order not found'
            }, status=404)
        except razorpay.errors.SignatureVerificationError:
            logger.error("Invalid payment signature")
            return JsonResponse({
                'success': False,
                'error': 'Invalid payment signature'
            }, status=400)
        except Exception as e:
            logger.error(f"Payment callback error: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Payment processing failed'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)
    
def order_success(request, order_id):
    try:
        order = Orders.objects.get(id=order_id)
        return render(request, 'order_success.html', {'order': order})
    except Orders.DoesNotExist:
        messages.error(request, "Order not found")
        return redirect('pharmacy')

def order_payment_failed(request, order_id):
    if request.method == 'POST':
        try:
            order = Orders.objects.get(id=order_id)
            order.status = 'Failed'
            order.save()
            return JsonResponse({'success': True})
        except Orders.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
        except Exception as e:
            logger.error(f"Payment failed update error: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'Update failed'}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


def payment_success(request):
    if request.method == 'POST':
        try:
            # Verify payment signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            params = {
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }
            
            client.utility.verify_payment_signature(params)
            
            # Get the order from the Razorpay order ID
            order = Orders.objects.get(razorpay_order_id=params['razorpay_order_id'])
            order.status = 'completed'
            order.razorpay_payment_id = params['razorpay_payment_id']
            order.save()
            
            # Clear cart
            CartItems.objects.filter(cart=order.user.cart).delete()
            
            return render(request, 'payment_success.html', {'order': order})
            
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return redirect('payment_failed')
    
    return redirect('pharmacy')







def add_to_cart(request, item_id, item_type):
    # Get user_id from session
    user_id = request.session.get('user_id')
    
    # Redirect to login if not logged in with proper next URL
    if not user_id:
        messages.info(request, "Please login to add items to your cart")
        # Store the intended destination URL in session
        request.session['next_url'] = request.get_full_path()
        return redirect('pharmacy_auth')
    
    try:
        user = get_object_or_404(User, id=user_id)
        cart, _ = Cart.objects.get_or_create(user=user)
        
        # Handle quantity from form (default to 1 if not provided)
        quantity = int(request.POST.get('quantity', 1))
        
        if item_type == 'medicine':
            item = get_object_or_404(Medicine, id=item_id)
            item_field = 'medicine'
        elif item_type == 'product':
            item = get_object_or_404(Products, id=item_id)
            item_field = 'product'
        else:
            messages.error(request, "Invalid item type")
            return redirect('view_cart')
        
        # Check stock availability
        if item.stock < quantity:
            messages.error(request, f"Not enough stock available for {item.name}")
            return redirect(request.META.get('HTTP_REFERER', 'view_cart'))
        
        # Create filter kwargs based on item type
        filter_kwargs = {
            'cart': cart,
            item_field: item
        }
        
        # Get or create cart item
        cart_item, created = CartItems.objects.get_or_create(
            **filter_kwargs,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity if item already exists
            if item.stock >= (cart_item.quantity + quantity):
                cart_item.quantity += quantity
                cart_item.save()
                messages.success(request, f"Added {quantity} more {item.name} to your cart")
            else:
                messages.error(request, f"Cannot add more {item.name} - insufficient stock")
        else:
            messages.success(request, f"{quantity} {item.name} added to your cart")
            
    except Exception as e:
        messages.error(request, f"Error adding item to cart: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'view_cart'))
    
    # Redirect to view_cart after successful addition
    return redirect('view_cart')


def view_cart(request):
    user_id = request.session.get('user_id')

    if not user_id:  # Redirect to login if not logged in
        messages.error(request, "Please login to view your cart")
        return redirect(f"/pharmacy/pharmacy_auth/?next={request.get_full_path()}")

    try:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.get(user=user)
        cart_items = CartItems.objects.filter(cart=cart).select_related('medicine', 'product')
        
        total_price = 0
        requires_prescription_upload = False
        
        for item in cart_items:
            if item.medicine:
                total_price += item.medicine.price * item.quantity
                if item.medicine.prescription_required and not item.prescription:
                    requires_prescription_upload = True
            elif item.product:
                price = item.product.discount_price if item.product.discount_price else item.product.price
                total_price += price * item.quantity
        
        total_items = sum(item.quantity for item in cart_items)

        context = {
            'cart': cart,
            'cart_items': cart_items,
            'total_price': total_price,
            'total_items': total_items,
            'requires_prescription_upload': requires_prescription_upload,
            'user': user
        }
        return render(request, 'cart.html', context)

    except User.DoesNotExist:
        messages.error(request, "User not found. Please log in again.")
        return redirect('pharmacy_auth')
    except Cart.DoesNotExist:
        user = User.objects.get(id=user_id)
        cart = Cart.objects.create(user=user)
        return render(request, 'cart.html', {
            'cart': cart,
            'cart_items': [],
            'total_price': 0,
            'total_items': 0,
            'requires_prescription_upload': False,
            'user': user
        })

def calculate_cart_totals(cart_items):
    subtotal = Decimal('0.00')
    
    for item in cart_items:
        if item.medicine:
            price = Decimal(str(item.medicine.price))
        else:
            price = Decimal(str(item.product.discount_price if item.product.discount_price 
                            else item.product.price))
        subtotal += price * item.quantity
    
    delivery_fee = Decimal('30.00')  # Fixed delivery fee
    tax_rate = Decimal('0.025')      # 10% tax
    tax_amount = subtotal * tax_rate
    total = subtotal + delivery_fee + tax_amount
    
    return {
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'tax_rate': tax_rate * 100,  # For display as percentage
        'tax_amount': tax_amount,
        'total': total,
        'item_count': sum(item.quantity for item in cart_items)
    }



def upload_prescription(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({
            'success': False,
            'error': 'Please login to upload prescription',
            'login_required': True
        }, status=401)
    
    try:
        user = get_object_or_404(User, id=user_id)
        cart = Cart.objects.get(user=user)
        item_id = request.POST.get('item_id')
        prescription_file = request.FILES.get('prescription')
        
        if not prescription_file:
            return JsonResponse({
                'success': False,
                'error': 'No prescription file provided'
            }, status=400)
            
        cart_item = CartItems.objects.get(id=item_id, cart=cart)
        
        # Delete old prescription if exists
        if cart_item.prescription:
            old_path = os.path.join(settings.MEDIA_ROOT, str(cart_item.prescription))
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new prescription
        file_ext = os.path.splitext(prescription_file.name)[1]
        filename = f"prescriptions/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        file_path = default_storage.save(filename, prescription_file)
        
        cart_item.prescription = file_path
        cart_item.save()
        
        # Check if all prescription-required items have prescriptions
        all_uploaded = True
        prescription_required_items = CartItems.objects.filter(
            cart=cart,
            medicine__prescription_required=True
        )
        
        for item in prescription_required_items:
            if not item.prescription:
                all_uploaded = False
                break
        
        return JsonResponse({
            'success': True,
            'prescription_url': cart_item.prescription.url if cart_item.prescription else None,
            'all_prescriptions_uploaded': all_uploaded
        })
        
    except CartItems.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Item not found in cart'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def update_cart(request, item_id, action):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({
            'success': False,
            'error': 'Please login to update cart',
            'login_required': True
        }, status=401)
    
    try:
        user = get_object_or_404(User, id=user_id)
        cart = Cart.objects.get(user=user)
        cart_item = CartItems.objects.get(id=item_id, cart=cart)
        
        if action == 'increase':
            item = cart_item.medicine if cart_item.medicine else cart_item.product
            if item.stock <= cart_item.quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {item.stock} available in stock',
                    'max_quantity': item.stock
                })
            cart_item.quantity += 1
        elif action == 'decrease':
            if cart_item.quantity <= 1:
                return JsonResponse({
                    'success': False,
                    'error': 'Quantity cannot be less than 1'
                })
            cart_item.quantity -= 1
        
        cart_item.save()
        
        # Calculate item price
        if cart_item.medicine:
            item_price = cart_item.medicine.price * cart_item.quantity
        else:
            price = cart_item.product.discount_price if cart_item.product.discount_price else cart_item.product.price
            item_price = price * cart_item.quantity
        
        # Calculate totals and check prescription requirements
        cart_items = CartItems.objects.filter(cart=cart)
        total_price = 0
        total_items = 0
        requires_prescription_upload = False
        
        for item in cart_items:
            if item.medicine:
                total_price += item.medicine.price * item.quantity
                if item.medicine.prescription_required and not item.prescription:
                    requires_prescription_upload = True
            elif item.product:
                price = item.product.discount_price if item.product.discount_price else item.product.price
                total_price += price * item.quantity
            total_items += item.quantity
        
        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_price': item_price,
            'total_price': total_price,
            'total_items': total_items,
            'requires_prescription_upload': requires_prescription_upload,
            'is_empty': len(cart_items) == 0
        })
        
    except CartItems.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Item not found in cart'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def remove_from_cart(request, item_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({
            'success': False,
            'error': 'Please login to update cart',
            'login_required': True
        }, status=401)
    
    try:
        user = get_object_or_404(User, id=user_id)
        cart = Cart.objects.get(user=user)
        cart_item = CartItems.objects.get(id=item_id, cart=cart)
        
        # Delete prescription file if exists
        if cart_item.prescription:
            file_path = os.path.join(settings.MEDIA_ROOT, str(cart_item.prescription))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        cart_item.delete()
        
        # Calculate totals and check prescription requirements
        cart_items = CartItems.objects.filter(cart=cart)
        total_price = 0
        total_items = 0
        requires_prescription_upload = False
        
        for item in cart_items:
            if item.medicine:
                total_price += item.medicine.price * item.quantity
                if item.medicine.prescription_required and not item.prescription:
                    requires_prescription_upload = True
            elif item.product:
                price = item.product.discount_price if item.product.discount_price else item.product.price
                total_price += price * item.quantity
            total_items += item.quantity
        
        return JsonResponse({
            'success': True,
            'total_price': total_price,
            'total_items': total_items,
            'requires_prescription_upload': requires_prescription_upload,
            'is_empty': len(cart_items) == 0
        })
        
    except CartItems.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Item not found in cart'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

    
