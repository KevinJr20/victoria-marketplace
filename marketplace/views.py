from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models, IntegrityError
from django.http import JsonResponse
from .models import Product, CartItem, Cart, Order, Category, Review
from python_daraja import payment
from django.conf import settings
from django.db.models import Avg
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ProductForm, UserRegistrationForm, UpdateProfileForm, UpdatePasswordForm
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging
import json
import stripe
import paypalrestsdk

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})

def home(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    cart_items = []
    cart_total = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)
            cart_total = sum(item.product.price * item.quantity for item in cart_items)
    product_reviews = {p.id: p.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0.0 for p in products}
    for product in products:
        rating = product_reviews.get(product.id, 0.0)
        product.rating = rating
        product.full_stars = int(rating)
        product.has_half_star = (rating - product.full_stars) >= 0.5
        product.rating_display = rating
    return render(request, 'marketplace/home.html', {
        'products': products,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'categories': categories,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = Review.objects.filter(product=product)
    cart_items = []
    cart_total = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)
            cart_total = sum(item.product.price * item.quantity for item in cart_items)
    rating = float(product.rating) if product.rating else 0.0
    full_stars = int(rating)
    has_half_star = (rating - full_stars) >= 0.5
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'user_review': None if not request.user.is_authenticated else reviews.filter(user=request.user).first(),
        'full_stars': full_stars,
        'has_half_star': has_half_star,
        'rating': rating,
    })

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('marketplace:home')
    else:
        form = UserRegistrationForm()
    return render(request, 'marketplace/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                # Check for 'next' parameter to redirect to the intended page
                next_url = request.GET.get('next', 'marketplace:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('marketplace:home')

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user)
    reviews = Review.objects.filter(user=request.user)
    cart_items = []
    cart_total = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)
            cart_total = sum(item.product.price * item.quantity for item in cart_items)

    # Precompute star variables for each review
    for review in reviews:
        rating = float(review.rating) if review.rating else 0.0
        review.full_stars = int(rating)
        review.has_half_star = (rating - review.full_stars) >= 0.5
        review.rating_display = rating

    # Handle missing Profile
    try:
        user_profile = request.user.profile
    except Profile.DoesNotExist:
        user_profile = None

    return render(request, 'marketplace/profile.html', {
        'orders': orders,
        'reviews': reviews,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'profile': user_profile, 
        'user': request.user
    })

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def update_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        if profile:
            profile_form = UpdateProfileForm(request.POST, instance=profile)
        else:
            profile_form = UpdateProfileForm(request.POST)
        password_form = UpdatePasswordForm(user=request.user, data=request.POST)
        if profile_form.is_valid() and password_form.is_valid():
            profile_instance = profile_form.save(commit=False)
            if not profile:  # Create Profile if it doesn't exist
                profile_instance.user = request.user
            profile_instance.save()
            password_form.save()
            login(request, request.user)  # Optional, refresh session
            return redirect('marketplace:profile')
    else:
        # If profile exists, pass it as instance; otherwise, initialize form without instance
        if profile:
            profile_form = UpdateProfileForm(instance=profile)
        else:
            profile_form = UpdateProfileForm()
        password_form = UpdatePasswordForm(user=request.user)
    return render(request, 'marketplace/update_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            # Delete any existing carts for the user to ensure only one active cart
            Cart.objects.filter(user=request.user).delete()
            cart, created = Cart.objects.get_or_create(user=request.user)
            logger.info(f"Cart created/updated for user {request.user.username}: {cart.id}")
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                cart_item.quantity += 1
                cart_item.save()
                logger.info(f"Cart item {cart_item.id} quantity updated to {cart_item.quantity}")
            else:
                logger.info(f"New cart item {cart_item.id} created for product {product.id}")
            cart_count = CartItem.objects.filter(cart=cart).count()
            cart_total = sum(item.product.price * item.quantity for item in CartItem.objects.filter(cart=cart))
            return JsonResponse({'success': True, 'cart_count': cart_count, 'cart_total': cart_total})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})
        except Exception as e:
            logger.error(f"Error adding to cart: {str(e)}")
            return JsonResponse({'success': False, 'message': 'An error occurred'})
    return JsonResponse({'success': False})

@login_required
def initiate_payment(request):
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, 'No order found.')
        return redirect('marketplace:cart')
    order = Order.objects.get(id=order_id, user=request.user)
    phone_number = '2547XXXXXXXXX'  # Replace with user's phone number
    amount = int(order.total_price)
    transaction_desc = f'Payment for Order {order.id}'
    callback_url = 'https://yourdomain.com/mpesa/callback/'
    try:
        response = payment.trigger_stk_push(
            phone_number=phone_number,
            amount=amount,
            callback_url=callback_url
        )
        logger.info(f"M-Pesa STK Push response: {response}")
        return render(request, 'marketplace/payment_pending.html', {'order': order})
    except Exception as e:
        logger.error(f"M-Pesa payment initiation failed: {str(e)}")
        return render(request, 'marketplace/payment_failed.html', {'error': str(e)})

@login_required
def order_confirmation(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'marketplace/order_confirmation.html', {
        'order': order,
    })

@login_required
def seller_dashboard(request):
    if not request.user.is_seller:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('marketplace:home')
    
    products = Product.objects.filter(seller=request.user)
    
    # Sales Trends Data (Using CartItem and Order)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    sales_data = CartItem.objects.filter(
        product__seller=request.user,
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values('order__created_at__date').annotate(
        total_sales=Sum(
            ExpressionWrapper(
                F('product__price') * F('quantity'),
                output_field=fields.DecimalField(max_digits=10, decimal_places=2)
            )
        )
    ).order_by('order__created_at__date')
    
    sales_dates = []
    sales_values = []
    current_date = start_date
    while current_date <= end_date:
        sales_dates.append(current_date.strftime('%Y-%m-%d'))
        sales_values.append(0)
        current_date += timedelta(days=1)
    
    for sale in sales_data:
        date_index = (sale['order__created_at__date'] - start_date).days
        sales_values[date_index] = float(sale['total_sales'] or 0)
    
    sales_chart_data = {
        'labels': sales_dates,
        'data': sales_values,
    }
    
    # Product Performance Data
    product_sales = CartItem.objects.filter(
        product__seller=request.user
    ).values('product__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('product__name')
    
    product_names = [item['product__name'] for item in product_sales]
    quantities = [item['total_quantity'] or 0 for item in product_sales]
    
    product_chart_data = {
        'labels': product_names,
        'data': quantities,
    }
    
    # Key Metrics
    total_sales = CartItem.objects.filter(
        product__seller=request.user
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('product__price') * F('quantity'),
                output_field=fields.DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )['total'] or 0
    
    total_orders = Order.objects.filter(
        cart_items__product__seller=request.user
    ).distinct().count()
    
    avg_order_value = Order.objects.filter(
        cart_items__product__seller=request.user
    ).distinct().aggregate(avg=Avg('total_price'))['avg'] or 0
    
    key_metrics = {
        'total_sales': float(total_sales),
        'total_orders': total_orders,
        'avg_order_value': float(avg_order_value),
    }
    
    # Recent Orders
    recent_orders = Order.objects.filter(
        cart_items__product__seller=request.user
    ).select_related('user').order_by('-created_at')[:5]
    
    # Products Overview
    total_products = products.count()
    out_of_stock = products.filter(stock=0).count()  # Note: stock field is missing in Product model
    top_product = product_sales.order_by('-total_quantity').first() if product_sales else None
    top_product_name = top_product['product__name'] if top_product else 'N/A'
    
    products_overview = {
        'total_products': total_products,
        'out_of_stock': out_of_stock,
        'top_product_name': top_product_name,
    }
    
    return render(request, 'marketplace/seller_dashboard.html', {
        'products': products,
        'sales_chart_data': sales_chart_data,
        'product_chart_data': product_chart_data,
        'key_metrics': key_metrics,
        'recent_orders': recent_orders,
        'products_overview': products_overview,
    })

def add_product(request):
    if not request.user.is_seller:
        return redirect('marketplace:home')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            return redirect('marketplace:seller_dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/add_product.html', {'form': form})

def edit_product(request, product_id):
    if not request.user.is_seller:
        return redirect('marketplace:home')
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('marketplace:seller_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'marketplace/edit_product.html', {'form': form, 'product': product})

def delete_product(request, product_id):
    if not request.user.is_seller:
        return redirect('marketplace:home')
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    if request.method == 'POST':
        product.delete()
        return redirect('marketplace:seller_dashboard')
    return render(request, 'marketplace/delete_product.html', {'product': product})

def order_history(request):
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'marketplace/order_history.html', {'orders': orders})
    return redirect('marketplace:login')

def search_products(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    products = Product.objects.all()

    if query:
        products = products.filter(name__icontains=query)
    if category_id:
        products = products.filter(category_id=category_id)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    categories = Category.objects.all()
    cart_items = []
    cart_total = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)
            cart_total = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'marketplace/home.html', {
        'products': products,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'categories': categories
    })
    
@login_required
def cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = CartItem.objects.filter(cart=cart) if cart else []
    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            if action == 'update':
                quantity = int(request.POST.get('quantity', 1))
                if quantity > 0:
                    cart_item.quantity = quantity
                    cart_item.save()
                else:
                    cart_item.delete()
            elif action == 'delete':
                cart_item.delete()
        except CartItem.DoesNotExist:
            pass
        return redirect('marketplace:cart')
    cart_items_with_subtotal = [{'item': item, 'subtotal': item.product.price * item.quantity} for item in cart_items]
    cart_total = sum(item['subtotal'] for item in cart_items_with_subtotal) if cart_items else 0
    return render(request, 'marketplace/cart.html', {
        'cart_items_with_subtotal': cart_items_with_subtotal,
        'cart_total': cart_total,
    })
    
@login_required
def checkout(request):
    logger.info(f"Checkout accessed by user: {request.user.username}, Session ID: {request.session.session_key}")
    cart = Cart.objects.filter(user=request.user).first()
    logger.info(f"Cart found: {cart}")
    if not cart:
        logger.warning(f"No cart found for user {request.user.username}")
        messages.info(request, 'Your cart is empty.')
        return redirect('marketplace:cart')
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    if not cart_items.exists():
        logger.warning(f"No items found in cart {cart.id} for user {request.user.username}")
        messages.info(request, 'Your cart is empty.')
    cart_items_with_subtotal = [{'item': item, 'subtotal': item.product.price * item.quantity} for item in cart_items]
    cart_total = sum(item['subtotal'] for item in cart_items_with_subtotal) if cart_items else 0
    if request.method == 'POST' and cart_items.exists():
        order = Order.objects.create(user=request.user, total_price=cart_total)
        request.session['order_id'] = order.id
        request.session['cart_items'] = [item.id for item in cart_items]
        return redirect('marketplace:initiate_payment')
    return render(request, 'marketplace/checkout.html', {
        'cart_items_with_subtotal': cart_items_with_subtotal,
        'cart_total': cart_total,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    })
    
@login_required
def order_confirmation(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'marketplace/order_confirmation.html', {
        'order': order,
    })
    
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'marketplace/order_history.html', {
        'orders': orders,
    })
    
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        logger.info(f"M-Pesa callback received: {request.body}")
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'failed'}, status=400)

def search_autocomplete(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(name__icontains=query)[:5]  # Limit to 5 suggestions
        suggestions = [product.name for product in products]
        return JsonResponse({'suggestions': suggestions})
    return JsonResponse({'suggestions': []})

@csrf_exempt
def set_theme(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        theme = data.get('theme')
        if theme in ['light', 'dark']:
            request.session['theme'] = theme
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@csrf_exempt
def add_review(request, product_id):
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        rating = float(request.POST.get('rating', 0.0))
        comment = request.POST.get('comment', '')
        review_id = request.POST.get('review_id')
        if 0 <= rating <= 5:
            if review_id:
                # Update existing review
                try:
                    review = Review.objects.get(id=review_id, product=product, user=request.user)
                    review.rating = rating
                    review.comment = comment
                    review.save()
                    message = 'Review updated!'
                except Review.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Review not found'})
            else:
                # Create new review
                review = Review.objects.create(product=product, user=request.user, rating=rating, comment=comment)
                message = 'Review added!'
            # Update product average rating
            avg_rating = product.reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.0
            product.rating = avg_rating
            product.save()
            return JsonResponse({'success': True, 'message': message})
        return JsonResponse({'success': False, 'message': 'Invalid rating'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def process_card_payment(request):
    if request.method == 'POST':
        amount = int(float(request.POST.get('amount')) * 100)  # Convert KSh to cents
        payment_method_id = request.POST.get('payment_method_id')

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='kes',
                payment_method=payment_method_id,
                confirmation_method='manual',
                confirm=True,
            )
            if payment_intent.status == 'succeeded':
                # Update order status or clear cart here (implement as needed)
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Payment failed.'})
        except stripe.error.StripeError as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request.'})

# PayPal Payment Initiation
def initiate_paypal_payment(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri('{% url "marketplace:paypal_success" %}'),
                "cancel_url": request.build_absolute_uri('{% url "marketplace:paypal_cancel" %}'),
            },
            "transactions": [{
                "amount": {
                    "total": amount,
                    "currency": "KES",
                },
                "description": "Payment for Victoria Marketplace order",
            }],
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            messages.error(request, "PayPal payment initiation failed.")
            return redirect('marketplace:checkout')

    return redirect('marketplace:checkout')

# PayPal Success Callback
def paypal_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        # Clear the cart after successful payment
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                CartItem.objects.filter(cart=cart).delete()
        messages.success(request, 'PayPal payment successful!')
        return redirect('marketplace:payment_success')
    else:
        messages.error(request, 'PayPal payment failed.')
        return redirect('marketplace:checkout')
    
# PayPal Cancel Callback
def paypal_cancel(request):
    messages.error(request, 'PayPal payment cancelled.')
    return redirect('marketplace:checkout')

# Payment Success Page
def payment_success(request):
    # Clear the cart after successful payment
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            CartItem.objects.filter(cart=cart).delete()
    return render(request, 'marketplace/payment_success.html')


@receiver(post_save, sender=Order)
def update_order_total(sender, instance, created, **kwargs):
    if created:
        total = sum(item.product.price * item.quantity for item in instance.cart_items.all())
        instance.total_price = total
        instance.save()