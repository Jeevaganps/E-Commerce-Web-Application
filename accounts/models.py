from django.db import models
from django.conf import settings
# Create your models here.
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin
from.manage import CustomUserManager
from django.contrib.auth.models import AbstractUser

class User(AbstractBaseUser,PermissionsMixin):
    email = models.EmailField(unique=True)
    #username = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    objects = CustomUserManager()


    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']  #'username', 

class Category(models.Model):
    name = models.CharField(max_length=250)
    image = models.ImageField(upload_to='categories/')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=250)
    brand = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name 
    
    # Final price logic
    def get_final_price(self):
        return self.discount_price if self.discount_price else self.price

    # Check stock status
    def is_in_stock(self):
        return self.quantity > 0       

class cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name} for {self.user.email}"    
    
    def get_total_price(self):
        return self.quantity * self.product.price
    
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=100, default='India')

    def __str__(self):
        return f"{self.address_line}, {self.city}"

class SavedCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=200)  # pm_xxx token
    brand = models.CharField(max_length=20)
    last4 = models.CharField(max_length=4)
    exp_month = models.IntegerField()
    exp_year = models.IntegerField()

    def __str__(self):
        return f"{self.brand} **** {self.last4}"

from django.db import models
from django.contrib.auth.models import User


class Favourite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,   # <-- FIXED
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE
    )
    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user} - {self.product.name}"
