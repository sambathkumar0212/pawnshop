from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, Role, Region, UserActivity, Customer


class CustomUserAdmin(UserAdmin):
    """Custom admin for the CustomUser model"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'branch', 'is_staff')
    list_filter = ('role', 'branch', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        (_('Role & Branch'), {'fields': ('role', 'branch', 'regions')}),
        (_('Face ID'), {'fields': ('face_id', 'face_encoding')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('date_joined', 'last_login')}),
    )
    
    filter_horizontal = ('groups', 'user_permissions', 'regions')


class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model"""
    list_display = ('name', 'role_type', 'category')
    list_filter = ('category', 'role_type')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)
    
    def save_model(self, request, obj, form, change):
        """Apply default permissions when new roles are created"""
        from .permissions import get_role_permissions
        
        # Save the model first
        super().save_model(request, obj, form, change)
        
        # Apply default permissions if this is a new role
        if not change:  # If this is a new role
            # Get default permissions for this role type
            default_permissions = get_role_permissions().get(obj.role_type, [])
            
            # If default permissions exist, apply them
            if default_permissions:
                from django.contrib.auth.models import Permission
                from django.contrib.contenttypes.models import ContentType
                
                # Get all permissions with matching codenames
                permissions_to_add = Permission.objects.filter(codename__in=default_permissions)
                
                # Apply these permissions to the role
                obj.permissions.add(*permissions_to_add)


class RegionAdmin(admin.ModelAdmin):
    """Admin for Region model"""
    list_display = ('name', 'branch_count')
    search_fields = ('name', 'description')


class UserActivityAdmin(admin.ModelAdmin):
    """Admin for UserActivity model"""
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'description')
    readonly_fields = ('user', 'activity_type', 'timestamp', 'description', 'ip_address')


class CustomerAdmin(admin.ModelAdmin):
    """Admin for Customer model"""
    list_display = ('first_name', 'last_name', 'phone', 'branch', 'active_loans_count')
    list_filter = ('branch',)
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    fieldsets = (
        (_('Personal Information'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'profile_photo')}),
        (_('Address'), {'fields': ('address', 'city', 'state', 'zip_code')}),
        (_('Branch Information'), {'fields': ('branch',)}),
        (_('ID Information'), {'fields': ('id_type', 'id_number', 'id_image')}),
        (_('Biometrics'), {'fields': ('face_encoding',)}),
        (_('Additional Information'), {'fields': ('notes', 'created_by')}),
    )
    readonly_fields = ('created_at', 'updated_at')


# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Region, RegionAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(Customer, CustomerAdmin)
