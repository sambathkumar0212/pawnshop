from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """Custom role model for user permissions"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    
    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')
        
    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    phone = models.CharField(max_length=20, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    face_id = models.BooleanField(default=False, help_text=_('Whether face ID is enabled for this user'))
    face_encoding = models.BinaryField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    def save(self, *args, **kwargs):
        # Set proper permissions based on role
        super().save(*args, **kwargs)
        if self.role:
            self.user_permissions.set(self.role.permissions.all())


class UserActivity(models.Model):
    """Track user activity in the system"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('user activity')
        verbose_name_plural = _('user activities')
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.user} - {self.activity_type} - {self.timestamp}"


# Add the Customer model that's referenced in the inventory app
class Customer(models.Model):
    """Model for pawnshop customers"""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    profile_photo = models.TextField(blank=True, null=True, help_text="Base64-encoded profile photo of customer")
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    id_type = models.CharField(max_length=50, blank=True, help_text="Type of ID provided")
    id_number = models.CharField(max_length=50, blank=True, help_text="ID document number")
    id_image = models.ImageField(upload_to='customer_ids/', blank=True, null=True)
    face_encoding = models.BinaryField(null=True, blank=True, help_text="Binary data for facial recognition")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        related_name='created_customers',
        on_delete=models.SET_NULL,
        null=True
    )
    
    class Meta:
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def active_loans_count(self):
        """Return number of active loans for this customer"""
        # Using a property to prevent circular import
        return self.loans.filter(status='active').count() if hasattr(self, 'loans') else 0
