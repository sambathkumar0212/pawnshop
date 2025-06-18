from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.utils import timezone
import decimal
from decimal import Decimal

from .models import Scheme, SchemeAuditLog
from .forms import SchemeForm
from accounts.models import UserActivity


class SchemeMixin(LoginRequiredMixin):
    """Base mixin for scheme views with common functionality"""
    
    def get_queryset(self):
        """Filter schemes based on user permissions"""
        user = self.request.user
        base_queryset = super().get_queryset()
        
        # Superusers can see all schemes
        if user.is_superuser:
            return base_queryset
        
        # Check if user has permission to view all schemes
        if user.has_perm('schemes.view_all_schemes'):
            return base_queryset
        
        # Regional managers can see schemes from branches they manage
        if user.role and user.role.name.lower() == 'regional manager':
            if hasattr(user, 'managed_branches'):
                managed_branches = user.managed_branches.all()
                return base_queryset.filter(
                    Q(branch__in=managed_branches) | Q(branch__isnull=True)
                )
        
        # Branch managers can only see schemes for their branch and global schemes
        if user.branch:
            return base_queryset.filter(
                Q(branch=user.branch) | Q(branch__isnull=True)
            )
        
        # Default: only show global schemes if the user doesn't have a branch
        return base_queryset.filter(branch__isnull=True)
    
    def log_user_activity(self, action_type, description):
        """Log user activity for auditing purposes"""
        UserActivity.objects.create(
            user=self.request.user,
            activity_type=action_type,
            description=description,
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class SchemeListView(SchemeMixin, PermissionRequiredMixin, ListView):
    model = Scheme
    template_name = 'schemes/scheme_list.html'
    context_object_name = 'schemes'
    permission_required = 'schemes.view_scheme'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Handle search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Handle status filtering
        status_filter = self.request.GET.get('status', '')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Handle branch filtering
        branch_filter = self.request.GET.get('branch', '')
        if branch_filter:
            if branch_filter == 'global':
                queryset = queryset.filter(branch__isnull=True)
            else:
                try:
                    branch_id = int(branch_filter)
                    queryset = queryset.filter(branch_id=branch_id)
                except ValueError:
                    pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['branch_filter'] = self.request.GET.get('branch', '')
        
        # Add status choices for filtering
        context['status_choices'] = Scheme.STATUS_CHOICES
        
        # Get available branches for filtering
        user = self.request.user
        if user.is_superuser:
            from branches.models import Branch
            context['available_branches'] = Branch.objects.filter(is_active=True)
        elif user.role and user.role.name.lower() == 'regional manager':
            if hasattr(user, 'managed_branches'):
                context['available_branches'] = user.managed_branches.filter(is_active=True)
        elif user.branch:
            context['available_branches'] = [user.branch]
        
        # Log view action
        self.log_user_activity('scheme_list_viewed', 'Viewed schemes list')
        
        return context


class SchemeDetailView(SchemeMixin, PermissionRequiredMixin, DetailView):
    model = Scheme
    template_name = 'schemes/scheme_detail.html'
    context_object_name = 'scheme'
    permission_required = 'schemes.view_scheme'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scheme = self.get_object()
        user = self.request.user
        
        # Add user information to context
        context['username'] = user.username
        
        # Add audit logs
        context['audit_logs'] = scheme.audit_logs.all().order_by('-timestamp')[:10]
        
        # Check if user can edit or delete
        can_edit = False
        can_delete = False
        
        if user.is_superuser:
            can_edit = True
            can_delete = True
        elif user.has_perm('schemes.change_scheme'):
            # Branch managers can edit schemes for their branch
            if user.role and user.role.name.lower() == 'branch manager':
                if user.branch and scheme.branch == user.branch:
                    can_edit = True
            # Regional managers can edit schemes for branches they manage
            elif user.role and user.role.name.lower() == 'regional manager':
                if scheme.branch and hasattr(user, 'managed_branches'):
                    if scheme.branch in user.managed_branches.all():
                        can_edit = True
                # Regional managers can also manage global schemes if they have permission
                elif scheme.branch is None and user.has_perm('schemes.manage_global_schemes'):
                    can_edit = True
        
        # Delete permission follows similar rules as edit
        if can_edit and user.has_perm('schemes.delete_scheme'):
            can_delete = True
        
        context['can_edit'] = can_edit
        context['can_delete'] = can_delete
        
        # Log view action
        self.log_user_activity('scheme_viewed', f'Viewed scheme: {scheme.name}')
        
        return context


class SchemeCreateView(SchemeMixin, PermissionRequiredMixin, CreateView):
    model = Scheme
    template_name = 'schemes/scheme_form.html'
    form_class = SchemeForm
    permission_required = 'schemes.add_scheme'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        scheme = form.save(commit=False)
        scheme.created_by = self.request.user
        scheme.updated_by = self.request.user
        
        # Auto-set branch for branch managers
        user = self.request.user
        if not scheme.branch and not user.is_superuser:
            if user.role and user.role.name.lower() == 'branch manager' and user.branch:
                scheme.branch = user.branch
        
        # Check permission for global schemes
        if not scheme.branch and not user.has_perm('schemes.manage_global_schemes'):
            messages.error(self.request, "You don't have permission to create global schemes.")
            return self.form_invalid(form)
            
        scheme.save()
        
        # Create audit log
        SchemeAuditLog.objects.create(
            scheme=scheme,
            user=self.request.user,
            action='created',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        # Log user activity
        self.log_user_activity(
            'scheme_created', 
            f'Created new scheme: {scheme.name}'
        )
        
        messages.success(self.request, f'Scheme "{scheme.name}" was created successfully.')
        return redirect('scheme_detail', pk=scheme.pk)


class SchemeUpdateView(SchemeMixin, PermissionRequiredMixin, UpdateView):
    model = Scheme
    template_name = 'schemes/scheme_form.html'
    form_class = SchemeForm 
    permission_required = 'schemes.change_scheme'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def dispatch(self, request, *args, **kwargs):
        # Check branch-based permissions before proceeding
        scheme = self.get_object()
        user = request.user
        
        if not user.is_superuser:
            # Branch managers can only edit schemes for their branch
            if user.role and user.role.name.lower() == 'branch manager':
                if scheme.branch != user.branch:
                    messages.error(request, "You don't have permission to edit this scheme.")
                    return redirect('scheme_detail', pk=scheme.pk)
            
            # Regional managers can edit schemes for branches they manage
            elif user.role and user.role.name.lower() == 'regional manager':
                if scheme.branch and hasattr(user, 'managed_branches'):
                    if scheme.branch not in user.managed_branches.all():
                        messages.error(request, "You don't have permission to edit this scheme.")
                        return redirect('scheme_detail', pk=scheme.pk)
                elif scheme.branch is None and not user.has_perm('schemes.manage_global_schemes'):
                    messages.error(request, "You don't have permission to edit global schemes.")
                    return redirect('scheme_detail', pk=scheme.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        scheme = form.save(commit=False)
        scheme.updated_by = self.request.user
        
        # Form's clean method already processed additional_conditions
        # Get it from the cleaned_data and assign it to the scheme
        if 'additional_conditions' in form.cleaned_data:
            scheme.additional_conditions = form.cleaned_data['additional_conditions']
        
        # Store changes for audit log
        changes = {}
        for field in form.changed_data:
            if hasattr(scheme, field):
                value = getattr(scheme, field)
                # Convert Decimal objects to float for JSON serialization
                if isinstance(value, (Decimal, decimal.Decimal)):
                    changes[field] = float(value)
                else:
                    changes[field] = value
        
        # Add additional conditions changes to audit log if they've changed
        if 'additional_conditions' in form.changed_data:
            changes['additional_conditions'] = scheme.additional_conditions
        
        scheme.save()
        
        # Create audit log
        SchemeAuditLog.objects.create(
            scheme=scheme,
            user=self.request.user,
            action='updated',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            changes=changes
        )
        
        # Log user activity
        self.log_user_activity(
            'scheme_updated', 
            f'Updated scheme: {scheme.name}'
        )
        
        messages.success(self.request, f'Scheme "{scheme.name}" was updated successfully.')
        return redirect('scheme_detail', pk=scheme.pk)


class SchemeDeleteView(SchemeMixin, PermissionRequiredMixin, DeleteView):
    model = Scheme
    template_name = 'schemes/scheme_confirm_delete.html'
    context_object_name = 'scheme'
    permission_required = 'schemes.delete_scheme'
    success_url = reverse_lazy('scheme_list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check branch-based permissions before proceeding
        scheme = self.get_object()
        user = request.user
        
        if not user.is_superuser:
            # Branch managers can only delete schemes for their branch
            if user.role and user.role.name.lower() == 'branch manager':
                if scheme.branch != user.branch:
                    messages.error(request, "You don't have permission to delete this scheme.")
                    return redirect('scheme_detail', pk=scheme.pk)
            
            # Regional managers can delete schemes for branches they manage
            elif user.role and user.role.name.lower() == 'regional manager':
                if scheme.branch and hasattr(user, 'managed_branches'):
                    if scheme.branch not in user.managed_branches.all():
                        messages.error(request, "You don't have permission to delete this scheme.")
                        return redirect('scheme_detail', pk=scheme.pk)
                # Regional managers need special permission for global schemes
                elif scheme.branch is None and not user.has_perm('schemes.manage_global_schemes'):
                    messages.error(request, "You don't have permission to delete global schemes.")
                    return redirect('scheme_detail', pk=scheme.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        scheme = self.get_object()
        scheme_name = scheme.name
        
        # Log audit before deletion
        SchemeAuditLog.objects.create(
            scheme=scheme,
            user=request.user,
            action='deleted',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Log user activity
        self.log_user_activity(
            'scheme_deleted', 
            f'Deleted scheme: {scheme_name}'
        )
        
        messages.success(request, f'Scheme "{scheme_name}" was deleted successfully.')
        return super().delete(request, *args, **kwargs)


class SchemeJsonView(SchemeMixin, View):
    """View to return scheme details in JSON format for AJAX requests"""
    
    def get(self, request, pk):
        try:
            scheme = get_object_or_404(Scheme, pk=pk)
            
            # Check permissions
            user = request.user
            if not user.is_superuser:
                if scheme.branch and user.branch != scheme.branch:
                    if not (user.role and user.role.name.lower() == 'regional manager'):
                        return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # Return scheme data as JSON
            scheme_data = {
                'id': scheme.id,
                'name': scheme.name,
                'description': scheme.description,
                'interest_rate': float(scheme.interest_rate),
                'loan_duration': scheme.loan_duration,
                'minimum_amount': float(scheme.minimum_amount),
                'maximum_amount': float(scheme.maximum_amount),
                'start_date': scheme.start_date.isoformat(),
                'status': scheme.status,
                'is_active': scheme.is_active,
            }
            
            if scheme.end_date:
                scheme_data['end_date'] = scheme.end_date.isoformat()
            
            if scheme.branch:
                scheme_data['branch'] = {
                    'id': scheme.branch.id,
                    'name': scheme.branch.name
                }
            
            if scheme.additional_conditions:
                scheme_data['additional_conditions'] = scheme.additional_conditions
                
            return JsonResponse(scheme_data)
        except Scheme.DoesNotExist:
            return JsonResponse({'error': 'Scheme not found'}, status=404)
