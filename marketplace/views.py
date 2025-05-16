from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from .models import Product, CartItem, Cart, Order, Category, Review
from python_daraja import payment
from django.conf import settings
from django.shortcuts import render, redirect
from django.db.models import Q
from .forms import CustomUserCreationForm, UpdateProfileForm, UpdatePasswordForm, ProductForm
import logging

logger = logging.getLogger(__name__)

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
            
    product_reviews = {p.id: p.reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating'] or 0.0 for p in products}
    for product in products:
        product.rating = product_reviews.get(product.id, 0.0)
    return render(request, 'marketplace/home.html', {
        'products': products,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'categories': categories,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'marketplace/product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('marketplace:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'marketplace/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('marketplace:home')
    return render(request, 'marketplace/login.html')

def logout_view(request):
    logout(request)
    return redirect('marketplace:home')

def profile(request):
    return render(request, 'marketplace/profile.html', {'user': request.user})

def update_profile(request):
    if request.method == 'POST':
        profile_form = UpdateProfileForm(request.POST, instance=request.user)
        password_form = UpdatePasswordForm(user=request.user, data=request.POST)
        if profile_form.is_valid():
            profile_form.save()
        if password_form.is_valid():
            password_form.save()
            login(request, request.user)
        return redirect('marketplace:profile')
    else:
        profile_form = UpdateProfileForm(instance=request.user)
        password_form = UpdatePasswordForm(user=request.user)
    return render(request, 'marketplace/update_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })

def cart(request):
    if request.user.is_authenticated:
        cart_items = request.user.cartitem_set.all()
        return render(request, 'marketplace/cart.html', {'cart_items': cart_items})
    return redirect('marketplace:login')

@login_required
@csrf_exempt
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        cart_count = CartItem.objects.filter(cart=cart).count()
        cart_total = sum(item.product.price * item.quantity for item in CartItem.objects.filter(cart=cart))
        return JsonResponse({'success': True, 'cart_count': cart_count, 'cart_total': cart_total})
    return JsonResponse({'success': False})

@login_required
def initiate_payment(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('marketplace:cart')
    order = Order.objects.get(id=order_id, user=request.user)
    phone_number = '2547XXXXXXXXX'  # Replace with user's phone number (get from user profile in production)
    amount = int(order.total_price)  # M-Pesa API expects amount as an integer
    transaction_desc = f'Payment for Order {order.id}'
    callback_url = 'https://yourdomain.com/mpesa/callback/'  # Update with your ngrok URL
    try:
        response = payment.trigger_stk_push(
            phone_number=phone_number,
            amount=amount,
            #account_reference=f'ORDER{order.id}',
            # transaction_desc=transaction_desc,
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

def seller_dashboard(request):
    if not request.user.is_seller:
        return redirect('marketplace:home')
    products = Product.objects.filter(seller=request.user)
    return render(request, 'marketplace/seller_dashboard.html', {'products': products})

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

    cart_items_with_subtotal = [
        {'item': item, 'subtotal': item.product.price * item.quantity}
        for item in cart_items
    ]
    cart_total = sum(item['subtotal'] for item in cart_items_with_subtotal) if cart_items else 0
    return render(request, 'marketplace/cart.html', {
        'cart_items_with_subtotal': cart_items_with_subtotal,
        'cart_total': cart_total,
    })
    
@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not CartItem.objects.filter(cart=cart).exists():
        return redirect('marketplace:cart')
    cart_items = CartItem.objects.filter(cart=cart)
    cart_items_with_subtotal = [
        {'item': item, 'subtotal': item.product.price * item.quantity}
        for item in cart_items
    ]
    cart_total = sum(item['subtotal'] for item in cart_items_with_subtotal)
    if request.method == 'POST':
        # Create the order but don't finalize until payment is confirmed
        order = Order.objects.create(
            user=request.user,
            total_price=cart_total
        )
        # Store order ID in session for payment processing
        request.session['order_id'] = order.id
        return redirect('marketplace:initiate_payment')
    return render(request, 'marketplace/checkout.html', {
        'cart_items_with_subtotal': cart_items_with_subtotal,
        'cart_total': cart_total,
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
        data = request.POST if request.POST else request.json
        theme = data.get('theme', 'light')
        request.session['theme'] = theme
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
@csrf_exempt
def add_review(request, product_id):
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        rating = float(request.POST.get('rating', 0.0))
        comment = request.POST.get('comment', '')
        if 0 <= rating <= 5:
            Review.objects.create(product=product, user=request.user, rating=rating, comment=comment)
            # Update product average rating
            avg_rating = product.reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.0
            product.rating = avg_rating
            product.save()
        return JsonResponse({'success': True, 'message': 'Review added!'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})