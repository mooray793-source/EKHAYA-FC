from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
import barcode
from barcode.writer import ImageWriter
import io

from .models import (
    Product, Sale, Purchase, StockMovement,
    Category, Supplier, Location, Department, Profile
)
from .forms import (
    ProductForm, StockInForm, StockOutForm, SaleForm,
    CategoryForm, SupplierForm, LocationForm, DepartmentForm,
    CreateUserForm, AdminResetPasswordForm, RoleUpdateForm
)
from .decorators import role_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    total_products = Product.objects.count()
    total_stock_value = Product.objects.aggregate(
        value=Sum(F('quantity') * F('selling_price'))
    )['value'] or 0
    low_stock_qs = Product.objects.filter(quantity__gt=0, quantity__lte=F('minimum_stock_level'))
    out_of_stock = Product.objects.filter(quantity=0).count()

    soon = timezone.now().date() + timedelta(days=7)
    expiring_soon = Product.objects.filter(expiry_date__isnull=False, expiry_date__lte=soon, expiry_date__gte=timezone.now().date())

    recent_sales = Sale.objects.order_by('-date')[:5]
    recent_purchases = Purchase.objects.order_by('-purchase_date')[:5]

    context = {
        'total_products': total_products,
        'total_stock_value': total_stock_value,
        'low_stock_items': low_stock_qs.count(),
        'low_stock_products': low_stock_qs[:10],
        'out_of_stock': out_of_stock,
        'expiring_soon': expiring_soon,
        'recent_sales': recent_sales,
        'recent_purchases': recent_purchases,
        'total_categories': Category.objects.count(),
        'total_suppliers': Supplier.objects.count(),
        'total_locations': Location.objects.count(),
        'total_departments': Department.objects.count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
def product_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.all()
    if query:
        products = products.filter(name__icontains=query)
    return render(request, 'product_list.html', {'products': products, 'query': query})


@login_required
@role_required('admin', 'manager', 'storekeeper')
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully.')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'product_form.html', {'form': form})


@login_required
@role_required('admin', 'manager', 'storekeeper')
def product_edit(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"'{product.name}' updated successfully.")
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'product_form.html', {'form': form, 'editing': True, 'product': product})


@login_required
@role_required('admin', 'manager')
def product_delete(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f"'{name}' deleted successfully.")
        return redirect('product_list')
    return render(request, 'confirm_delete.html', {'object': product, 'object_name': product.name, 'cancel_url': 'product_list'})


@login_required
def product_barcode(request, product_id):
    product = Product.objects.get(id=product_id)
    code128 = barcode.get_barcode_class('code128')
    barcode_obj = code128(product.code, writer=ImageWriter())

    buffer = io.BytesIO()
    barcode_obj.write(buffer, options={
        'write_text': True,
        'module_height': 8,
        'font_size': 8,
        'text_distance': 3,
    })
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


@login_required
@role_required('admin', 'manager', 'storekeeper')
def stock_in(request):
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.movement_type = 'in'
            try:
                instance.save()
                messages.success(request, 'Stock received and added successfully.')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = StockInForm()
    return render(request, 'stock_in.html', {'form': form})


@login_required
@role_required('admin', 'manager', 'storekeeper')
def stock_out(request):
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.movement_type = 'out'
            try:
                instance.save()
                messages.success(request, 'Stock issued successfully.')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = StockOutForm()
    return render(request, 'stock_out.html', {'form': form})


@login_required
def sale_list(request):
    sales = Sale.objects.order_by('-date')[:100]
    return render(request, 'sale_list.html', {'sales': sales})


@login_required
def sale_add(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.sold_by = request.user
            sale.save()
            messages.success(request, f'Sale recorded: {sale.quantity} x {sale.product.name} = MWK {sale.total}')
            return redirect('sale_list')
    else:
        form = SaleForm()
    return render(request, 'sale_form.html', {'form': form})


@login_required
@role_required('admin', 'manager')
def reports(request):
    today = timezone.now().date()

    low_stock = Product.objects.filter(quantity__gt=0, quantity__lte=F('minimum_stock_level'))
    out_of_stock = Product.objects.filter(quantity=0)
    expired = Product.objects.filter(expiry_date__isnull=False, expiry_date__lt=today)

    stock_valuation = Product.objects.aggregate(
        value=Sum(F('quantity') * F('selling_price'))
    )['value'] or 0

    thirty_days_ago = today - timedelta(days=30)
    recent_sales = Sale.objects.filter(date__gte=thirty_days_ago)
    total_revenue = sum(s.total for s in recent_sales)

    total_cost_of_goods_sold = sum(
        (s.product.buying_price * s.quantity) for s in recent_sales if s.product
    )
    total_profit = total_revenue - total_cost_of_goods_sold
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    best_sellers = (
        Sale.objects.filter(date__gte=thirty_days_ago)
        .values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    supplier_purchases = (
        Purchase.objects.values('supplier__name')
        .annotate(total_qty=Sum('quantity'), total_cost=Sum('cost'))
        .order_by('-total_cost')[:10]
    )

    context = {
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'expired': expired,
        'stock_valuation': stock_valuation,
        'total_revenue': total_revenue,
        'total_cost_of_goods_sold': total_cost_of_goods_sold,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'recent_sales_count': recent_sales.count(),
        'best_sellers': best_sellers,
        'supplier_purchases': supplier_purchases,
    }
    return render(request, 'reports.html', context)


@login_required
@role_required('admin', 'manager')
def category_list(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'form': form, 'categories': categories})


@login_required
@role_required('admin', 'manager')
def category_edit(request, pk):
    obj = Category.objects.get(id=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=obj)
    return render(request, 'generic_edit.html', {'form': form, 'title': f'Edit Category: {obj.name}', 'cancel_url': 'category_list'})


@login_required
@role_required('admin', 'manager')
def category_delete(request, pk):
    obj = Category.objects.get(id=pk)
    if request.method == 'POST':
        name = obj.name
        obj.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('category_list')
    return render(request, 'confirm_delete.html', {'object': obj, 'object_name': obj.name, 'cancel_url': 'category_list'})


@login_required
@role_required('admin', 'manager')
def supplier_list(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    suppliers = Supplier.objects.all()
    return render(request, 'supplier_list.html', {'form': form, 'suppliers': suppliers})


@login_required
@role_required('admin', 'manager')
def supplier_edit(request, pk):
    obj = Supplier.objects.get(id=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Supplier updated.")
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=obj)
    return render(request, 'generic_edit.html', {'form': form, 'title': f'Edit Supplier: {obj.name}', 'cancel_url': 'supplier_list'})


@login_required
@role_required('admin', 'manager')
def supplier_delete(request, pk):
    obj = Supplier.objects.get(id=pk)
    if request.method == 'POST':
        name = obj.name
        obj.delete()
        messages.success(request, f"Supplier '{name}' deleted.")
        return redirect('supplier_list')
    return render(request, 'confirm_delete.html', {'object': obj, 'object_name': obj.name, 'cancel_url': 'supplier_list'})


@login_required
@role_required('admin', 'manager')
def location_list(request):
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Location added successfully.')
            return redirect('location_list')
    else:
        form = LocationForm()
    locations = Location.objects.all()
    return render(request, 'location_list.html', {'form': form, 'locations': locations})


@login_required
@role_required('admin', 'manager')
def location_edit(request, pk):
    obj = Location.objects.get(id=pk)
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Location updated.")
            return redirect('location_list')
    else:
        form = LocationForm(instance=obj)
    return render(request, 'generic_edit.html', {'form': form, 'title': f'Edit Location: {obj}', 'cancel_url': 'location_list'})


@login_required
@role_required('admin', 'manager')
def location_delete(request, pk):
    obj = Location.objects.get(id=pk)
    if request.method == 'POST':
        name = str(obj)
        obj.delete()
        messages.success(request, f"Location '{name}' deleted.")
        return redirect('location_list')
    return render(request, 'confirm_delete.html', {'object': obj, 'object_name': str(obj), 'cancel_url': 'location_list'})


@login_required
@role_required('admin', 'manager')
def department_list(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department added successfully.')
            return redirect('department_list')
    else:
        form = DepartmentForm()
    departments = Department.objects.all()
    return render(request, 'department_list.html', {'form': form, 'departments': departments})


@login_required
@role_required('admin', 'manager')
def department_edit(request, pk):
    obj = Department.objects.get(id=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated.")
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=obj)
    return render(request, 'generic_edit.html', {'form': form, 'title': f'Edit Department: {obj.name}', 'cancel_url': 'department_list'})


@login_required
@role_required('admin', 'manager')
def department_delete(request, pk):
    obj = Department.objects.get(id=pk)
    if request.method == 'POST':
        name = obj.name
        obj.delete()
        messages.success(request, f"Department '{name}' deleted.")
        return redirect('department_list')
    return render(request, 'confirm_delete.html', {'object': obj, 'object_name': obj.name, 'cancel_url': 'department_list'})


@login_required
def verify_admin_pin(request):
    if request.method == 'POST':
        pin = request.POST.get('pin', '')
        if pin == django_settings.ADMIN_PANEL_PIN:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False})
    return JsonResponse({'success': False})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'change_password.html', {'form': form})


@login_required
@role_required('admin')
def user_list(request):
    users = User.objects.select_related('profile').all().order_by('username')
    return render(request, 'user_list.html', {'users': users})


@login_required
@role_required('admin')
def user_create(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            profile, created = Profile.objects.get_or_create(user=user)
            profile.role = form.cleaned_data['role']
            profile.phone = form.cleaned_data['phone']
            profile.save()
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect('user_list')
    else:
        form = CreateUserForm()
    return render(request, 'user_form.html', {'form': form})


@login_required
@role_required('admin')
def user_reset_password(request, user_id):
    target_user = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = AdminResetPasswordForm(request.POST)
        if form.is_valid():
            target_user.set_password(form.cleaned_data['new_password'])
            target_user.save()
            messages.success(request, f"Password for '{target_user.username}' has been reset.")
            return redirect('user_list')
    else:
        form = AdminResetPasswordForm()
    return render(request, 'user_reset_password.html', {'form': form, 'target_user': target_user})


@login_required
@role_required('admin')
def user_edit_role(request, user_id):
    target_user = User.objects.get(id=user_id)
    profile, created = Profile.objects.get_or_create(user=target_user)
    if request.method == 'POST':
        form = RoleUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Role for '{target_user.username}' updated.")
            return redirect('user_list')
    else:
        form = RoleUpdateForm(instance=profile)
    return render(request, 'user_edit_role.html', {'form': form, 'target_user': target_user})


@login_required
@role_required('admin')
def user_deactivate(request, user_id):
    target_user = User.objects.get(id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('user_list')
    target_user.is_active = False
    target_user.save()
    messages.success(request, f"'{target_user.username}' has been deactivated and can no longer log in.")
    return redirect('user_list')


@login_required
@role_required('admin')
def user_reactivate(request, user_id):
    target_user = User.objects.get(id=user_id)
    target_user.is_active = True
    target_user.save()
    messages.success(request, f"'{target_user.username}' has been reactivated.")
    return redirect('user_list')
