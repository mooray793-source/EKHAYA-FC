from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('storekeeper', 'Store Keeper'),
        ('sales', 'Sales Person'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales')
    phone = models.CharField(max_length=20, blank=True)

    def can_receive_stock(self):
        return self.role in ['admin', 'manager', 'storekeeper']

    def can_issue_stock(self):
        return self.role in ['admin', 'manager', 'storekeeper']

    def can_manage_master_data(self):
        return self.role in ['admin', 'manager']

    def can_approve_allocations(self):
        return self.role in ['admin', 'manager']

    def can_view_reports(self):
        return self.role in ['admin', 'manager']

    def can_manage_users(self):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_code = models.CharField(max_length=10, unique=True, default='GEN', help_text="e.g. TRN for Training Kits")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    store = models.CharField(max_length=50, help_text="e.g. Store A, Store B")
    box_number = models.CharField(max_length=50, help_text="e.g. Box 1, Shelf 2")
    notes = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.store} - {self.box_number}"

    class Meta:
        unique_together = ('store', 'box_number')


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class DepartmentAllocation(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='allocations')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='allocations')
    allocated_quantity = models.PositiveIntegerField(help_text="Max units this department can draw for this category")
    period_start = models.DateField(default=timezone.now)
    period_end = models.DateField(null=True, blank=True)

    def used_quantity(self):
        total = StockMovement.objects.filter(
            department=self.department,
            product__category=self.category,
            movement_type='out'
        ).aggregate(total=models.Sum('quantity'))['total']
        return total or 0

    def remaining_quantity(self):
        return self.allocated_quantity - self.used_quantity()

    def __str__(self):
        return f"{self.department.name} - {self.category.name} (limit: {self.allocated_quantity})"

    class Meta:
        unique_together = ('department', 'category')


class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True)
    buying_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    minimum_stock_level = models.PositiveIntegerField(default=5)
    expiry_date = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.minimum_stock_level:
            return "Low Stock"
        return "Available"

    def generate_code(self):
        cat_part = self.category.short_code if self.category else "GEN"
        if self.location:
            loc_part = f"{self.location.store}-{self.location.box_number}"
        else:
            loc_part = "NA"
        base_code = f"{cat_part}-{loc_part}".upper().replace(" ", "")
        candidate = base_code
        counter = 1
        while Product.objects.filter(code=candidate).exclude(pk=self.pk).exists():
            counter += 1
            candidate = f"{base_code}-{counter}"
        return candidate

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('damaged', 'Damaged'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    reason = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)

    def clean(self):
        if self.movement_type == 'out' and self.department and self.product and self.product.category:
            try:
                allocation = DepartmentAllocation.objects.get(
                    department=self.department,
                    category=self.product.category
                )
            except DepartmentAllocation.DoesNotExist:
                allocation = None

            if allocation:
                used = StockMovement.objects.filter(
                    department=self.department,
                    product__category=self.product.category,
                    movement_type='out'
                ).exclude(pk=self.pk).aggregate(total=models.Sum('quantity'))['total'] or 0

                remaining = allocation.allocated_quantity - used

                if self.quantity > remaining:
                    raise ValidationError(
                        f"DENIED: {self.department.name} has only {remaining} unit(s) left "
                        f"of their {allocation.allocated_quantity}-unit allocation for "
                        f"'{self.product.category.name}'. Requested: {self.quantity}."
                    )

        if self.movement_type in ('out', 'damaged') and self.product and self.quantity > self.product.quantity:
            raise ValidationError(
                f"DENIED: Only {self.product.quantity} unit(s) of '{self.product.name}' "
                f"are in stock. Cannot issue {self.quantity}."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.movement_type == 'in':
            self.product.quantity += self.quantity
        elif self.movement_type in ('out', 'damaged'):
            self.product.quantity -= self.quantity
        self.product.save()

    def __str__(self):
        dept = f" -> {self.department.name}" if self.department else ""
        return f"{self.movement_type} - {self.product.name} ({self.quantity}){dept}"


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchases')
    quantity = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    purchase_date = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.quantity += self.quantity
        self.product.save()

    def __str__(self):
        return f"Purchase: {self.product.name} x{self.quantity}"


class Sale(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
        ('credit', 'Credit'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)

    @property
    def total(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.quantity -= self.quantity
        self.product.save()

    def __str__(self):
        return f"Sale: {self.product.name} x{self.quantity}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}: {self.action} at {self.timestamp}"
