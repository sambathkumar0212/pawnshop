from django.db import models
from django.utils import timezone
from branches.models import Branch
from accounts.models import CustomUser
from django.urls import reverse

class Scheme(models.Model):
    """
    Model to store scheme details that can be managed by branch managers or regional managers.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('upcoming', 'Upcoming'),
        ('expired', 'Expired'),
    )

    name = models.CharField(max_length=100, help_text="Name of the scheme")
    description = models.TextField(help_text="Detailed description of the scheme")
    
    # Conditions
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, 
                                       help_text="Interest rate for the scheme (in %)")
    loan_duration = models.PositiveIntegerField(
        help_text="Standard loan duration in days")
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, 
                                       help_text="Minimum loan amount")
    maximum_amount = models.DecimalField(max_digits=10, decimal_places=2, 
                                       help_text="Maximum loan amount")
    
    # Additional conditions - can be stored as JSON
    additional_conditions = models.JSONField(null=True, blank=True, 
                                           help_text="Additional conditions in JSON format")
    
    # Dates
    start_date = models.DateField(help_text="Date when the scheme becomes active")
    end_date = models.DateField(null=True, blank=True, 
                               help_text="Date when the scheme expires (leave blank for ongoing)")
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, 
        related_name='created_schemes'
    )
    updated_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, 
        related_name='updated_schemes'
    )
    
    # Branch association (can be null for global schemes)
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, null=True, blank=True,
        related_name='loan_schemes',
        help_text="Branch the scheme is associated with (leave empty for global schemes)"
    )

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("view_all_schemes", "Can view all schemes including from other branches"),
            ("manage_global_schemes", "Can manage schemes that apply globally"),
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['branch']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('scheme_detail', kwargs={'pk': self.pk})
    
    @property
    def is_active(self):
        today = timezone.now().date()
        return (self.status == 'active' and 
                self.start_date <= today and 
                (not self.end_date or self.end_date >= today))
    
    @property
    def no_interest_period_days(self):
        """Returns the no_interest_period_days from additional_conditions if present"""
        if self.additional_conditions and 'no_interest_period_days' in self.additional_conditions:
            return self.additional_conditions['no_interest_period_days']
        return None
    
    def update_status(self):
        """
        Update the status of the scheme based on current date and start/end dates
        """
        today = timezone.now().date()
        
        if self.status == 'inactive':
            # Don't change inactive status automatically
            return
            
        if self.start_date > today:
            self.status = 'upcoming'
        elif self.end_date and self.end_date < today:
            self.status = 'expired'
        else:
            self.status = 'active'
        
        self.save(update_fields=['status'])


class SchemeAuditLog(models.Model):
    """
    Model to keep track of all changes made to schemes
    """
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20)  # created, updated, deleted
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} on {self.scheme.name} by {self.user.username}"
