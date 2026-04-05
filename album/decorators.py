from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('login')

            try:
                profile = request.user.userprofile
            except:
                return HttpResponseForbidden("User profile not found")

            if not profile.is_approved:
                messages.error(request, "Account not approved yet")
                return redirect('login')

            if profile.role not in allowed_roles:
                return HttpResponseForbidden("Permission denied")

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
