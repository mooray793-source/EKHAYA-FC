from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from .models import Profile


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            profile, created = Profile.objects.get_or_create(user=request.user)
            if profile.role not in roles:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
