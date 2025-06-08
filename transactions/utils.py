from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

class ManagerPermissionMixin(UserPassesTestMixin):
    """
    Permission mixin that restricts access to managers, regional managers, and admin users only.
    Regular employees will be redirected with an error message.
    """
    permission_denied_message = "Only branch managers, regional managers, and administrators can edit loans."
    
    def test_func(self):
        """Check if user has manager-level permissions."""
        # Allow superuser access
        if self.request.user.is_superuser:
            return True
        
        # Check if the user has a role
        if not hasattr(self.request.user, 'role') or not self.request.user.role:
            return False
        
        # Check if role name indicates manager-level permissions
        role_name = self.request.user.role.name.lower()
        return any(title in role_name for title in ['manager', 'admin', 'director', 'supervisor', 'head'])
    
    def handle_no_permission(self):
        """Show an error message and redirect when permission is denied."""
        messages.error(self.request, self.permission_denied_message)
        return redirect('loan_detail', loan_number=self.kwargs.get('loan_number'))