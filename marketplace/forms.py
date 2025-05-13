from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User, Product

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone_number', 'is_seller')
        
class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'phone_number', 'is_seller')

class UpdatePasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(user=kwargs.pop('user', None), *args, **kwargs)
        
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name', 'description', 'price', 'category', 'image')