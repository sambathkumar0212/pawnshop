from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.http import Http404, HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from .models import Loan, Payment, LoanExtension, Sale
from .forms import LoanForm, SaleForm, LoanExtensionForm

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
        loan_identifier = self.kwargs.get('loan_number')
        
        # First try to find by loan_number (UUID)
        try:
            return Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    return Loan.objects.get(pk=int(loan_identifier))
            except (Loan.DoesNotExist, ValueError):
                pass
            
            # If we get here, the loan doesn't exist
            raise Http404("No Loan matches the given query.")
        
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
        loan_identifier = self.kwargs.get('loan_number')
        
        # First try to find by loan_number (UUID)
        try:
            return Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    return Loan.objects.get(pk=int(loan_identifier))
            except (Loan.DoesNotExist, ValueError):
                pass
            
            # If we get here, the loan doesn't exist
            raise Http404("No Loan matches the given query.")
    
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
    model = LoanExtension
    template_name = 'transactions/loan_extension_form.html'
    form_class = LoanExtensionForm
    
    def get_object_loan(self):
        loan_identifier = self.kwargs.get('loan_number')
        
        # First try to find by loan_number (UUID)
        try:
            return Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    return Loan.objects.get(pk=int(loan_identifier))
            except (Loan.DoesNotExist, ValueError):
                pass
            
            # If we get here, the loan doesn't exist
            raise Http404("No Loan matches the given query.")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loan'] = self.get_object_loan()
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['loan'] = self.get_object_loan()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        loan = self.get_object_loan()
        form.instance.loan = loan
        form.instance.previous_due_date = loan.due_date
        form.instance.approved_by = self.request.user
        
        # Update the loan status, due date and grace period end
        loan.status = 'extended'
        loan.due_date = form.instance.new_due_date
        loan.grace_period_end = form.cleaned_data.get('new_grace_period_end')
        loan.save()
        
        messages.success(self.request, f'Loan #{loan.loan_number} has been extended successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.kwargs['loan_number']})


class LoanForecloseView(LoginRequiredMixin, UpdateView):
    model = Loan
    template_name = 'transactions/loan_foreclose_form.html'
    fields = ['status']
    
    def get_object(self):
        loan_identifier = self.kwargs.get('loan_number')
        
        # First try to find by loan_number (UUID)
        try:
            return Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    return Loan.objects.get(pk=int(loan_identifier))
            except (Loan.DoesNotExist, ValueError):
                pass
            
            # If we get here, the loan doesn't exist
            raise Http404("No Loan matches the given query.")
    
    def get_success_url(self):
        return reverse('loan_list')


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    template_name = 'transactions/payment_form.html'
    fields = ['amount', 'payment_method', 'payment_date', 'reference_number', 'notes']
    
    def get_object_loan(self):
        loan_identifier = self.kwargs.get('loan_number')
        
        # First try to find by loan_number (UUID)
        try:
            return Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    return Loan.objects.get(pk=int(loan_identifier))
            except (Loan.DoesNotExist, ValueError):
                pass
            
            # If we get here, the loan doesn't exist
            raise Http404("No Loan matches the given query.")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loan'] = self.get_object_loan()
        return context
    
    def form_valid(self, form):
        loan = self.get_object_loan()
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


class LoanDocumentView(LoginRequiredMixin, View):
    """Generate a PDF loan agreement with Indian rules and conditions"""
    
    def get(self, request, loan_number):
        loan_identifier = loan_number
        
        # First try to find by loan_number (UUID)
        try:
            loan = Loan.objects.get(loan_number=loan_identifier)
        except Loan.DoesNotExist:
            # If not found, try to find by primary key (ID)
            try:
                if loan_identifier.isdigit():
                    loan = Loan.objects.get(pk=int(loan_identifier))
                else:
                    raise Http404("No Loan matches the given query.")
            except (Loan.DoesNotExist, ValueError):
                raise Http404("No Loan matches the given query.")
        
        # Get loan items with gold details
        loan_items = loan.loanitem_set.all()
        
        # Process customer photo (remove the data:image/jpeg;base64, prefix if present)
        customer_photo = None
        if hasattr(loan, 'customer_face_capture') and loan.customer_face_capture:
            if loan.customer_face_capture.startswith('data:image/jpeg;base64,'):
                customer_photo = loan.customer_face_capture.replace('data:image/jpeg;base64,', '')
            else:
                customer_photo = loan.customer_face_capture
                
        # Process item photos (parse JSON string if needed)
        item_photos = []
        if hasattr(loan, 'item_photos') and loan.item_photos:
            import json
            try:
                # If stored as JSON string
                if isinstance(loan.item_photos, str):
                    photo_list = json.loads(loan.item_photos)
                    for photo in photo_list:
                        if photo.startswith('data:image/jpeg;base64,'):
                            item_photos.append(photo.replace('data:image/jpeg;base64,', ''))
                        else:
                            item_photos.append(photo)
                # If already a list or similar iterable
                elif hasattr(loan.item_photos, '__iter__'):
                    for photo in loan.item_photos:
                        if photo.startswith('data:image/jpeg;base64,'):
                            item_photos.append(photo.replace('data:image/jpeg;base64,', ''))
                        else:
                            item_photos.append(photo)
            except (json.JSONDecodeError, AttributeError):
                # If there's an error parsing, leave item_photos empty
                pass
        
        # Prepare context for PDF template
        context = {
            'loan': loan,
            'loan_items': loan_items,
            'customer': loan.customer,
            'branch': loan.branch,
            'date_today': timezone.now().date(),
            'customer_photo': customer_photo,
            'item_photos': item_photos
        }
        
        # Render the PDF template
        template = get_template('transactions/loan_document_pdf.html')
        html = template.render(context)
        result = BytesIO()
        
        # Create PDF from HTML content
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            # Generate response with PDF content
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"loan_agreement_{loan.loan_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # If PDF generation fails
        return HttpResponse("Error generating PDF", status=400)
