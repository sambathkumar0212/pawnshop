from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone

from .models import Branch, BranchSettings
from .forms import BranchForm, BranchSettingsForm


class BranchListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Branch
    template_name = 'branches/branch_list.html'
    context_object_name = 'branches'
    permission_required = 'branches.view_branch'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Annotate with statistics - use different names to avoid property conflicts
        queryset = queryset.annotate(
            staff_count_annotated=Count('staff', distinct=True),
            inventory_count_annotated=Count('items', distinct=True),
            # Use Q object instead of dictionary for filtering
            active_loans_annotated=Count('loans', filter=Q(loans__status='active'), distinct=True)
        )
        return queryset


class BranchDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Branch
    template_name = 'branches/branch_detail.html'
    context_object_name = 'branch'
    permission_required = 'branches.view_branch'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branch = self.object
        today = timezone.now().date()
        current_month = timezone.now().month
        
        # Get staff counts
        context['staff_count'] = branch.staff.count()
        
        # Get inventory statistics
        context['inventory_count'] = branch.items.count()
        context['available_items'] = branch.items.filter(status='available').count()
        context['pawned_items'] = branch.items.filter(status='pawned').count()
        
        # Get loan statistics
        context['active_loans'] = branch.loans.filter(status='active').count()
        context['overdue_loans'] = branch.loans.filter(status='active', due_date__lt=today).count()
        
        # Get sales statistics
        context['sales_this_month'] = branch.sales.filter(
            sale_date__month=current_month
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Get settings
        try:
            context['settings'] = branch.settings
        except BranchSettings.DoesNotExist:
            context['settings'] = None
        
        return context


class BranchCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Branch
    template_name = 'branches/branch_form.html'
    form_class = BranchForm
    permission_required = 'branches.add_branch'
    success_url = reverse_lazy('branch_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Branch {form.instance.name} has been created successfully.')
        
        # Create default branch settings
        BranchSettings.objects.create(
            branch=form.instance,
            max_loan_amount=5000.00,
            default_interest_rate=0.10,
            loan_duration_days=30
        )
        
        return response


class BranchUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Branch
    template_name = 'branches/branch_form.html'
    form_class = BranchForm
    permission_required = 'branches.change_branch'
    success_url = reverse_lazy('branch_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Branch {form.instance.name} has been updated successfully.')
        return response


class BranchDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Branch
    template_name = 'branches/branch_confirm_delete.html'
    context_object_name = 'branch'
    permission_required = 'branches.delete_branch'
    success_url = reverse_lazy('branch_list')
    
    def delete(self, request, *args, **kwargs):
        branch = self.get_object()
        messages.success(request, f'Branch {branch.name} has been deleted successfully.')
        return super().delete(request, *args, **kwargs)


class BranchSettingsUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = BranchSettings
    template_name = 'branches/branch_settings_form.html'
    form_class = BranchSettingsForm
    permission_required = 'branches.change_branchsettings'
    
    def get_object(self, queryset=None):
        branch_id = self.kwargs.get('branch_id')
        branch = get_object_or_404(Branch, id=branch_id)
        obj, created = BranchSettings.objects.get_or_create(branch=branch)
        return obj
    
    def get_success_url(self):
        return reverse_lazy('branch_detail', kwargs={'pk': self.kwargs.get('branch_id')})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Branch settings have been updated successfully.')
        return response
