from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from accounts.models import Customer  # Import Customer from accounts app
import uuid


class Loan(models.Model):
    """Pawn loan model"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('repaid', 'Repaid'),
        ('defaulted', 'Defaulted'),
        ('extended', 'Extended'),
        ('foreclosed', 'Foreclosed'),
    ]
    
    # Basic information
    loan_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    items = models.ManyToManyField('inventory.Item', through='LoanItem', related_name='loans')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='loans')
    
    # Financial information
    principal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    distribution_amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total_payable = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateField()
    due_date = models.DateField()
    grace_period_end = models.DateField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Management
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, related_name='loans_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('loan')
        verbose_name_plural = _('loans')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Loan #{self.loan_number} - {self.customer}"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now().date() and self.status == 'active'
    
    @property
    def days_remaining(self):
        from django.utils import timezone
        if self.status != 'active':
            return 0
        delta = self.due_date - timezone.now().date()
        return max(0, delta.days)

class LoanItem(models.Model):
    """Model to track items in a loan with their gold details"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    item = models.ForeignKey('inventory.Item', on_delete=models.CASCADE)
    
    # Gold ornament details
    gold_karat = models.DecimalField(max_digits=4, decimal_places=2, help_text="Purity of gold in karats")
    gross_weight = models.DecimalField(max_digits=7, decimal_places=3, help_text="Total weight of the ornament in grams")
    net_weight = models.DecimalField(max_digits=7, decimal_places=3, help_text="Weight of pure gold content in grams")
    stone_weight = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True, help_text="Weight of stones if any in grams")
    market_price_22k = models.DecimalField(max_digits=10, decimal_places=2, help_text="Market price of 22K gold per gram at the time of loan")
    
    class Meta:
        unique_together = ['loan', 'item']  # An item can only be used once in a loan
        
    def __str__(self):
        return f"{self.item.name} in {self.loan}"

class Payment(models.Model):
    """Payment model for tracking loan payments"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('other', 'Other'),
    ]
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, related_name='payments_received')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.loan}"


class LoanExtension(models.Model):
    """Model to track loan extensions/renewals"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='extensions')
    extension_date = models.DateField()
    previous_due_date = models.DateField()
    new_due_date = models.DateField()
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, related_name='extensions_approved')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('loan extension')
        verbose_name_plural = _('loan extensions')
        ordering = ['-extension_date']
    
    def __str__(self):
        return f"Extension for {self.loan} - {self.extension_date}"


class Sale(models.Model):
    """Model for sale transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    ]
    
    transaction_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    item = models.ForeignKey('inventory.Item', on_delete=models.CASCADE, related_name='sales')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='sales')
    
    # Financial information
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=Payment.PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sale_date = models.DateField()
    
    # Management
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                              null=True, related_name='sales_processed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('sale')
        verbose_name_plural = _('sales')
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"Sale #{self.transaction_number} - ₹{self.total_amount}"
