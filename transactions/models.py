from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from accounts.models import Customer  # Import Customer from accounts app
from schemes.models import Scheme  # Changed from content_manager.models to schemes.models
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import datetime
import json
from .utils import item_photo_path

class Loan(models.Model):
    """Pawn loan model"""
    # Loan ID with prefix for easier identification
    loan_number = models.CharField(
        max_length=50, 
        unique=True,
        null=False,  # Ensure null is not allowed
        blank=False, # Ensure blank is not allowed
        help_text="Unique loan identifier"
    )
    
    # Customer and branch relationships
    customer = models.ForeignKey('accounts.Customer', on_delete=models.PROTECT, related_name='loans')
    branch = models.ForeignKey('branches.Branch', on_delete=models.PROTECT, related_name='loans')
    items = models.ManyToManyField('inventory.Item', through='LoanItem')
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.PROTECT, null=True, blank=True)
    
    # Status choices
    STATUS_CHOICES = (
        ('active', _('Active')),
        ('repaid', _('Repaid')),
        ('defaulted', _('Defaulted')),
        ('extended', _('Extended')),
        ('foreclosed', _('Foreclosed')),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Financial details
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    processing_fee = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Processing fee amount in whole Rupees"
    )
    distribution_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)]
    )
    
    # Important dates
    issue_date = models.DateField()
    due_date = models.DateField()
    grace_period_end = models.DateField()
    
    # Customer verification and photos
    customer_face_capture = models.TextField(blank=True, null=True, help_text="Base64-encoded customer photo")
    item_photos = models.JSONField(default=list, blank=True, help_text="List of photo URLs or base64 data")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='loans_created'
    )
    
    class Meta:
        verbose_name = _('loan')
        verbose_name_plural = _('loans')
        ordering = ['-created_at']
        permissions = [
            ("can_approve_loan", "Can approve loan"),
            ("can_extend_loan", "Can extend loan"),
            ("can_foreclose_loan", "Can foreclose loan"),
        ]

    def __str__(self):
        return f"Loan #{self.loan_number} - {self.customer.full_name}"
    
    @property
    def monthly_interest(self):
        """Calculate monthly interest details for the loan.
        
        Returns a dictionary with monthly interest rate, amount, and per thousand rate
        """
        from decimal import Decimal
        
        # Calculate monthly interest rate (annual rate / 12)
        monthly_rate = Decimal(self.interest_rate) / Decimal('12')
        
        # Calculate monthly interest amount
        monthly_amount = (self.principal_amount * monthly_rate) / Decimal('100')
        
        # Calculate rate per 1000 of principal
        per_thousand = (monthly_rate * Decimal('10')) # per Rs. 1,000
        
        return {
            'rate': round(monthly_rate, 2),
            'amount': round(monthly_amount, 2),
            'per_thousand': round(per_thousand, 2)
        }
    
    @property
    def is_overdue(self):
        # A loan is overdue if the due date has passed and it's still active
        return self.status == 'active' and self.due_date < timezone.now().date()
    
    @property
    def days_since_issue(self):
        # Number of days since the loan was issued
        return (timezone.now().date() - self.issue_date).days
    
    @property
    def days_remaining(self):
        # Number of days remaining until the due date
        if self.due_date >= timezone.now().date():
            return (self.due_date - timezone.now().date()).days
        return 0

    def save(self, *args, **kwargs):
        # Handle base64 photos
        if isinstance(self.item_photos, str) and self.item_photos.startswith('data:image/'):
            # Convert base64 to file and update item_photos
            from django.core.files.base import ContentFile
            import base64
            import os
            
            try:
                # Extract image format and data
                format, imgstr = self.item_photos.split(';base64,')
                ext = format.split('/')[-1]
                
                # Decode base64
                image_data = base64.b64decode(imgstr)
                
                # Generate filename and save
                filename = f"{uuid.uuid4()}.{ext}"
                file_path = item_photo_path(self, filename)
                file_path = os.path.join('media', file_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                
                # Update item_photos with URL
                self.item_photos = [f"/media/inventory_images/loan_{self.loan_number}/{filename}"]
                
            except Exception as e:
                print(f"Error processing base64 image: {e}")
                # Default to empty list if there's an error
                if not isinstance(self.item_photos, list):
                    self.item_photos = []
        
        # Convert item_photos to JSON if it's a list
        if isinstance(self.item_photos, list):
            try:
                self.item_photos = json.dumps(self.item_photos)
            except Exception as e:
                print(f"Error converting item_photos to JSON: {e}")
                self.item_photos = "[]"  # Default to empty JSON array
        
        # Ensure item_photos is a valid JSON string
        if isinstance(self.item_photos, str) and not self.item_photos.startswith('data:image/'):
            try:
                # Validate JSON format
                json.loads(self.item_photos)
            except json.JSONDecodeError:
                # If not valid JSON, reset to empty array
                print("Invalid JSON in item_photos, resetting to empty array")
                self.item_photos = "[]"
        
        super().save(*args, **kwargs)

    @property
    def amount_paid(self):
        """Calculate total amount paid on this loan"""
        return self.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    @property
    def remaining_balance(self):
        """Calculate remaining balance including interest"""
        return max(Decimal('0.00'), self.total_payable_mature - self.amount_paid)

    @property
    def days_since_issue(self):
        """Calculate number of days since loan was issued"""
        if not self.issue_date:
            return 0
        return (timezone.now().date() - self.issue_date).days

    @property
    def days_remaining(self):
        """Calculate number of days remaining until due date"""
        if not self.due_date:
            return 0
        remaining = (self.due_date - timezone.now().date()).days
        return max(0, remaining)

    @property
    def is_overdue(self):
        """Check if loan is overdue"""
        if not self.due_date:
            return False
        return timezone.now().date() > self.due_date and self.status == 'active'

    @property
    def total_payable_till_date(self):
        """Calculate total amount payable including interest till today"""
        if self.status != 'active':
            return Decimal('0.00')
        
        principal_amount = self.principal_amount
        
        # Get scheme details from the scheme model
        if not self.scheme:
            return principal_amount
            
        # For schemes with no_interest_period_days, check if we're still in that period
        if self.scheme.no_interest_period_days and self.days_since_issue <= self.scheme.no_interest_period_days:
            return principal_amount
            
        # Use monthly interest calculation instead of daily
        return principal_amount + self.monthly_interest_till_date()

    @property
    def total_payable_mature(self):
        """Calculate total amount payable at maturity"""
        if not self.due_date or self.status != 'active' or not self.scheme:
            return Decimal('0.00')
        
        principal_amount = self.principal_amount
        
        # For schemes with no_interest_period_days, check if loan duration is within that period
        if self.scheme.no_interest_period_days and (self.due_date - self.issue_date).days <= self.scheme.no_interest_period_days:
            return principal_amount
            
        # Calculate months between issue date and due date
        months = ((self.due_date.year - self.issue_date.year) * 12 + 
                 self.due_date.month - self.issue_date.month)
        
        # If there's any partial month, count it as a full month
        if self.due_date.day > self.issue_date.day:
            months += 1
            
        # Calculate interest using monthly rate
        monthly_info = self.monthly_interest
        monthly_amount = monthly_info['amount']
        total_interest = monthly_amount * Decimal(str(months))
        
        return principal_amount + total_interest
    
    def calculate_interest(self):
        """Calculate interest on loan"""
        if not self.due_date or self.status != 'active' or not self.scheme:
            return Decimal('0.00')
        
        # Use the transaction date for calculating days elapsed
        current_date = timezone.now().date()
        days_elapsed = (current_date - self.issue_date).days
        principal_amount = self.principal_amount
        
        # For schemes with no_interest_period_days, check if we're still in that period
        if self.scheme.no_interest_period_days and days_elapsed <= self.scheme.no_interest_period_days:
            return Decimal('0.00')
            
        # Calculate interest based on scheme interest rate
        daily_rate = self.scheme.interest_rate / Decimal('36500')  # Convert annual rate to daily rate
        interest = principal_amount * daily_rate * days_elapsed
        
        return interest
        
    @property
    def monthly_interest(self):
        """Calculate monthly interest rate and amount for the loan"""
        if not self.scheme or not self.principal_amount:
            return {
                'rate': Decimal('0.00'),
                'amount': Decimal('0.00'),
                'per_thousand': Decimal('0.00')
            }
        
        # Calculate monthly interest rate
        monthly_rate = self.scheme.interest_rate / Decimal('12')
        
        # Calculate monthly interest amount
        monthly_interest_amount = (self.principal_amount * monthly_rate) / Decimal('100')
        
        # Calculate per thousand rate (how much interest per 1000 of principal)
        per_thousand = (monthly_rate / Decimal('100')) * Decimal('1000')
        
        return {
            'rate': monthly_rate.quantize(Decimal('0.01')),
            'amount': monthly_interest_amount.quantize(Decimal('0.01')),
            'per_thousand': per_thousand.quantize(Decimal('0.01'))
        }
    
    def monthly_interest_till_date(self):
        """Calculate total monthly interest accumulated till date including current month for active loans"""
        if not self.issue_date or not self.scheme:
            return Decimal('0.00')
        
        current_date = timezone.now().date()
        months_elapsed = ((current_date.year - self.issue_date.year) * 12 + 
                        current_date.month - self.issue_date.month)
        
        # For active loans, always charge current month interest
        if self.status == 'active':
            # If we're in a different month than issue date, or if at least 1 day has passed in same month
            if months_elapsed > 0 or (months_elapsed == 0 and current_date.day > self.issue_date.day):
                months_elapsed += 1
            
        # Ensure we don't have negative months
        if months_elapsed < 0:
            months_elapsed = 0
            
        # Get monthly interest rate and amount
        monthly_info = self.monthly_interest
        monthly_amount = monthly_info['amount']
        
        return monthly_amount * Decimal(str(months_elapsed))

class LoanItem(models.Model):
    """Model to track items in a loan with their gold details"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    item = models.ForeignKey('inventory.Item', on_delete=models.CASCADE)
    
    # Gold ornament details
    gold_karat = models.DecimalField(max_digits=4, decimal_places=2, help_text="Purity of gold in karats")
    gross_weight = models.DecimalField(max_digits=7, decimal_places=3, help_text="Total weight of the ornament in grams")
    net_weight = models.DecimalField(max_digits=7, decimal_places=3, help_text="Weight of pure gold content in grams")
    stone_weight = models.DecimalField(max_digits=7, decimal_places=3, help_text="Weight of stones if any in grams", null=True, blank=True)
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
    reference_number = models.CharField(max_length=255, blank=True, null=True)  # Increased from 100 to 255
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
    reference_number = models.CharField(max_length=255, blank=True, null=True)  # Increased from 100 to 255
    
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
