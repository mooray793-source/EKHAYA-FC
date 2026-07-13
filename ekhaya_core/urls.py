from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from inventory import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('stock/in/', views.stock_in, name='stock_in'),
    path('stock/out/', views.stock_out, name='stock_out'),
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/add/', views.sale_add, name='sale_add'),
    path('reports/', views.reports, name='reports'),
    path('categories/', views.category_list, name='category_list'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('locations/', views.location_list, name='location_list'),
    path('departments/', views.department_list, name='department_list'),
    path('verify-admin-pin/', views.verify_admin_pin, name='verify_admin_pin'),
    path('change-password/', views.change_password, name='change_password'),
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('users/<int:user_id>/edit-role/', views.user_edit_role, name='user_edit_role'),
    path('products/<int:product_id>/barcode/', views.product_barcode, name='product_barcode'),]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
