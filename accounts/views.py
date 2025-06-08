from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django import forms
from django.http import JsonResponse
from django.contrib.auth import login
from biometrics.models import FaceEnrollment, FaceAuthLog, CustomerFaceEnrollment
import json
import base64
import os
from django.conf import settings
import datetime

from .models import CustomUser, Role, UserActivity, Customer
from .forms import UserFaceCreateForm, UserUpdateForm
from branches.models import Branch
from inventory.models import Item
from transactions.models import Loan, Sale


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    """Custom logout view that accepts both GET and POST requests"""
    http_method_names = ['get', 'post']  # Allow both GET and POST methods


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        
        # Determine if user is branch-specific or has global access
        if user.is_superuser or not user.branch:
            branches = Branch.objects.filter(is_active=True)
            branch_filter = Q()
        else:
            branches = Branch.objects.filter(id=user.branch.id)
            branch_filter = Q(branch=user.branch)
        
        # Get inventory statistics
        context['total_items'] = Item.objects.filter(branch_filter).count()
        context['available_items'] = Item.objects.filter(branch_filter, status='available').count()
        context['pawned_items'] = Item.objects.filter(branch_filter, status='pawned').count()
        
        # Get loan statistics
        context['active_loans'] = Loan.objects.filter(branch_filter, status='active').count()
        context['overdue_loans'] = Loan.objects.filter(
            branch_filter, status='active', due_date__lt=today
        ).count()
        context['loans_due_today'] = Loan.objects.filter(
            branch_filter, status='active', due_date=today
        ).count()
        
        # Get sales statistics
        context['total_sales'] = Sale.objects.filter(
            branch_filter, status='completed', sale_date=today
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Get recent loans with all related data
        context['recent_loans'] = Loan.objects.filter(
            branch_filter
        ).select_related(
            'customer'
        ).prefetch_related(
            'loanitem_set',
            'loanitem_set__item'
        ).order_by('-created_at')[:5]
        
        context['recent_sales'] = Sale.objects.filter(
            branch_filter
        ).select_related('item').order_by('-created_at')[:5]
        
        # Branch information
        context['branches'] = branches
        context['branch_count'] = branches.count()
        
        # Customer statistics
        context['customer_count'] = Customer.objects.filter().count()
        context['new_customers_today'] = Customer.objects.filter(created_at__date=today).count()
        
        return context


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    permission_required = 'accounts.view_customuser'


class UserDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    permission_required = 'accounts.view_customuser'


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = CustomUser
    template_name = 'accounts/user_face_form.html'
    form_class = UserFaceCreateForm
    success_url = reverse_lazy('user_list')
    permission_required = 'accounts.add_customuser'
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        
        # Handle face enrollment if enabled
        enable_face_auth = form.cleaned_data.get('enable_face_auth')
        face_image_data = form.cleaned_data.get('face_image')
        
        if enable_face_auth and face_image_data:
            try:
                # Process and save the face image
                import base64
                import io
                from django.core.files.base import ContentFile
                from PIL import Image
                import numpy as np
                
                # Extract the base64 encoded image data (remove the data:image/jpeg;base64, prefix)
                image_data = face_image_data.split(',')[1]
                image_binary = base64.b64decode(image_data)
                
                # Create a file-like object
                image_file = ContentFile(image_binary)
                
                # In a production system, you would:
                # 1. Process the image to extract facial features/encoding
                # 2. Save the encoding as binary data
                # For simplicity, we'll just save the image and use a placeholder for encoding
                
                # Create face enrollment
                face_enrollment = FaceEnrollment(user=user)
                
                # Save the image file
                image_name = f"face_{user.username}.jpg"
                face_enrollment.face_image.save(image_name, image_file, save=False)
                
                # In a real implementation, you would compute the face encoding here
                # For now, we'll use a placeholder
                placeholder_encoding = b"placeholder_face_encoding"  # Replace with actual encoding in production
                face_enrollment.face_encoding = placeholder_encoding
                
                face_enrollment.save()
                
                messages.success(self.request, f"User {user.username} was created successfully with face authentication.")
            except Exception as e:
                messages.error(self.request, f"Error processing face data: {str(e)}")
        else:
            messages.success(self.request, f"User {user.username} was created successfully.")
        
        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='user_created',
            description=f'Created user: {user.username}',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'accounts/user_form.html'
    form_class = UserUpdateForm
    success_url = reverse_lazy('user_list')
    permission_required = 'accounts.change_customuser'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Add any additional context needed for the form
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.username} was updated successfully.')
        
        # Log activity
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='user_updated',
            description=f'Updated user: {self.object.username}',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        return response


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'accounts/user_confirm_delete.html'
    context_object_name = 'user_obj'
    success_url = reverse_lazy('user_list')
    permission_required = 'accounts.delete_customuser'
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(request, f'User {user.username} was deleted successfully.')
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='user_deleted',
            description=f'Deleted user: {user.username}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return super().delete(request, *args, **kwargs)


class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'
    permission_required = 'accounts.view_role'


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'description', 'permissions']
    success_url = reverse_lazy('role_list')
    permission_required = 'accounts.add_role'


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'description', 'permissions']
    success_url = reverse_lazy('role_list')
    permission_required = 'accounts.change_role'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object:
            # Initialize permissions with existing values
            form.fields['permissions'].initial = [p.pk for p in self.object.permissions.all()]
        return form


class RoleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Role
    template_name = 'accounts/role_confirm_delete.html'
    context_object_name = 'role'
    success_url = reverse_lazy('role_list')
    permission_required = 'accounts.delete_role'


class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'accounts/profile.html'
    context_object_name = 'user_obj'
    
    def get_object(self):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'accounts/profile_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone']
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your profile was updated successfully.')
        return response


class FaceEnrollmentView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/face_enrollment.html'


class FaceLoginView(View):
    """View for facial recognition login"""
    def get(self, request):
        return render(request, 'accounts/face_login.html')
    
    def post(self, request):
        
        # Extract the face image data from the POST request
        face_image = request.POST.get('face_image')
        
        if face_image:
            # In a real implementation, you would:
            # 1. Process the image data
            # 2. Compare it against enrolled face data
            # 3. Authenticate the user if match found
            
            # For this demo, we'll simulate a successful authentication
            # In production, replace this with actual face recognition logic
            
            # Log the authentication attempt
            auth_log = FaceAuthLog(
                timestamp=datetime.datetime.now(),
                ip_address=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT'),
                success=True,
                confidence=0.85  # This would be the actual confidence score from your FR system
            )
            
            # For demo purposes, authenticate as the first admin user
            # In production, this would be the user matched by facial recognition
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.filter(is_staff=True).first()
                
                if user:
                    # Log which user was authenticated
                    auth_log.user = user
                    auth_log.save()
                    
                    # Log in the user
                    login(request, user)
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Authentication successful',
                        'redirect': '/dashboard/'
                    })
                else:
                    auth_log.success = False
                    auth_log.save()
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'No matching user found'
                    })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                })
        
        return JsonResponse({
            'status': 'error',
            'message': 'No image data received'
        })


# Customer views
class CustomerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Customer
    template_name = 'accounts/customer_list.html'
    context_object_name = 'customers'
    permission_required = 'accounts.view_customer'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_term = self.request.GET.get('search', '')
        
        if search_term:
            queryset = queryset.filter(
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone__icontains=search_term)
            )
        
        return queryset


class CustomerDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Customer
    template_name = 'accounts/customer_detail.html'
    context_object_name = 'customer'
    permission_required = 'accounts.view_customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Get related items and loans
        if hasattr(customer, 'items'):
            context['items'] = customer.items.all()
        
        if hasattr(customer, 'loans'):
            context['loans'] = customer.loans.all()
            context['active_loans'] = customer.loans.filter(status='active')
        
        return context


class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Customer
    template_name = 'accounts/customer_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 
              'state', 'zip_code', 'id_type', 'id_number', 'id_image', 'notes']
    success_url = reverse_lazy('customer_list')
    permission_required = 'accounts.add_customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add fieldset information for better UI organization
        context['fieldsets'] = [
            {'title': 'Personal Information', 'fields': ['first_name', 'last_name', 'email', 'phone']},
            {'title': 'Address', 'fields': ['address', 'city', 'state', 'zip_code']},
            {'title': 'Identification', 'fields': ['id_type', 'id_number', 'id_image']},
            {'title': 'Additional Information', 'fields': ['notes']}
        ]
        context['show_camera_capture'] = True
        context['show_profile_photo'] = True
        context['page_title'] = 'Add New Customer'
        context['submit_text'] = 'Create Customer'
        # Add camera configuration
        context['camera_config'] = {
            'width': 640,
            'height': 480,
            'image_format': 'jpeg',
            'jpeg_quality': 90,
            'target_field': 'id_image',
            'camera_id_field': 'camera_image_data'
        }
        # Add debug flag
        context['debug_mode'] = settings.DEBUG
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Improve form widgets
        form.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'First Name'})
        form.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Last Name'})
        form.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email Address'})
        form.fields['phone'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Phone Number', 'type': 'tel'})
        form.fields['address'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Street Address'})
        form.fields['city'].widget.attrs.update({'class': 'form-control', 'placeholder': 'City'})
        form.fields['state'].widget.attrs.update({'class': 'form-control', 'placeholder': 'State/Province'})
        form.fields['zip_code'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Zip/Postal Code'})
        form.fields['notes'].widget.attrs.update({'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes about the customer'})
        
        # Make ID image optional in the form since we're using camera capture
        form.fields['id_image'].required = False
        
        # Add hidden fields for camera data
        form.fields['camera_image_data'] = forms.CharField(required=False, widget=forms.HiddenInput())
        form.fields['profile_photo_data'] = forms.CharField(required=False, widget=forms.HiddenInput())
        
        return form
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Log received form data for debugging (only field names for privacy)
        if settings.DEBUG:
            print(f"Form data received: {list(self.request.POST.keys())}")
            print(f"Files received: {list(self.request.FILES.keys())}")
        
        # Process camera image if available
        camera_image_data = self.request.POST.get('camera_image_data')
        if camera_image_data and camera_image_data.startswith('data:image/'):
            try:
                # Extract the base64 encoded image data
                format, imgstr = camera_image_data.split(';base64,')
                ext = format.split('/')[-1]
                
                # Decode base64 image data
                image_data = base64.b64decode(imgstr)
                
                # Create a ContentFile to save to the ImageField
                from django.core.files.base import ContentFile
                image_file = ContentFile(image_data, name=f"id_{form.instance.first_name}_{form.instance.last_name}.{ext}")
                
                # Assign to the form instance
                form.instance.id_image = image_file
                
                # Log success message
                messages.success(self.request, "ID image captured successfully.")
                
                if settings.DEBUG:
                    print("Successfully processed camera image")
            except Exception as e:
                messages.error(self.request, f"Error processing ID image: {str(e)}")
                if settings.DEBUG:
                    print(f"Error processing camera image: {str(e)}")
        else:
            if settings.DEBUG and 'camera_image_data' in self.request.POST:
                print("Camera image data was received but in incorrect format")
            elif settings.DEBUG:
                print("No camera image data was received")
        
        # Process profile photo if available
        profile_photo_data = self.request.POST.get('profile_photo_data')
        if profile_photo_data and profile_photo_data.startswith('data:image/'):
            try:
                # Store the base64 data directly in the profile_photo field
                form.instance.profile_photo = profile_photo_data
            except Exception as e:
                messages.error(self.request, f"Error processing profile photo: {str(e)}")
        
        messages.success(self.request, f'Customer {form.instance.first_name} {form.instance.last_name} was created successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Add more helpful error messages
        messages.error(self.request, 'Please correct the errors below.')
        for field, errors in form.errors.items():
            for error in errors:
                field_name = form.fields[field].label or field
                messages.error(self.request, f"{field_name}: {error}")
        return super().form_invalid(form)


class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Customer
    template_name = 'accounts/customer_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 
              'state', 'zip_code', 'id_type', 'id_number', 'id_image', 'notes']
    permission_required = 'accounts.change_customer'
    
    def get_success_url(self):
        return reverse_lazy('customer_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Process camera image if available
        camera_image_data = self.request.POST.get('camera_image_data')
        if camera_image_data and camera_image_data.startswith('data:image/'):
            try:
                # Extract the base64 encoded image data
                format, imgstr = camera_image_data.split(';base64,')
                ext = format.split('/')[-1]
                
                # Decode base64 image data
                image_data = base64.b64decode(imgstr)
                
                # Create a ContentFile to save to the ImageField
                from django.core.files.base import ContentFile
                image_file = ContentFile(image_data, name=f"id_{form.instance.first_name}_{form.instance.last_name}.{ext}")
                
                # Assign to the form instance
                form.instance.id_image = image_file
            except Exception as e:
                messages.error(self.request, f"Error processing ID image: {str(e)}")

        # Process profile photo if available
        profile_photo_data = self.request.POST.get('profile_photo_data')
        if profile_photo_data and profile_photo_data.startswith('data:image/'):
            try:
                # Store the base64 data directly in the profile_photo field
                form.instance.profile_photo = profile_photo_data
            except Exception as e:
                messages.error(self.request, f"Error processing profile photo: {str(e)}")
        
        messages.success(self.request, f'Customer {form.instance.first_name} {form.instance.last_name} was updated successfully.')
        return super().form_valid(form)


class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Customer
    template_name = 'accounts/customer_confirm_delete.html'
    context_object_name = 'customer'
    success_url = reverse_lazy('customer_list')
    permission_required = 'accounts.delete_customer'
    
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        messages.success(request, f'Customer {customer.full_name} was deleted successfully.')
        return super().delete(request, *args, **kwargs)
