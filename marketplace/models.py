# ecommerce_project/marketplace/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True)
    is_seller = models.BooleanField(default=False)

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    def total_price(self):
        return self.quantity * self.product.price
    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    cart_items = models.ManyToManyField(CartItem)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    def __str__(self):
        return f"Profile of {self.user.username}"