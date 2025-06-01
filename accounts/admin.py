from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role, UserActivity, Customer


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role', 'branch')
    list_filter = ('is_staff', 'is_active', 'role', 'branch')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'role', 'branch', 'face_id', 'face_encoding')}),
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'phone', 'email', 'city', 'get_active_loans')
    list_filter = ('city', 'state')
    search_fields = ('first_name', 'last_name', 'phone', 'email', 'id_number')
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'email')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
        ('Identification', {
            'fields': ('id_type', 'id_number', 'id_image')
        }),
        ('Additional Information', {
            'fields': ('notes', 'face_encoding')
        }),
    )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Name'

    def get_active_loans(self, obj):
        return obj.loans.filter(status='active').count()
    get_active_loans.short_description = 'Active Loans'


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    filter_horizontal = ('permissions',)
    search_fields = ('name', 'description')


class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'description')
    readonly_fields = ('user', 'activity_type', 'timestamp', 'description', 'ip_address')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
