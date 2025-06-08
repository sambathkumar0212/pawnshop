from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import CustomUser, Role, Customer
from django.contrib.auth.models import Group
from branches.models import Branch

class UserFaceCreateForm(forms.ModelForm):
    """Form for creating a new user with face authentication"""
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    face_image = forms.CharField(widget=forms.HiddenInput(), required=False)
    enable_face_auth = forms.BooleanField(
        initial=True, 
        required=False,
        label="Enable Face Authentication",
        help_text="Allow this user to login using facial recognition"
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'password', 'confirm_password', 'first_name', 
            'last_name', 'email', 'phone', 'role', 'branch', 
            'enable_face_auth', 'face_image'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match")
        
        enable_face_auth = cleaned_data.get("enable_face_auth")
        face_image = cleaned_data.get("face_image")
        
        if enable_face_auth and not face_image:
            self.add_error('face_image', "Face image is required if face authentication is enabled")
            
        return cleaned_data

class UserUpdateForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        empty_label="Select a role"
    )
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'branch', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Set initial role
            self.fields['role'].initial = self.instance.role
            # Set initial branch
            self.fields['branch'].initial = self.instance.branch

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Handle role assignment
            if self.cleaned_data.get('role'):
                user.role = self.cleaned_data['role']
                user.save()
                # Update user permissions based on role
                user.user_permissions.set(self.cleaned_data['role'].permissions.all())
        return user