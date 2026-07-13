from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Product, StockMovement, Category, Supplier, Location, Department, Sale, Profile


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'supplier', 'location', 'description',
            'buying_price', 'selling_price', 'quantity',
            'minimum_stock_level', 'expiry_date', 'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }


class StockInForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'quantity', 'reason']


class StockOutForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'quantity', 'department', 'reason']


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'product', 'quantity', 'price', 'payment_method']

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        if product and quantity and quantity > product.quantity:
            raise forms.ValidationError(
                f"DENIED: Only {product.quantity} unit(s) of '{product.name}' in stock. Cannot sell {quantity}."
            )
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'short_code', 'description']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'company_name', 'phone', 'email', 'address']


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['store', 'box_number', 'notes']


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']


class CreateUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)
    phone = forms.CharField(max_length=20, required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, label="New Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class RoleUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role', 'phone']
