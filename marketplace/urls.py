from django.urls import path
from . import views

app_name = 'marketplace'
urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('cart/', views.cart, name='cart'),
    path('orders/', views.order_history, name='orders'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('initiate_payment/<int:cart_item_id>/', views.initiate_payment, name='initiate_payment'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/product/add/', views.add_product, name='add_product'),
    path('seller/product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('seller/product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('orders/', views.order_history, name='order_history'),
    path('search/', views.search_products, name='search_products'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('add-review/<int:product_id>/', views.add_review, name='add_review'),
    path('search-autocomplete/', views.search_autocomplete, name='search_autocomplete'),
    path('set-theme/', views.set_theme, name='set_theme'),
]