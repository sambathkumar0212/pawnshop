from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Avg, Count
from django.http import JsonResponse
from django.utils import timezone
import datetime

from .models import Scheme, SchemeUsageStats, SchemeNotification
from .forms import SchemeForm, SchemeNotificationForm
from accounts.permissions import BranchManagerRequiredMixin


# REST API endpoint for scheme data
class SchemeAPIView(LoginRequiredMixin, View):
    """API endpoint to get scheme details for the calculator"""
    def get(self, request, scheme_id):
        try:
            # Get the scheme (respect branch restrictions)
            scheme = Scheme.objects.filter(
                Q(branch=request.user.branch) | Q(branch__isnull=True),
                id=scheme_id,
                is_active=True
            ).first()
            
            if not scheme:
                return JsonResponse({'error': 'Scheme not found or not accessible'}, status=404)
            
            # Return scheme details
            return JsonResponse({
                'id': scheme.id,
                'name': scheme.name,
                'scheme_type': scheme.scheme_type,
                'interest_rate': float(scheme.interest_rate),
                'duration_days': scheme.duration_days,
                'processing_fee_percentage': float(scheme.processing_fee_percentage),
                'no_interest_period_days': scheme.no_interest_period_days,
                'minimum_period_days': scheme.minimum_period_days
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class SchemeListView(LoginRequiredMixin, BranchManagerRequiredMixin, ListView):
    """View for listing all loan schemes available to a branch"""
    model = Scheme
    template_name = 'content_manager/scheme_list.html'
    context_object_name = 'schemes'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Scheme.objects.all().order_by('-is_active', 'name')
        user = self.request.user
        
        # Filter by branch for non-superusers
        if not user.is_superuser:
            # Show global schemes + branch-specific schemes for current branch
            queryset = queryset.filter(
                Q(branch__isnull=True) |  # Global schemes
                Q(branch=user.branch)     # Branch-specific schemes
            )
            
        # Handle search query
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query)
            )
            
        # Filter by active status if requested
        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['branch_schemes'] = Scheme.objects.filter(branch=self.request.user.branch).count()
        context['total_schemes'] = self.get_queryset().count()
        return context


class SchemeDetailView(LoginRequiredMixin, BranchManagerRequiredMixin, DetailView):
    """View for showing the details of a single scheme"""
    model = Scheme
    template_name = 'content_manager/scheme_detail.html'
    context_object_name = 'scheme'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        
        # Check if user has access to this scheme
        if not user.is_superuser:
            # Users can only access global schemes or schemes for their branch
            if obj.branch is not None and obj.branch != user.branch:
                raise PermissionError("You do not have permission to view this scheme.")
                
        return obj


class SchemeCreateView(LoginRequiredMixin, BranchManagerRequiredMixin, CreateView):
    """View for creating a new loan scheme"""
    model = Scheme
    form_class = SchemeForm
    template_name = 'content_manager/scheme_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Set branch automatically for non-superusers
        if not self.request.user.is_superuser:
            form.instance.branch = self.request.user.branch
        
        response = super().form_valid(form)
        messages.success(self.request, f'Scheme "{form.instance.name}" has been created successfully.')
        return response
    
    def get_success_url(self):
        return reverse('scheme_list')


class SchemeUpdateView(LoginRequiredMixin, BranchManagerRequiredMixin, UpdateView):
    """View for updating an existing loan scheme"""
    model = Scheme
    form_class = SchemeForm
    template_name = 'content_manager/scheme_form.html'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        
        # Superusers can edit any scheme
        if user.is_superuser:
            return obj
            
        # Branch managers can only edit schemes for their branch
        if obj.branch is None or obj.branch != user.branch:
            raise PermissionError("You do not have permission to edit this scheme.")
            
        return obj
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Scheme "{form.instance.name}" has been updated successfully.')
        return response
    
    def get_success_url(self):
        return reverse('scheme_detail', kwargs={'pk': self.object.pk})


class SchemeDeleteView(LoginRequiredMixin, BranchManagerRequiredMixin, DeleteView):
    """View for deleting a loan scheme"""
    model = Scheme
    template_name = 'content_manager/scheme_confirm_delete.html'
    context_object_name = 'scheme'
    success_url = reverse_lazy('scheme_list')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        
        # Superusers can delete any scheme
        if user.is_superuser:
            return obj
            
        # Branch managers can only delete schemes for their branch
        if obj.branch is None or obj.branch != user.branch:
            raise PermissionError("You do not have permission to delete this scheme.")
            
        return obj
        
    def delete(self, request, *args, **kwargs):
        scheme = self.get_object()
        scheme_name = scheme.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Scheme "{scheme_name}" has been deleted successfully.')
        return response


def toggle_scheme_status(request, pk):
    """View for toggling a scheme's active status"""
    scheme = get_object_or_404(Scheme, pk=pk)
    user = request.user
    
    # Check permissions
    if not user.is_superuser:
        if scheme.branch is None or scheme.branch != user.branch:
            messages.error(request, "You do not have permission to modify this scheme.")
            return redirect('scheme_list')
    
    # Toggle status
    scheme.is_active = not scheme.is_active
    scheme.save()
    
    status = "activated" if scheme.is_active else "deactivated"
    messages.success(request, f'Scheme "{scheme.name}" has been {status}.')
    
    # Redirect back to the list or detail page
    next_page = request.GET.get('next', 'scheme_list')
    if next_page == 'detail':
        return redirect('scheme_detail', pk=scheme.pk)
    return redirect('scheme_list')


class SchemeStatsView(LoginRequiredMixin, BranchManagerRequiredMixin, TemplateView):
    """View for displaying scheme usage statistics"""
    template_name = 'content_manager/scheme_stats.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get time period from request parameters, default to last 30 days
        days = int(self.request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get scheme filter, if any
        scheme_id = self.request.GET.get('scheme')
        scheme = None
        if scheme_id:
            try:
                scheme = Scheme.objects.get(pk=scheme_id)
            except Scheme.DoesNotExist:
                pass
        
        # Get branch filter - for superusers, allow filtering by branch
        branch_id = self.request.GET.get('branch')
        branch = None
        
        # For branch users, always filter by their branch
        if not user.is_superuser:
            branch = user.branch
        elif branch_id:
            try:
                from branches.models import Branch
                branch = Branch.objects.get(pk=branch_id)
            except:
                pass
        
        # Query base
        stats_query = SchemeUsageStats.objects.filter(
            start_date__gte=start_date - datetime.timedelta(days=30),  # get stats from slightly before
            end_date__lte=end_date + datetime.timedelta(days=1)  # ensure we get today's stats
        )
        
        # Apply filters
        if scheme:
            stats_query = stats_query.filter(scheme=scheme)
        
        if branch:
            stats_query = stats_query.filter(branch=branch)
        elif not user.is_superuser:
            # Non-superusers can only see global stats and their branch stats
            stats_query = stats_query.filter(
                Q(branch__isnull=True) | Q(branch=user.branch)
            )
        
        # Get the data
        stats = stats_query.select_related('scheme', 'branch').order_by('-start_date')
        
        # Calculate totals and averages
        summary = {
            'total_loans': stats.aggregate(Sum('total_loans_count'))['total_loans_count__sum'] or 0,
            'active_loans': stats.aggregate(Sum('active_loans_count'))['active_loans_count__sum'] or 0,
            'completed_loans': stats.aggregate(Sum('completed_loans_count'))['completed_loans_count__sum'] or 0,
            'defaulted_loans': stats.aggregate(Sum('defaulted_loans_count'))['defaulted_loans_count__sum'] or 0,
            'total_principal': stats.aggregate(Sum('total_principal_amount'))['total_principal_amount__sum'] or 0,
            'total_interest': stats.aggregate(Sum('total_interest_earned'))['total_interest_earned__sum'] or 0,
            'total_fees': stats.aggregate(Sum('total_processing_fees'))['total_processing_fees__sum'] or 0,
        }
        
        # Calculate default rate
        if summary['total_loans'] > 0:
            summary['default_rate'] = (summary['defaulted_loans'] / summary['total_loans']) * 100
        else:
            summary['default_rate'] = 0
            
        # Calculate completion rate
        if summary['total_loans'] > 0:
            summary['completion_rate'] = (summary['completed_loans'] / summary['total_loans']) * 100
        else:
            summary['completion_rate'] = 0
        
        # Add to context
        context.update({
            'stats': stats[:100],  # Limit to 100 records for performance
            'summary': summary,
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'scheme': scheme,
            'branch': branch,
            'day_options': [7, 30, 90, 180, 365],
        })
        
        # Get schemes for filter dropdown
        available_schemes = Scheme.objects.filter(is_active=True)
        if not user.is_superuser:
            available_schemes = available_schemes.filter(
                Q(branch__isnull=True) | Q(branch=user.branch)
            )
        context['available_schemes'] = available_schemes
        
        # Get branches for filter dropdown (superusers only)
        if user.is_superuser:
            from branches.models import Branch
            context['available_branches'] = Branch.objects.all()
            
        return context


class SchemeStatsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View to display scheme usage statistics"""
    model = SchemeUsageStats
    template_name = 'content_manager/scheme_stats.html'
    context_object_name = 'stats'
    permission_required = 'content_manager.view_schemeusagestats'
    
    def get_queryset(self):
        # Get filter parameters from request
        days = int(self.request.GET.get('days', 30))
        scheme_id = self.request.GET.get('scheme')
        branch_id = self.request.GET.get('branch')
        
        # Store selected filters for context
        self.days = days
        self.scheme = Scheme.objects.filter(id=scheme_id).first() if scheme_id else None
        self.branch = Branch.objects.filter(id=branch_id).first() if branch_id else None
        
        # Base queryset filtered by time period
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        queryset = SchemeUsageStats.objects.filter(
            end_date__gte=start_date,
            start_date__lte=end_date
        )
        
        # Apply additional filters if provided
        if self.scheme:
            queryset = queryset.filter(scheme=self.scheme)
        
        if self.branch:
            queryset = queryset.filter(branch=self.branch)
            
        # Only show stats for branches the user has access to
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(branch=self.request.user.branch) | Q(branch__isnull=True)
            )
            
        return queryset.order_by('-end_date', 'scheme__name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['days'] = self.days
        context['scheme'] = self.scheme
        context['branch'] = self.branch
        context['day_options'] = [7, 30, 90, 180, 365]
        
        # Get available schemes and branches for filters
        if self.request.user.is_superuser:
            context['available_schemes'] = Scheme.objects.filter(is_active=True)
            context['available_branches'] = Branch.objects.all()
        else:
            # Only show schemes available to the user's branch
            context['available_schemes'] = Scheme.objects.filter(
                Q(branch=self.request.user.branch) | Q(branch__isnull=True),
                is_active=True
            )
            context['available_branches'] = [self.request.user.branch]
            
        # Add summary statistics
        stats = context['stats']
        
        summary = {
            'total_loans': sum(s.total_loans_count for s in stats),
            'active_loans': sum(s.active_loans_count for s in stats),
            'completed_loans': sum(s.completed_loans_count for s in stats),
            'defaulted_loans': sum(s.defaulted_loans_count for s in stats),
            'total_principal': sum(s.total_principal_amount for s in stats),
            'total_interest': sum(s.total_interest_earned for s in stats),
            'total_fees': sum(s.total_processing_fees for s in stats),
        }
        
        # Calculate derived metrics
        if summary['total_loans'] > 0:
            summary['completion_rate'] = (summary['completed_loans'] / summary['total_loans']) * 100
            summary['default_rate'] = (summary['defaulted_loans'] / summary['total_loans']) * 100
            summary['average_loan'] = summary['total_principal'] / summary['total_loans']
        else:
            summary['completion_rate'] = 0
            summary['default_rate'] = 0
            summary['average_loan'] = 0
            
        context['summary'] = summary
            
        return context


# SchemeNotification Views
class SchemeNotificationListView(LoginRequiredMixin, BranchManagerRequiredMixin, ListView):
    """View to list all scheme notifications"""
    model = SchemeNotification
    template_name = 'content_manager/scheme_notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 10
    
    def get_queryset(self):
        # Base queryset
        queryset = SchemeNotification.objects.all()
        
        # Filter by branch access
        if not self.request.user.is_superuser:
            user_branch = self.request.user.branch
            queryset = queryset.filter(
                Q(all_branches=True) | 
                Q(branches=user_branch)
            ).distinct()
            
        # Add filter for active/current notifications
        show_active = self.request.GET.get('active', 'true').lower() == 'true'
        if show_active:
            today = timezone.now().date()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=today,
                end_date__gte=today
            )
            
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add flag for active filter
        context['show_active'] = self.request.GET.get('active', 'true').lower() == 'true'
        return context


class SchemeNotificationDetailView(LoginRequiredMixin, BranchManagerRequiredMixin, DetailView):
    """View to show details of a scheme notification"""
    model = SchemeNotification
    template_name = 'content_manager/scheme_notification_detail.html'
    context_object_name = 'notification'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check if user has access to this notification
        if not self.request.user.is_superuser:
            user_branch = self.request.user.branch
            if not (obj.all_branches or user_branch in obj.branches.all()):
                messages.error(self.request, "You don't have permission to view this notification.")
                return redirect('scheme_notification_list')
                
        return obj


class SchemeNotificationCreateView(LoginRequiredMixin, BranchManagerRequiredMixin, CreateView):
    """View to create a new scheme notification"""
    model = SchemeNotification
    form_class = SchemeNotificationForm
    template_name = 'content_manager/scheme_notification_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass user to form for permission-based scheme filtering
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, f"Notification '{self.object.title}' has been created.")
        return reverse_lazy('scheme_notification_list')


class SchemeNotificationUpdateView(LoginRequiredMixin, BranchManagerRequiredMixin, UpdateView):
    """View to update an existing scheme notification"""
    model = SchemeNotification
    form_class = SchemeNotificationForm
    template_name = 'content_manager/scheme_notification_form.html'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check if user has permission to edit this notification
        if not self.request.user.is_superuser:
            # Only allow branch managers to edit notifications for their branch's schemes
            if obj.scheme.branch and obj.scheme.branch != self.request.user.branch:
                messages.error(self.request, "You don't have permission to edit this notification.")
                return redirect('scheme_notification_list')
                
        return obj
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, f"Notification '{self.object.title}' has been updated.")
        return reverse_lazy('scheme_notification_list')


class SchemeNotificationDeleteView(LoginRequiredMixin, BranchManagerRequiredMixin, DeleteView):
    """View to delete a scheme notification"""
    model = SchemeNotification
    template_name = 'content_manager/scheme_notification_confirm_delete.html'
    context_object_name = 'notification'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check if user has permission to delete this notification
        if not self.request.user.is_superuser:
            # Only allow branch managers to delete notifications for their branch's schemes
            if obj.scheme.branch and obj.scheme.branch != self.request.user.branch:
                messages.error(self.request, "You don't have permission to delete this notification.")
                return redirect('scheme_notification_list')
                
        return obj
    
    def get_success_url(self):
        messages.success(self.request, f"Notification '{self.object.title}' has been deleted.")
        return reverse_lazy('scheme_notification_list')


@login_required
@permission_required('content_manager.change_scheme')
def toggle_scheme_status(request, pk):
    """Toggle the active status of a scheme"""
    scheme = get_object_or_404(Scheme, pk=pk)
    
    # Check if user has permission to modify this scheme
    if not request.user.is_superuser and scheme.branch != request.user.branch:
        messages.error(request, "You don't have permission to modify this scheme.")
        return redirect('scheme_list')
    
    # Toggle status
    scheme.is_active = not scheme.is_active
    scheme.save()
    
    status = "activated" if scheme.is_active else "deactivated"
    messages.success(request, f"Scheme '{scheme.name}' has been {status}.")
    
    return redirect('scheme_list')
