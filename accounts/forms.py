from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import CustomUser, Role, Customer

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