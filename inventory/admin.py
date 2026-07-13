from django.contrib import admin
from .models import (
    Profile, Category, Supplier, Customer, Location,
    Department, DepartmentAllocation,
    Product, StockMovement, Purchase, Sale, AuditLog
)

admin.site.site_header = "Ekhaya Inventory Management System"
admin.site.site_title = "Ekhaya Inventory"
admin.site.index_title = "Welcome to Ekhaya Inventory Dashboard"

admin.site.register(Profile)
admin.site.register(Supplier)
admin.site.register(Customer)
admin.site.register(Location)
admin.site.register(Department)
admin.site.register(Purchase)
admin.site.register(AuditLog)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code')


@admin.register(DepartmentAllocation)
class DepartmentAllocationAdmin(admin.ModelAdmin):
    list_display = ('department', 'category', 'allocated_quantity', 'used_quantity', 'remaining_quantity')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'location', 'quantity', 'selling_price', 'status')
    search_fields = ('name', 'code')
    list_filter = ('category', 'supplier', 'location')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'department', 'date')
    list_filter = ('movement_type', 'department')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'price', 'total', 'payment_method', 'date')
