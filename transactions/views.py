from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from .models import Loan, Payment, LoanExtension, Sale
from .forms import LoanForm, SaleForm

# Basic placeholder views for the transactions app
# These will need to be implemented properly with the correct models

class LoanListView(LoginRequiredMixin, ListView):
    template_name = 'transactions/loan_list.html'
    context_object_name = 'loans'
    
    def get_queryset(self):
        queryset = Loan.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(branch=self.request.user.branch)
        return queryset


class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = 'transactions/loan_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        initial['issue_date'] = timezone.now().date()
        if 'customer_id' in self.request.GET:
            initial['customer'] = self.request.GET['customer_id']
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if not form.instance.branch and self.request.user.branch:
            form.instance.branch = self.request.user.branch
        response = super().form_valid(form)
        messages.success(self.request, f'Loan #{form.instance.loan_number} has been created successfully.')
        return response

    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.object.loan_number})


class LoanDetailView(LoginRequiredMixin, DetailView):
    model = Loan
    template_name = 'transactions/loan_detail.html'
    context_object_name = 'loan'
    
    def get_object(self):
        loan_number = self.kwargs.get('loan_number')
        return get_object_or_404(Loan, loan_number=loan_number)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        
        # Add payment history
        context['payments'] = loan.payments.order_by('-payment_date')
        
        # Add loan extensions
        context['extensions'] = loan.extensions.order_by('-extension_date')
        
        # Add loan items with gold details
        context['loan_items'] = loan.loanitem_set.all()
        
        return context


class LoanUpdateView(LoginRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = 'transactions/loan_form.html'
    
    def get_object(self):
        loan_number = self.kwargs.get('loan_number')
        return get_object_or_404(Loan, loan_number=loan_number)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Loan #{form.instance.loan_number} has been updated successfully.')
        return response

    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.object.loan_number})


class LoanExtensionCreateView(LoginRequiredMixin, CreateView):
    template_name = 'transactions/loan_extension_form.html'
    
    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.kwargs['loan_number']})


class LoanForecloseView(LoginRequiredMixin, UpdateView):
    template_name = 'transactions/loan_foreclose_form.html'
    
    def get_success_url(self):
        return reverse('loan_list')


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    template_name = 'transactions/payment_form.html'
    fields = ['amount', 'payment_method', 'payment_date', 'reference_number', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan_number = self.kwargs.get('loan_number')
        context['loan'] = get_object_or_404(Loan, loan_number=loan_number)
        return context
    
    def form_valid(self, form):
        loan_number = self.kwargs.get('loan_number')
        loan = get_object_or_404(Loan, loan_number=loan_number)
        form.instance.loan = loan
        form.instance.received_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Payment of ₹{form.instance.amount} has been recorded successfully.')
        return response

    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.kwargs['loan_number']})


class PaymentListView(LoginRequiredMixin, ListView):
    template_name = 'transactions/payment_list.html'
    context_object_name = 'payments'
    
    def get_queryset(self):
        # This will need to be implemented with proper Payment model
        return []


class PaymentDetailView(LoginRequiredMixin, DetailView):
    template_name = 'transactions/payment_detail.html'
    context_object_name = 'payment'


class SaleListView(LoginRequiredMixin, ListView):
    template_name = 'transactions/sale_list.html'
    context_object_name = 'sales'
    
    def get_queryset(self):
        # This will need to be implemented with proper Sale model
        return []


class SaleCreateView(LoginRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'transactions/sale_form.html'
    
    def form_valid(self, form):
        form.instance.sold_by = self.request.user
        form.instance.sale_date = timezone.now().date()
        form.instance.branch = self.request.user.branch
        form.instance.total_amount = (
            form.instance.selling_price + 
            form.instance.tax - 
            form.instance.discount
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('sale_list')


class SaleDetailView(LoginRequiredMixin, DetailView):
    template_name = 'transactions/sale_detail.html'
    context_object_name = 'sale'


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'transactions/sale_form.html'
    
    def get_success_url(self):
        return reverse('sale_detail', kwargs={'transaction_number': self.object.transaction_number})


class SaleCancelView(LoginRequiredMixin, UpdateView):
    template_name = 'transactions/sale_cancel_form.html'
    
    def get_success_url(self):
        return reverse('sale_list')


class SaleReceiptView(LoginRequiredMixin, DetailView):
    template_name = 'transactions/sale_receipt.html'
    context_object_name = 'sale'
