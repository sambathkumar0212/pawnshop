from django import forms
from django.db.models import Q
from .models import Scheme, SchemeNotification
from branches.models import Branch
from accounts.models import CustomUser

class SchemeForm(forms.ModelForm):
    """Form for creating and editing loan schemes"""
    
    class Meta:
        model = Scheme
        fields = [
            'name', 'code', 'scheme_type', 'description', 
            'interest_rate', 'duration_days', 'no_interest_period_days', 
            'minimum_period_days', 'processing_fee_percentage', 
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'scheme_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'no_interest_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimum_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'processing_fee_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'interest_rate': 'Annual interest rate as a percentage (e.g., 12.00 for 12%)',
            'duration_days': 'Standard duration of the loan in days (e.g., 90 for 3 months)',
            'no_interest_period_days': 'Number of days without interest if repaid early (0 if not applicable)',
            'minimum_period_days': 'Minimum period before loan can be closed (0 for no minimum)',
            'processing_fee_percentage': 'Processing fee as a percentage of loan amount (e.g., 1.00 for 1%)',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Branch managers can only create/edit schemes for their branch
        if self.user and not self.user.is_superuser:
            if hasattr(self.user, 'branch') and self.user.branch:
                # Set branch field to the user's branch and make it readonly
                self.instance.branch = self.user.branch
            else:
                raise forms.ValidationError("You must be associated with a branch to manage schemes.")
    
    def clean_code(self):
        """Ensure code has no spaces and is uppercase"""
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper().replace(' ', '_')
        return code

class SchemeNotificationForm(forms.ModelForm):
    """Form for creating and updating scheme notifications"""
    
    class Meta:
        model = SchemeNotification
        fields = ['title', 'message', 'scheme', 'is_active', 'priority', 
                  'all_branches', 'branches', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        # Get the user from kwargs to filter schemes by permission
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter schemes based on user permissions
        if self.user:
            if self.user.is_superuser:
                # Superusers can see all schemes
                self.fields['scheme'].queryset = Scheme.objects.filter(is_active=True)
            else:
                # Branch managers can only see their branch's schemes or global ones
                self.fields['scheme'].queryset = Scheme.objects.filter(
                    Q(branch=self.user.branch) | Q(branch__isnull=True),
                    is_active=True
                )
                # Branch managers can only select their own branch
                self.fields['branches'].queryset = Branch.objects.filter(id=self.user.branch.id)
                
                # If not a superuser, all_branches can only be False
                if not self.user.has_perm('content_manager.can_create_global_notifications'):
                    self.fields['all_branches'].widget = forms.HiddenInput()
                    self.fields['all_branches'].initial = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        all_branches = cleaned_data.get('all_branches')
        branches = cleaned_data.get('branches')
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        # Ensure at least one branch is selected if not all_branches
        if not all_branches and not branches:
            raise forms.ValidationError("You must select at least one branch if 'All Branches' is not checked.")
        
        return cleaned_data