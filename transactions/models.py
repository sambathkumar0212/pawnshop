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
    
    SCHEME_CHOICES = [
        ('standard', 'Standard (12% - Min 3 months)'),
        ('flexible', 'Flexible (24% - No interest if repaid within 25 days)'),
    ]
    
    # Basic information
    loan_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    items = models.ManyToManyField('inventory.Item', through='LoanItem', related_name='loans')
    branch = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='loans')
    
    # Scheme type
    scheme = models.CharField(max_length=20, choices=SCHEME_CHOICES, default='standard')
    
    # Photo information
    customer_face_capture = models.TextField(blank=True, null=True, help_text="Base64-encoded customer photo")
    item_photos = models.TextField(blank=True, null=True, help_text="JSON string of Base64-encoded item photos")
    
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
        
    @property
    def total_interest(self):
        """Calculate the total interest amount"""
        return self.total_payable - self.principal_amount - self.processing_fee
        
    @property
    def amount_paid(self):
        """Calculate the total amount paid so far"""
        return self.payments.aggregate(models.Sum('amount'))['amount__sum'] or 0
        
    @property
    def remaining_balance(self):
        """Calculate the remaining amount to be paid"""
        return self.total_payable - self.amount_paid
        
    @property
    def is_in_grace_period(self):
        """Check if the loan is in grace period"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.due_date < today <= self.grace_period_end and self.status == 'active'
        
    @property
    def payment_status_display(self):
        """Returns a human-readable payment status"""
        if self.status == 'repaid':
            return "Fully Paid"
        elif self.amount_paid >= self.principal_amount:
            return "Principal Recovered"
        elif self.amount_paid > 0:
            return "Partially Paid"
        else:
            return "No Payments"
            
    @property
    def can_be_repaid(self):
        """Check if loan can be repaid based on the scheme rules"""
        from django.utils import timezone
        today = timezone.now().date()
        # Standard scheme - can only be repaid after 3 months
        if self.scheme == 'standard':
            min_duration = timezone.timedelta(days=90)  # 3 months
            return (today - self.issue_date) >= min_duration
        # Flexible scheme - can be repaid anytime
        return True
        
    @property
    def days_since_issue(self):
        """Calculate days since loan was issued"""
        from django.utils import timezone
        today = timezone.now().date()
        return (today - self.issue_date).days
    
    @property
    def total_payable_till_date(self):
        """Calculate total payable amount as of today (principal + interest till date)"""
        from django.utils import timezone
        from decimal import Decimal
        
        today = timezone.now().date()
        principal_amount = self.principal_amount
        days_elapsed = (today - self.issue_date).days
        
        # For flexible scheme with early repayment within 25 days
        if self.scheme == 'flexible' and days_elapsed <= 25:
            interest_amount = Decimal('0.00')
        else:
            # Calculate interest based on scheme and elapsed time
            # For standard scheme: 12% per year = 0.03287% per day
            # For flexible scheme: 24% per year = 0.06575% per day
            daily_rate = Decimal('0.0003287') if self.scheme == 'standard' else Decimal('0.0006575')
            interest_amount = principal_amount * daily_rate * days_elapsed
        
        # Return gross total payable (principal + interest)
        return principal_amount + interest_amount
    
    @property
    def total_payable_mature(self):
        """Calculate total payable amount at maturity (principal + full interest till due date)"""
        # This will be the same as the stored total_payable which is calculated at loan creation
        return self.total_payable
        
    def calculate_interest_amount(self):
        """Calculate interest amount based on scheme rules"""
        from django.utils import timezone
        from decimal import Decimal
        today = timezone.now().date()
        
        # Flexible scheme with no interest if repaid within 25 days
        if self.scheme == 'flexible' and (today - self.issue_date).days <= 25:
            return Decimal('0.00')
            
        # Otherwise, use the standard interest rate calculation
        return self.principal_amount * (self.interest_rate / Decimal('100'))
    
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
