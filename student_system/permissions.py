from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def staff_required(view_func):
    """Allow only staff/superusers; stack under @login_required for auth redirects."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Only administrators can perform this action.")
        return view_func(request, *args, **kwargs)
    return _wrapped


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for class-based views restricted to staff/superusers."""

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
