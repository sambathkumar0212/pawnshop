from django import forms
from django.core.exceptions import ValidationError
from .models import Loan, Payment, LoanExtension, Sale, LoanItem
from inventory.models import Item, Category
from inventory.forms import ItemForm
from accounts.models import Customer
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div
from decimal import Decimal

class LoanForm(forms.ModelForm):
    distribution_amount = forms.DecimalField(
        disabled=True,
        required=False,
        max_digits=10,
        decimal_places=2,
        help_text="Amount to be distributed after processing fee"
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
        help_text='Enter the name or description of the gold item'
    )
    item_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Detailed description of the item including any distinguishing marks'
    )
    item_category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.filter(name__icontains='Gold'),
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
        initial=12.00,  # Set default to 12%
        help_text="Interest rate per year (1% per month)"
    )
    processing_fee = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0.01,  # Default 1%
        help_text="Processing fee percentage (default 1%)"
    )

    class Meta:
        model = Loan
        fields = [
            'customer', 'principal_amount', 'processing_fee', 'interest_rate',
            'issue_date', 'due_date', 'grace_period_end', 'branch'
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'grace_period_end': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configure customer field
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
        self.fields['customer'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"

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
                Column('gross_weight', css_class='col-md-6'),
                Column('stone_weight', css_class='col-md-6'),
            ),
            Row(
                Column('net_weight', css_class='col-md-12'),
            ),
            Row(
                Column('item_description', css_class='col-12'),
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

    def clean(self):
        cleaned_data = super().clean()

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

        # Calculate processing fee amount and distribution amount
        principal_amount = cleaned_data.get('principal_amount')
        processing_fee_percentage = cleaned_data.get('processing_fee')
        interest_rate = cleaned_data.get('interest_rate')

        if principal_amount and processing_fee_percentage:
            # Convert percentage to decimal for calculation
            processing_fee_amount = principal_amount * (processing_fee_percentage / Decimal('100'))
            cleaned_data['processing_fee'] = processing_fee_amount
            cleaned_data['distribution_amount'] = principal_amount - processing_fee_amount

        # Calculate total payable amount (principal + interest)
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
            annual_interest_rate = instance.interest_rate / Decimal('100')
            interest_amount = instance.principal_amount * annual_interest_rate
            instance.total_payable = instance.principal_amount + interest_amount

        # Calculate and set distribution_amount
        if instance.principal_amount and instance.processing_fee:
            # Convert percentage to decimal for calculation (since processing_fee is stored as percentage)
            instance.distribution_amount = instance.principal_amount - instance.processing_fee
        
        if commit:
            instance.save()
            
            # Create new item with gold details
            new_item = Item(
                name=self.cleaned_data['item_name'],
                description=self.cleaned_data['item_description'],
                category=self.cleaned_data['item_category'],
                status='pledged',  # Set status to pledged when used in loan
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