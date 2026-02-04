from django.contrib import admin

# Register your models here.
from .models import User, Category, Product, Address
from .models import SavedCard

admin.site.register(User)
#admin.site.register(Category)
#admin.site.register(Product)

admin.site.register(Address)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'discount_price', 'quantity', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    list_editable = ('quantity', 'is_active')

@admin.register(SavedCard)
class SavedCardAdmin(admin.ModelAdmin):
    list_display = ("user", "brand", "last4", "exp_month", "exp_year")