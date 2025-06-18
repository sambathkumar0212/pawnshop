from django import forms
from .models import Scheme
from django.utils import timezone

class SchemeForm(forms.ModelForm):
    """Form for creating and updating schemes"""
    
    # Fields for basic additional conditions
    no_interest_period_days = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter number of days'
        }),
        help_text="Number of days without interest if repaid early"
    )
    
    late_fee_percentage = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'e.g., 2.00'
        }),
        help_text="Late fee percentage (if applicable)"
    )
    
    processing_fee_percentage = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'e.g., 1.00'
        }),
        help_text="Processing fee percentage (if applicable)"
    )
    
    early_payment_discount = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Check if early payment discount is available"
    )
    
    grace_period_days = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter number of days'
        }),
        help_text="Number of days after due date before late fees apply"
    )
    
    prepayment_penalty_percentage = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'e.g., 1.00'
        }),
        help_text="Penalty percentage for early repayment (if applicable)"
    )
    
    # Field for any custom additional conditions
    custom_conditions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter any custom conditions, one per line in Key: Value format'
        }),
        help_text="Any custom conditions not covered by the fields above"
    )
    
    class Meta:
        model = Scheme
        fields = [
            'name', 'description', 'interest_rate', 'loan_duration', 
            'minimum_amount', 'maximum_amount', 'start_date', 'end_date', 
            'status', 'branch'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maximum_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make branch field optional
        self.fields['branch'].required = False
        
        # If there's a user and they have a branch, limit choices
        if user and not user.is_superuser:
            if user.branch:
                if user.role and user.role.name.lower() == 'branch manager':
                    self.fields['branch'].initial = user.branch
                    self.fields['branch'].widget.attrs['readonly'] = True
                    self.fields['branch'].disabled = True
                elif user.role and user.role.name.lower() == 'regional manager':
                    managed_branches = user.managed_branches.all()
                    if managed_branches.exists():
                        self.fields['branch'].queryset = managed_branches
        
        # If editing an existing scheme with additional conditions, populate the fields
        if self.instance.pk and self.instance.additional_conditions:
            conditions = self.instance.additional_conditions
            
            # Set values for specific fields
            self.fields['no_interest_period_days'].initial = conditions.get('no_interest_period_days')
            self.fields['late_fee_percentage'].initial = conditions.get('late_fee_percentage')
            self.fields['processing_fee_percentage'].initial = conditions.get('processing_fee_percentage')
            self.fields['early_payment_discount'].initial = conditions.get('early_payment_discount', False)
            self.fields['grace_period_days'].initial = conditions.get('grace_period_days')
            self.fields['prepayment_penalty_percentage'].initial = conditions.get('prepayment_penalty_percentage')
            
            # Collect any custom conditions
            custom_conditions = []
            standard_fields = [
                'no_interest_period_days', 'late_fee_percentage', 
                'processing_fee_percentage', 'early_payment_discount',
                'grace_period_days', 'prepayment_penalty_percentage'
            ]
            
            for key, value in conditions.items():
                if key not in standard_fields:
                    if isinstance(value, bool):
                        value = "Yes" if value else "No"
                    custom_conditions.append(f"{key.replace('_', ' ').title()}: {value}")
            
            if custom_conditions:
                self.fields['custom_conditions'].initial = "\n".join(custom_conditions)
    
    def clean(self):
        from decimal import Decimal
        cleaned_data = super().clean()
        
        # Build the additional conditions dictionary
        conditions_dict = {}
        
        # Add specific fields if they have values
        fields_to_check = [
            'no_interest_period_days', 'late_fee_percentage', 
            'processing_fee_percentage', 'early_payment_discount',
            'grace_period_days', 'prepayment_penalty_percentage'
        ]
        
        for field in fields_to_check:
            value = cleaned_data.get(field)
            if value is not None and value != '':
                # Convert Decimal to float for JSON serialization
                if isinstance(value, Decimal):
                    conditions_dict[field] = float(value)
                elif isinstance(value, bool):
                    conditions_dict[field] = value
                elif isinstance(value, (int, float)):
                    conditions_dict[field] = float(value) if isinstance(value, float) or '.' in str(value) else int(value)
        
        # Process custom conditions
        custom_conditions = cleaned_data.get('custom_conditions')
        if custom_conditions:
            for line in custom_conditions.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    # Try to convert value to appropriate type
                    if value.replace('.', '', 1).isdigit():
                        conditions_dict[key] = float(value) if '.' in value else int(value)
                    elif value.lower() in ['yes', 'true']:
                        conditions_dict[key] = True
                    elif value.lower() in ['no', 'false']:
                        conditions_dict[key] = False
                    else:
                        conditions_dict[key] = value
                elif line.strip():
                    conditions_dict[line.strip().lower().replace(' ', '_')] = True
        
        cleaned_data['additional_conditions'] = conditions_dict if conditions_dict else None
        return cleaned_data