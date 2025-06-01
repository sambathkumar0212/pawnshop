from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django import forms

from .models import CustomUser, Role, UserActivity, Customer
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
            # Get global stats
            branches = Branch.objects.filter(is_active=True)
            branch_filter = Q()
        else:
            # Get branch-specific stats
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
        
        context['recent_sales'] = Sale.objects.filter(
            branch_filter
        ).order_by('-created_at')[:5]
        
        context['recent_loans'] = Loan.objects.filter(
            branch_filter
        ).order_by('-created_at')[:5]
        
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
    template_name = 'accounts/user_form.html'
    fields = ['username', 'password', 'first_name', 'last_name', 'email', 'phone', 'role', 'branch']
    success_url = reverse_lazy('user_list')
    permission_required = 'accounts.add_customuser'
    
    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        messages.success(self.request, f'User {user.username} was created successfully.')
        
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
    fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'branch', 'is_active']
    success_url = reverse_lazy('user_list')
    permission_required = 'accounts.change_customuser'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'] = forms.CharField(
            disabled=True,
            initial=self.object.username,
            help_text='Username cannot be changed after creation'
        )
        # Ensure role and branch fields are initialized with current values
        if self.object.role:
            form.fields['role'].initial = self.object.role.id
        if self.object.branch:
            form.fields['branch'].initial = self.object.branch.id
        return form
    
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


class RoleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'description', 'permissions']
    success_url = reverse_lazy('role_list')
    permission_required = 'accounts.add_role'


class RoleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
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


class FaceLoginView(TemplateView):
    template_name = 'accounts/face_login.html'


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
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Customer was created successfully.')
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Customer
    template_name = 'accounts/customer_form.html'
    fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 
              'state', 'zip_code', 'id_type', 'id_number', 'id_image', 'notes']
    permission_required = 'accounts.change_customer'
    
    def get_success_url(self):
        return reverse_lazy('customer_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer was updated successfully.')
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
