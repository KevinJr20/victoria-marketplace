from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, CartItem, Order, Category
from python_daraja import payment
from django.conf import settings
from django.shortcuts import render, redirect
from django.db.models import Q
from .models import Product, CartItem
from .forms import CustomUserCreationForm, UpdateProfileForm, UpdatePasswordForm, ProductForm

def home(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    
    products = Product.objects.all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_id:
        products = products.filter(category__id=category_id)
    if price_min and price_max:
        products = products.filter(price__gte=price_min, price__lte=price_max)
    
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories,
        'query': query,
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

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        CartItem.objects.update_or_create(
            user=request.user, product=product,
            defaults={'quantity': 1}
        )
    return redirect('marketplace:home')

def initiate_payment(request, cart_item_id):
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(id=cart_item_id, user=request.user)
        total_amount = cart_item.total_price()
        client = payment.MpesaClient(
            consumer_key=settings.MPESA_CONSUMER_KEY,
            consumer_secret=settings.MPESA_CONSUMER_SECRET,
            shortcode=settings.MPESA_SHORTCODE,
            passkey=settings.MPESA_PASSKEY,
            callback_url=settings.MPESA_CALLBACK_URL
        )
        response = client.stk_push(
            phone_number=request.user.phone_number,
            amount=total_amount,
            reference=f'Order_{cart_item.id}'
        )
        if response.get('success'):
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                status='Pending'
            )
            order.cart_items.add(cart_item)
            cart_item.delete()
            return redirect('marketplace:order_history')
        else:
            order = Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                status='Failed'
            )
            order.cart_items.add(cart_item)
            cart_item.delete()
            return render(request, 'marketplace/payment.html', {
                'response': response,
                'cart_item': cart_item,
                'error': 'Payment failed. Please try again.'
            })
    return redirect('marketplace:login')

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