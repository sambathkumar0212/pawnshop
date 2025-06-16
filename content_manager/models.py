from django.db import models
from django.conf import settings
from django.utils import timezone
from branches.models import Branch
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


class Scheme(models.Model):
    """Model for loan schemes that branch managers can administer"""
    SCHEME_TYPE_CHOICES = [
        ('GOLD', 'Gold Loan'),
        ('MORTGAGE', 'Mortgage Loan'),
        ('VEHICLE', 'Vehicle Loan'),
        ('PERSONAL', 'Personal Loan'),
        ('BUSINESS', 'Business Loan'),
        ('OTHER', 'Other Loan')
    ]
    
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True, help_text="Short code for reference")
    scheme_type = models.CharField(max_length=20, choices=SCHEME_TYPE_CHOICES, default='GOLD')
    description = models.TextField(blank=True)
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Annual interest rate as a percentage (e.g. 12.00 for 12%)"
    )
    duration_days = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Standard duration in days"
    )
    no_interest_period_days = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of days without interest if repaid early"
    )
    minimum_period_days = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum period before loan can be closed (0 for no minimum)"
    )
    processing_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Processing fee as a percentage of loan amount"
    )
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE, 
        related_name='schemes',
        null=True,
        blank=True, 
        help_text="Leave blank for global schemes available to all branches"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Loan Scheme"
        verbose_name_plural = "Loan Schemes"
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'branch'], 
                name='unique_scheme_per_branch'
            )
        ]
    
    def __str__(self):
        if self.branch:
            return f"{self.name} ({self.branch.name})"
        return f"{self.name} (Global)"
        
    def save(self, *args, **kwargs):
        # Generate code from name if not provided
        if not self.code:
            self.code = slugify(self.name)[:20]
        
        super().save(*args, **kwargs)


class SchemeUsageStats(models.Model):
    """Model to track usage statistics for loan schemes"""
    scheme = models.ForeignKey(
        Scheme, 
        on_delete=models.CASCADE,
        related_name='usage_stats'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Usage statistics
    total_loans_count = models.IntegerField(default=0)
    active_loans_count = models.IntegerField(default=0)
    completed_loans_count = models.IntegerField(default=0)
    defaulted_loans_count = models.IntegerField(default=0)
    
    # Financial metrics
    total_principal_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_interest_earned = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_processing_fees = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Additional metrics
    average_loan_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_loan_duration = models.IntegerField(default=0, help_text="Average actual loan duration in days")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Scheme Usage Statistic"
        verbose_name_plural = "Scheme Usage Statistics"
        unique_together = ('scheme', 'branch', 'start_date', 'end_date')
        ordering = ['-end_date', 'scheme']
    
    def __str__(self):
        branch_name = self.branch.name if self.branch else "All Branches"
        return f"{self.scheme.name} - {branch_name} ({self.start_date} to {self.end_date})"
    
    @property
    def default_rate(self):
        """Calculate the default rate as a percentage"""
        if self.total_loans_count == 0:
            return 0
        return (self.defaulted_loans_count / self.total_loans_count) * 100
    
    @property
    def completion_rate(self):
        """Calculate the completion rate as a percentage"""
        if self.total_loans_count == 0:
            return 0
        return (self.completed_loans_count / self.total_loans_count) * 100


class SchemeNotification(models.Model):
    """Model for notifications about special schemes to alert staff"""
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent')
    ]
    
    scheme = models.ForeignKey(
        Scheme, 
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=100)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    
    # Target audience
    all_branches = models.BooleanField(default=False, help_text="Show to all branches")
    branches = models.ManyToManyField(Branch, blank=True, related_name='scheme_notifications')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', '-start_date']
    
    def __str__(self):
        return f"{self.title} ({self.scheme.name})"
    
    @property
    def is_current(self):
        """Check if the notification is currently active based on dates"""
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date
