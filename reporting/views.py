# Django imports
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.http import HttpResponse, FileResponse

# Model imports
from transactions.models import Sale, Loan, Payment
from branches.models import Branch
from .models import Report, ReportSchedule, ReportExecution, Dashboard, DashboardWidget

import csv
import io
from datetime import datetime, timedelta

# Placeholder views for reporting functionality
class DashboardListView(LoginRequiredMixin, ListView):
    template_name = 'reporting/dashboard_list.html'
    context_object_name = 'dashboards'
    
    def get_queryset(self):
        # Will be implemented with actual Dashboard model
        return []


class DashboardView(LoginRequiredMixin, DetailView):
    template_name = 'reporting/dashboard_detail.html'
    context_object_name = 'dashboard'
    
    def get_object(self):
        # Will be implemented with actual Dashboard model
        return None


class DashboardCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/dashboard_form.html'


class DashboardUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/dashboard_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard_id'] = self.kwargs.get('pk')
        return context


class DashboardDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/dashboard_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard_id'] = self.kwargs.get('pk')
        return context


class WidgetCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/widget_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard_id'] = self.kwargs.get('dashboard_id')
        return context


class WidgetUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/widget_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['widget_id'] = self.kwargs.get('pk')
        return context


class WidgetDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/widget_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['widget_id'] = self.kwargs.get('pk')
        return context


class ReportListView(LoginRequiredMixin, ListView):
    template_name = 'reporting/report_list.html'
    context_object_name = 'reports'
    
    def get_queryset(self):
        # Will be implemented with actual Report model
        return []


class ReportCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/report_form.html'


class ReportDetailView(LoginRequiredMixin, DetailView):
    template_name = 'reporting/report_detail.html'
    context_object_name = 'report'
    
    def get_object(self):
        # Will be implemented with actual Report model
        return None


class ReportUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/report_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_id'] = self.kwargs.get('pk')
        return context


class ReportDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/report_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_id'] = self.kwargs.get('pk')
        return context

# Missing views referenced in URLs
class ReportRunView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # Logic to run a report based on its ID
        messages.success(request, "Report execution started")
        return redirect('report_detail', pk=pk)


class ReportScheduleCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/report_schedule_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_id'] = self.kwargs.get('pk')
        return context


class ReportDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # Logic to download report results
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_{pk}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        # Sample CSV data
        writer = csv.writer(response)
        writer.writerow(['Date', 'Category', 'Amount'])
        writer.writerow([timezone.now().date(), 'Sample Category', '100.00'])
        
        return response


class ReportGenerateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/report_generate.html'


# Specific report type views
class FinancialReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/financial_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add financial report specific context here
        context['title'] = 'Financial Report'
        return context


class InventoryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/inventory_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add inventory report specific context here
        context['title'] = 'Inventory Report'
        return context


class LoanReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/loan_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add loan report specific context here
        context['title'] = 'Loan Report'
        return context


class CustomerReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/customer_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add customer report specific context here
        context['title'] = 'Customer Report'
        return context


class OperationalReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/operational_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add operational report specific context here
        context['title'] = 'Operational Report'
        return context


# Specific dashboard type views
class FinancialDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/financial_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day = today.replace(day=1)
        last_month = (first_day - timedelta(days=1)).replace(day=1)
        
        # Filter by branch if user is not superuser
        branch_filter = Q()
        if not self.request.user.is_superuser and self.request.user.branch:
            branch_filter = Q(branch=self.request.user.branch)
        
        # Calculate revenue metrics
        current_month_sales = Sale.objects.filter(
            branch_filter,
            sale_date__year=today.year,
            sale_date__month=today.month,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        last_month_sales = Sale.objects.filter(
            branch_filter,
            sale_date__year=last_month.year,
            sale_date__month=last_month.month,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate loan metrics
        loan_portfolio = Loan.objects.filter(
            branch_filter,
            status='active'
        ).aggregate(total=Sum('principal_amount'))['total'] or 0
        
        last_month_portfolio = Loan.objects.filter(
            branch_filter,
            status='active',
            created_at__lt=first_day
        ).aggregate(total=Sum('principal_amount'))['total'] or 0
        
        # Get branch data
        branches = Branch.objects.filter(is_active=True)
        if not self.request.user.is_superuser and self.request.user.branch:
            branches = branches.filter(id=self.request.user.branch.id)
        
        branch_data = []
        branch_labels = []
        branch_revenue = []
        branch_colors = []
        
        for idx, branch in enumerate(branches):
            revenue = Sale.objects.filter(
                branch=branch,
                sale_date__year=today.year,
                sale_date__month=today.month,
                status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            color = [
                'rgba(78, 115, 223, 0.8)',
                'rgba(28, 200, 138, 0.8)',
                'rgba(246, 194, 62, 0.8)',
                'rgba(231, 74, 59, 0.8)',
                'rgba(54, 185, 204, 0.8)'
            ][idx % 5]
            
            branch_data.append({
                'name': branch.name,
                'revenue': revenue,
                'color': color
            })
            branch_labels.append(branch.name)
            branch_revenue.append(revenue)
            branch_colors.append(color)
        
        # Calculate monthly data for charts
        months = range(1, 13)
        interest_income_data = []
        sales_revenue_data = []
        other_revenue_data = []
        gross_margin_data = []
        net_margin_data = []
        
        for month in months:
            # Interest income from loans
            interest = Loan.objects.filter(
                branch_filter,
                created_at__year=today.year,
                created_at__month=month
            ).aggregate(
                total=Sum(F('principal_amount') * F('interest_rate') / 100)
            )['total'] or 0
            
            # Sales revenue
            sales = Sale.objects.filter(
                branch_filter,
                sale_date__year=today.year,
                sale_date__month=month,
                status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            # Other revenue (placeholder - implement based on your needs)
            other = 0
            
            # Calculate estimated expenses (60% of revenue as placeholder)
            total_revenue = interest + sales + other
            estimated_expenses = total_revenue * 0.6
            estimated_profit = total_revenue * 0.2
            
            # Calculate margins
            if total_revenue > 0:
                gross_margin = ((total_revenue - estimated_expenses) / total_revenue) * 100
                net_margin = (estimated_profit / total_revenue) * 100
            else:
                gross_margin = 0
                net_margin = 0
            
            interest_income_data.append(interest)
            sales_revenue_data.append(sales)
            other_revenue_data.append(other)
            gross_margin_data.append(gross_margin)
            net_margin_data.append(net_margin)
        
        # Calculate growth rates
        revenue_growth = ((current_month_sales - last_month_sales) / last_month_sales * 100) if last_month_sales else 0
        portfolio_growth = ((loan_portfolio - last_month_portfolio) / last_month_portfolio * 100) if last_month_portfolio else 0
        
        # Add all data to context
        context.update({
            'total_revenue': current_month_sales,
            'revenue_growth': revenue_growth,
            'net_profit': current_month_sales * 0.2,  # Placeholder - implement actual calculation
            'profit_growth': 2.5,  # Placeholder - implement actual calculation
            'loan_portfolio': loan_portfolio,
            'portfolio_growth': portfolio_growth,
            'expenses': current_month_sales * 0.6,  # Placeholder - implement actual calculation
            'expense_growth': 1.8,  # Placeholder - implement actual calculation
            
            # Chart data
            'interest_income_data': interest_income_data,
            'sales_revenue_data': sales_revenue_data,
            'other_revenue_data': other_revenue_data,
            'gross_margin_data': gross_margin_data,
            'net_margin_data': net_margin_data,
            
            # Branch data
            'branches': branch_data,
            'branch_labels': branch_labels,
            'branch_revenue_data': branch_revenue,
            'branch_colors': branch_colors,
            
            # Financial metrics
            'roa_current': 15.2,  # Placeholder - implement actual calculation
            'roa_previous': 14.8,
            'roa_change': 0.4,
            'roa_target': 15.0,
            
            'current_ratio': 2.1,  # Placeholder - implement actual calculation
            'previous_ratio': 2.0,
            'ratio_change': 0.1,
            'ratio_target': 2.0,
            
            'default_rate': 3.2,  # Placeholder - implement actual calculation
            'previous_default_rate': 3.4,
            'default_rate_change': -0.2,
            'default_rate_target': 3.5,
        })
        
        return context


class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/inventory_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inventory Dashboard'
        return context


class LoanDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/loan_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Loan Dashboard'
        return context


class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/customer_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Customer Dashboard'
        return context


class BranchDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/branch_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Branch Dashboard'
        return context


class ExecutiveDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/executive_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Executive Dashboard'
        return context


# Schedule management views
class ScheduleListView(LoginRequiredMixin, ListView):
    template_name = 'reporting/schedule_list.html'
    context_object_name = 'schedules'
    
    def get_queryset(self):
        # Will be implemented with actual Schedule model
        return []


class ScheduleUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/schedule_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedule_id'] = self.kwargs.get('pk')
        return context


class ScheduleDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/schedule_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedule_id'] = self.kwargs.get('pk')
        return context


# Report execution views
class ExecutionListView(LoginRequiredMixin, ListView):
    template_name = 'reporting/execution_list.html'
    context_object_name = 'executions'
    
    def get_queryset(self):
        # Will be implemented with actual ReportExecution model
        return []


class ExecutionDetailView(LoginRequiredMixin, DetailView):
    template_name = 'reporting/execution_detail.html'
    context_object_name = 'execution'
    
    def get_object(self):
        # Will be implemented with actual ReportExecution model
        return None


# Analysis tool views
class SalesAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/sales_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sales Analysis'
        return context


class InventoryAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/inventory_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inventory Analysis'
        return context


class LoanAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/loan_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Loan Analysis'
        return context


class BranchAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'reporting/branch_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Branch Analysis'
        return context
