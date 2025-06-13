from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from .models import Loan, Payment, LoanExtension, Sale, LoanItem
from inventory.models import Item, Category
from inventory.forms import ItemForm
from accounts.models import Customer
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div
from decimal import Decimal, InvalidOperation
from django.utils import timezone

class LoanForm(forms.ModelForm):
    distribution_amount = forms.DecimalField(
        disabled=True,
        required=False,
        max_digits=10,
        decimal_places=0,
        help_text="Amount to be distributed after processing fee",
        widget=forms.NumberInput(attrs={
            'data-show-words': 'true'  # Custom attribute to identify fields that need words display
        })
    )

    scheme = forms.ChoiceField(
        choices=Loan.SCHEME_CHOICES,
        initial='standard',
        help_text="Select loan scheme: Standard (12%), Flexible (24% - no interest if paid within 23 days), or Premium (36% - no interest if paid within 30 days)"
    )

    KARAT_CHOICES = [
        ('24', '24K (99.9%) - Pure Gold'),
        ('22', '22K (91.6%) - Indian Standard'),
        ('21', '21K (87.5%) - Middle Eastern'),
        ('20', '20K (83.3%) - Indian Standard'),
        ('18', '18K (75.0%) - European Standard'),
        ('14', '14K (58.3%) - US Common'),
    ]

    KARAT_PURITY = {
        '24': Decimal('0.999'),
        '22': Decimal('0.916'),
        '21': Decimal('0.875'),
        '20': Decimal('0.833'),
        '18': Decimal('0.750'),
        '14': Decimal('0.583'),
    }

    # Item fields for new items
    item_name = forms.CharField(
        label='Item Name',
        help_text='Enter the name or description of the gold item',
        max_length=255,
        required=True
    )
    item_description = forms.CharField(
        required=False,  # Making it optional
        label='Item Description',
        help_text='Optional: Detailed description of the item including any distinguishing marks or damaged parts',
        widget=forms.Textarea(attrs={'rows': 3})
    )
    item_category = forms.ModelChoiceField(
        required=True,
        queryset=Category.objects.all(),  # Will filter in __init__
        label='Ornament Type',
        help_text="Select the type of gold ornament"
    )
    gold_karat = forms.ChoiceField(
        required=False,
        choices=KARAT_CHOICES,
        initial='22',
        help_text="Select the purity of gold"
    )
    market_price_22k = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        label="Today's 22K Gold Price (per gram)",
        help_text="Enter today's market price for 22K gold per gram"
    )
    gross_weight = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=3,
        help_text="Total weight of the ornament in grams"
    )
    net_weight = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=3,
        widget=forms.NumberInput(attrs={'style': 'width: 50%;'}),  # Added style to make width 50%
        help_text="Weight of pure gold content in grams"
    )
    stone_weight = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=3,
        help_text="Weight of stones if any in grams"
    )
    interest_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        disabled=True,  # We'll set this programmatically based on scheme
        required=False,  # Add this line to make it not required for form submission
        help_text="Interest rate per year"
    )
    processing_fee = forms.DecimalField(
        max_digits=10,
        decimal_places=0,  # Changed to 0 decimal places for integer
        initial=0.01,  # Default 1%
        help_text="Processing fee percentage (default 1%)"
    )

    class Meta:
        model = Loan
        fields = [
            'customer', 'branch', 'scheme', 'principal_amount', 'processing_fee',
            'distribution_amount', 'interest_rate', 'issue_date', 'due_date',
            'grace_period_end', 'notes'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'grace_period_end': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'issue_date': 'Loan Date',
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set default dates for new loans
        if not self.instance.pk:  # Only for new loans
            today = timezone.now().date()
            self.fields['issue_date'].initial = today
            self.fields['due_date'].initial = today + timezone.timedelta(days=364)
            self.fields['grace_period_end'].initial = today + timezone.timedelta(days=369)  # due date + 5 days

        # Update principal_amount field to use integer values
        self.fields['principal_amount'] = forms.DecimalField(
            max_digits=10,
            decimal_places=0,
            help_text="₹ Loan amount in Rupees",
            widget=forms.NumberInput(attrs={
                'data-show-words': 'true',
                'step': '1'  # Ensure only whole numbers
            })
        )

        # Update processing_fee field to use integer values
        self.fields['processing_fee'] = forms.DecimalField(
            max_digits=10,
            decimal_places=0,
            initial=0,
            help_text="Processing fee amount in Rupees",
            widget=forms.NumberInput(attrs={
                'step': '1'  # Ensure only whole numbers
            })
        )

        # Configure customer field - filter by current branch if user has branch assigned
        if self.user and not self.user.is_superuser and self.user.branch:
            # Only show customers from the current branch
            self.fields['customer'].queryset = Customer.objects.filter(branch=self.user.branch).order_by('first_name', 'last_name')
        else:
            # Show all customers for superusers or users without a branch
            self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
            
        self.fields['customer'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"
        
        # Add data attribute to customer field to support setting branch based on customer's branch
        self.fields['customer'].widget.attrs['data-branch-update'] = 'true'

        # Define top priority ornament types and Tamil Nadu relevant gold ornament categories
        top_categories = [
            'Mixed Items',
            'Chain', 
            'Chain with Dollar', 
            'Chain without Dollar', 
            'Ring'
        ]

        # Create Mixed Items category first to ensure it exists
        mixed_items_category, created = Category.objects.get_or_create(
            name='Mixed Items',
            defaults={'description': 'Multiple types of gold ornaments'}
        )
        category_ids = [mixed_items_category.id]

        # Create other top categories
        for category_name in top_categories[1:]:  # Skip Mixed Items as it's already created
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Gold ornament: {category_name}'}
            )
            category_ids.append(category.id)

        # Then create or get the Tamil Nadu categories
        tamilnadu_categories = [
            'Thali (Mangalsutra)', 'Jimikki (Earrings)', 'Mothiram (Rings)', 
            'Valai (Bangles)', 'Malai (Necklaces)', 'Koppu (Studs)',
            'Odiyanam (Waist Belt)', 'Thodu (Ear Hoops)', 'Vanki (Armlet)',
            'Kolusu (Anklet)', 'Metti (Toe Ring)', 'Jadai Nagam (Hair Ornament)'
        ]

        for category_name in tamilnadu_categories:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Traditional Tamil Nadu gold ornament: {category_name}'}
            )
            category_ids.append(category.id)
        
        # Create the complete categories list in order
        all_categories = ['Mixed Items'] + top_categories[1:] + tamilnadu_categories
        
        # Order the categories to ensure Mixed Items appears first
        self.fields['item_category'].queryset = Category.objects.filter(id__in=category_ids).order_by(
            models.Case(
                *[models.When(name=name, then=pos) for pos, name in enumerate(all_categories)]
            )
        )
        
        # Always set Mixed Items as default
        self.fields['item_category'].initial = mixed_items_category
        self.fields['item_category'].label = 'Ornament Type'
        self.fields['item_category'].help_text = 'Select the type of gold ornament'

        # Filter available items
        available_items = Item.objects.exclude(
            loans__status='active'
        ).filter(status='available')

        # Add formset for multiple items
        from django.forms import formset_factory
        ItemFormSet = formset_factory(ItemForm, extra=1, can_delete=True)
        self.items_formset = ItemFormSet(prefix='items')

        # Set branch if user belongs to one
        if self.user and not self.user.is_superuser and self.user.branch:
            self.fields['branch'].initial = self.user.branch
            self.fields['branch'].widget = forms.HiddenInput()
            
        # If this is an existing loan, populate the item fields
        if self.instance and self.instance.pk:
            # Get the first loan item associated with this loan
            loan_item = self.instance.loanitem_set.first()
            if loan_item:
                # Populate all item-related fields from the existing data
                self.fields['item_name'].initial = loan_item.item.name
                self.fields['item_description'].initial = loan_item.item.description
                self.fields['item_category'].initial = loan_item.item.category
                
                # Convert Decimal to string for gold_karat field
                if loan_item.gold_karat:
                    # Convert to string and remove decimal part if it's .00
                    karat_str = str(loan_item.gold_karat)
                    if karat_str.endswith('.00'):
                        karat_str = karat_str.split('.')[0]
                    self.fields['gold_karat'].initial = karat_str
                
                self.fields['gross_weight'].initial = loan_item.gross_weight
                self.fields['net_weight'].initial = loan_item.net_weight
                self.fields['stone_weight'].initial = loan_item.stone_weight
                self.fields['market_price_22k'].initial = loan_item.market_price_22k

        # Set up crispy form layout
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-8'),
                Column('branch', css_class='col-md-4'),
            ),
            Row(
                Column('item_name', css_class='col-md-6'),
                Column('item_category', css_class='col-md-6'),
            ),
            Row(
                Column('market_price_22k', css_class='col-md-6'),
                Column('gold_karat', css_class='col-md-6'),
            ),
            Row(
                Column('gross_weight', css_class='col-md-4'),
                Column('stone_weight', css_class='col-md-4'),
                Column('net_weight', css_class='col-md-4'),
            ),
            Row(
                Column('item_description', css_class='col-md-6'),
            ),
            Row(
                Column('principal_amount', css_class='col-md-4'),
                Column('processing_fee', css_class='col-md-4'),
                Column('distribution_amount', css_class='col-md-4'),
            ),
            Row(
                Column('interest_rate', css_class='col-md-12'),
            ),
            Row(
                Column('issue_date', css_class='col-md-4'),
                Column('due_date', css_class='col-md-4'),
                Column('grace_period_end', css_class='col-md-4'),
            ),
        )

    def get_initial(self):
        initial = super().get_initial()
        initial['issue_date'] = timezone.now().date()
        
        # Auto-calculate due date and grace period end based on issue date
        today = timezone.now().date()
        
        # Both Standard and Flexible schemes use the same due date calculation: 364 days from issue date
        initial['due_date'] = today + timezone.timedelta(days=364)
            
        # Grace period is 5 days after due date for both schemes
        initial['grace_period_end'] = initial['due_date'] + timezone.timedelta(days=5)
            
        # Handle customer_id from request if available
        if hasattr(self, 'request') and hasattr(self.request, 'GET') and 'customer_id' in self.request.GET:
            initial['customer'] = self.request.GET['customer_id']
            
        return initial

    def clean(self):
        cleaned_data = super().clean()

        # Convert string inputs to Decimal and ensure they are integers
        try:
            if 'market_price_22k' in cleaned_data:
                cleaned_data['market_price_22k'] = Decimal(cleaned_data['market_price_22k'])
            if 'principal_amount' in cleaned_data:
                cleaned_data['principal_amount'] = Decimal(str(int(float(cleaned_data['principal_amount']))))
        except (ValueError, TypeError, InvalidOperation):
            raise ValidationError("Please enter valid whole numbers for principal amount")

        # Calculate processing fee and distribution amount
        principal_amount = cleaned_data.get('principal_amount')
        if principal_amount:
            # Processing fee is fixed at 1% of the principal amount
            processing_fee_amount = (principal_amount * Decimal('0.01')).to_integral_value()
            cleaned_data['processing_fee'] = processing_fee_amount
            cleaned_data['distribution_amount'] = principal_amount - processing_fee_amount

        # Check if at least one item is being added
        # For new item creation, check required fields
        required_fields = [
            'item_name', 'item_category', 'gold_karat',
            'gross_weight', 'net_weight', 'market_price_22k'
        ]
        missing_fields = [field for field in required_fields if not cleaned_data.get(field)]
        if missing_fields:
            for field in missing_fields:
                self.add_error(field, 'This field is required when creating a new item.')

        # Calculate allowed principal amount range if creating new item
        if all(cleaned_data.get(f) for f in ['market_price_22k', 'gold_karat', 'net_weight']):
            market_price = Decimal(str(cleaned_data['market_price_22k']))
            selected_karat = cleaned_data['gold_karat']
            net_weight = Decimal(str(cleaned_data['net_weight']))
            
            # Calculate value based on purity ratio
            purity_ratio = self.KARAT_PURITY[selected_karat] / self.KARAT_PURITY['22']
            gold_value = market_price * net_weight * purity_ratio
            max_principal = gold_value * Decimal('0.85')  # 85% of the gold value
            min_principal = gold_value * Decimal('0.50')  # 50% of the gold value
            principal = cleaned_data.get('principal_amount', 0)

            if principal > max_principal:
                self.add_error('principal_amount', 
                    f'Principal amount cannot exceed 85% of the gold value. Maximum allowed: ₹{max_principal:.2f}')
            elif principal < min_principal:
                self.add_error('principal_amount',
                    f'Principal amount must be at least 50% of the gold value. Minimum required: ₹{min_principal:.2f}')

        # Calculate total payable amount (principal + interest)
        interest_rate = cleaned_data.get('interest_rate')
        if principal_amount and interest_rate:
            # Interest rate is annual, convert to decimal
            annual_interest_rate = interest_rate / Decimal('100')
            interest_amount = principal_amount * annual_interest_rate
            cleaned_data['total_payable'] = principal_amount + interest_amount

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Calculate and set total_payable
        if instance.principal_amount and instance.interest_rate:
            # Convert interest_rate to Decimal if it's not already
            interest_rate = Decimal(str(instance.interest_rate))
            annual_interest_rate = interest_rate / Decimal('100')
            interest_amount = instance.principal_amount * annual_interest_rate
            instance.total_payable = instance.principal_amount + interest_amount

        # Set distribution_amount
        if instance.principal_amount and instance.processing_fee:
            # The processing_fee is already stored as an amount at this point, not a percentage
            instance.distribution_amount = instance.principal_amount - instance.processing_fee
        
        if commit:
            instance.save()
            
            # Check if this is an update or new loan
            if instance.pk and instance.loanitem_set.exists():
                # Update existing loan item information
                loan_item = instance.loanitem_set.first()
                if loan_item:
                    # Update item information
                    loan_item.item.name = self.cleaned_data['item_name']
                    loan_item.item.description = self.cleaned_data['item_description']
                    loan_item.item.category = self.cleaned_data['item_category']
                    loan_item.item.save()
                    
                    # Update loan item details
                    loan_item.gold_karat = self.cleaned_data['gold_karat']
                    loan_item.gross_weight = self.cleaned_data['gross_weight']
                    loan_item.net_weight = self.cleaned_data['net_weight']
                    loan_item.stone_weight = self.cleaned_data.get('stone_weight', 0)
                    loan_item.market_price_22k = self.cleaned_data['market_price_22k']
                    loan_item.save()
            else:
                # Create new item with gold details
                new_item = Item(
                    name=self.cleaned_data['item_name'],
                    description=self.cleaned_data['item_description'],
                    category=self.cleaned_data['item_category'],
                    status='pawned',  # Set status to pawned when used in loan
                    branch=instance.branch if instance.branch else self.user.branch,
                    created_by=self.user
                )
                new_item.save()
                
                # Create LoanItem with gold details
                loan_item = LoanItem(
                    loan=instance,
                    item=new_item,
                    gold_karat=self.cleaned_data['gold_karat'],
                    gross_weight=self.cleaned_data['gross_weight'],
                    net_weight=self.cleaned_data['net_weight'],
                    stone_weight=self.cleaned_data.get('stone_weight', 0),
                    market_price_22k=self.cleaned_data['market_price_22k']
                )
                loan_item.save()
            
            # Handle existing items from formset
            if hasattr(self, 'items_formset') and self.items_formset.is_valid():
                for item_form in self.items_formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                        item = item_form.save(commit=False)
                        item.status = 'pledged'
                        item.save()
                        LoanItem.objects.create(loan=instance, item=item)
        
        return instance

    def clean_scheme(self):
        scheme = self.cleaned_data.get('scheme')
        if not scheme:
            # If somehow scheme is empty, default to standard
            scheme = 'standard'
            
        interest_rate = None
        if scheme == 'standard':
            interest_rate = Decimal('12.00')
        elif scheme == 'flexible':
            interest_rate = Decimal('24.00')
        elif scheme == 'premium':
            interest_rate = Decimal('36.00')
        else:
            # If it's an invalid value, default to standard
            scheme = 'standard'
            interest_rate = Decimal('12.00')

        # Set interest rate in cleaned_data
        self.cleaned_data['interest_rate'] = interest_rate
        return scheme

class LoanExtensionForm(forms.ModelForm):
    EXTENSION_PERIOD_CHOICES = [
        (30, '30 Days (1 Month)'),
        (60, '60 Days (2 Months)'),
        (90, '90 Days (3 Months)'),
    ]
    
    extension_period = forms.ChoiceField(
        choices=EXTENSION_PERIOD_CHOICES,
        initial=30,
        label="Extension Period",
        help_text="Choose the period to extend the loan by"
    )
    
    extension_fee = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0.00,
        label="Extension Fee",
        help_text="Fee charged for extending the loan"
    )
    
    new_grace_period_end = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="New Grace Period End Date",
        help_text="The new grace period end date after extension"
    )

    class Meta:
        model = LoanExtension
        fields = ['extension_date', 'new_due_date', 'fee', 'notes']
        widgets = {
            'extension_date': forms.DateInput(attrs={'type': 'date'}),
            'new_due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'extension_date': 'Extension Date',
            'new_due_date': 'New Due Date',
            'fee': 'Extension Fee',
            'notes': 'Notes'
        }

    def __init__(self, *args, **kwargs):
        self.loan = kwargs.pop('loan', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Setup form helper for crispy forms
        self.helper = FormHelper()
        self.helper.form_tag = False
        
        # Set default dates if loan is provided
        if self.loan:
            # Map fee to extension_fee for template
            self.fields['extension_fee'] = self.fields.pop('fee')
            
            # Set default values
            self.initial['extension_date'] = timezone.now().date()
            self.initial['new_due_date'] = self.loan.due_date + timezone.timedelta(days=30)
            self.initial['new_grace_period_end'] = self.loan.due_date + timezone.timedelta(days=35)  # 5 days grace period
            
            # Calculate default extension fee (0.5% of principal amount)
            self.initial['extension_fee'] = (self.loan.principal_amount * Decimal('0.005')).quantize(Decimal('0.01'))
            
    def clean(self):
        cleaned_data = super().clean()
        extension_period = int(cleaned_data.get('extension_period', 30))
        extension_date = cleaned_data.get('extension_date')
        
        if not self.loan:
            raise ValidationError("No loan specified for extension")
            
        # Check if loan is active
        if self.loan.status != 'active':
            raise ValidationError(f"Cannot extend a loan with status '{self.loan.status}'. Only active loans can be extended.")
        
        # Check if loan is not overdue by more than 30 days
        today = timezone.now().date()
        if self.loan.due_date < today:
            days_overdue = (today - self.loan.due_date).days
            if days_overdue > 30:
                raise ValidationError(f"Loan is overdue by {days_overdue} days. Extensions are not allowed for loans overdue by more than 30 days.")
        
        # Check if this would exceed the maximum of 3 extensions
        existing_extensions_count = self.loan.extensions.count()
        if existing_extensions_count >= 3:
            raise ValidationError(f"Maximum of 3 extensions allowed per loan. This loan already has {existing_extensions_count} extensions.")
        
        # Calculate new due date based on extension period
        if extension_date and self.loan:
            new_due_date = self.loan.due_date + timezone.timedelta(days=extension_period)
            cleaned_data['new_due_date'] = new_due_date
            
            # Calculate new grace period end (due date + 5 days)
            new_grace_period_end = new_due_date + timezone.timedelta(days=5)
            cleaned_data['new_grace_period_end'] = new_grace_period_end
            
        # Validate extension fee (must be at least 0.5% of principal)
        extension_fee = cleaned_data.get('extension_fee')
        min_fee = (self.loan.principal_amount * Decimal('0.005')).quantize(Decimal('0.01'))
        
        if extension_fee and extension_fee < min_fee:
            self.add_error('extension_fee', f"Extension fee must be at least 0.5% of the principal amount (₹{min_fee}).")
        
        # Map extension_fee back to fee for model
        if 'extension_fee' in cleaned_data:
            cleaned_data['fee'] = cleaned_data.pop('extension_fee')
            
        # Set previous due date
        cleaned_data['previous_due_date'] = self.loan.due_date
        
        return cleaned_data
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set loan and previous due date
        instance.loan = self.loan
        instance.previous_due_date = self.loan.due_date
        
        # Set approved_by to current user
        if self.user:
            instance.approved_by = self.user
            
        if commit:
            instance.save()
            
            # Update the loan with new due date and status
            self.loan.due_date = instance.new_due_date
            self.loan.grace_period_end = instance.new_due_date + timezone.timedelta(days=5)
            self.loan.status = 'extended'
            self.loan.save()
            
        return instance

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'customer', 'item', 'selling_price', 
            'tax', 'discount', 'payment_method'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configure customer field
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
        self.fields['customer'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"
        
        # Filter available items
        available_items = Item.objects.filter(status='available')
        self.fields['item'].queryset = available_items

        # Setup form helper for crispy forms
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-6'),
                Column('item', css_class='col-md-6'),
            ),
            Row(
                Column('selling_price', css_class='col-md-4'),
                Column('tax', css_class='col-md-4'),
                Column('discount', css_class='col-md-4'),
            ),
            Row(
                Column('payment_method', css_class='col-12'),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        selling_price = cleaned_data.get('selling_price')
        tax = cleaned_data.get('tax', 0)
        discount = cleaned_data.get('discount', 0)

        if selling_price and (selling_price + tax - discount) <= 0:
            raise ValidationError("Total amount must be greater than zero")

        return cleaned_data