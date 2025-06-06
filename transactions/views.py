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
        try:
            print(f"Form is valid, attempting to save: {form.cleaned_data}")
            form.instance.created_by = self.request.user
            if not form.instance.branch and self.request.user.branch:
                form.instance.branch = self.request.user.branch

            # Ensure interest_rate is set based on scheme
            if form.instance.scheme == 'flexible':
                form.instance.interest_rate = 24.00
            else:  # standard scheme
                form.instance.interest_rate = 12.00

            # Process customer photo
            customer_photo = self.request.POST.get('customer_face_capture')
            if customer_photo and customer_photo.startswith('data:image/jpeg;base64,'):
                print("Saving customer photo capture")
                form.instance.customer_face_capture = customer_photo

            # Process item photos
            item_photos = self.request.POST.getlist('item_photos')
            if item_photos:
                import json
                form.instance.item_photos = json.dumps(item_photos)

            response = super().form_valid(form)
            messages.success(self.request, f'Loan #{form.instance.loan_number} has been created successfully.')
            return response
        except Exception as e:
            print(f"Error saving form: {str(e)}")
            messages.error(self.request, f'Error saving loan: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        print(f"Form is invalid. Errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"Error in field '{field}': {error}")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        print("POST data received:", request.POST)
        # Check for critical form fields
        required_fields = ['customer', 'item_name', 'item_category', 'gold_karat', 
                          'gross_weight', 'net_weight', 'market_price_22k', 
                          'principal_amount', 'scheme']
        
        missing_fields = [field for field in required_fields if field not in request.POST or not request.POST.get(field)]
        if missing_fields:
            messages.error(request, f"Missing required fields: {', '.join(missing_fields)}")
            print(f"Missing fields: {missing_fields}")
        
        return super().post(request, *args, **kwargs)
        
    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.object.loan_number})


class LoanDetailView(LoginRequiredMixin, DetailView):
    model = Loan
    template_name = 'transactions/loan_detail.html'
    context_object_name = 'loan'
    
    def get_object(self):
        loan_number = self.kwargs.get('loan_number')
        loan = get_object_or_404(Loan, loan_number=loan_number)
        return loan
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        
        # Add payment history
        context['payments'] = loan.payments.order_by('-payment_date')
        
        # Add loan extensions
        context['extensions'] = loan.extensions.order_by('-extension_date')
        
        # Add loan items with gold details - ensure proper querying
        loan_items = loan.loanitem_set.all().select_related('item')
        context['loan_items'] = loan_items
        
        # Debug log the items to make sure they're being fetched
        print(f"Found {loan_items.count()} loan items: {[item.item.name for item in loan_items]}")
        
        # Process item photos for the template
        if loan.item_photos:
            import json
            try:
                if isinstance(loan.item_photos, str):
                    photo_list = json.loads(loan.item_photos)
                    context['item_photos_list'] = photo_list
                elif hasattr(loan.item_photos, '__iter__'):
                    context['item_photos_list'] = list(loan.item_photos)
            except (json.JSONDecodeError, AttributeError):
                context['item_photos_list'] = []
        
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
    
    def get_initial(self):
        initial = super().get_initial()
        loan = self.get_object()
        # Ensure scheme is properly initialized
        initial['scheme'] = loan.scheme
        # Set interest rate based on scheme
        if loan.scheme == 'flexible':
            initial['interest_rate'] = 24.00
        else:
            initial['interest_rate'] = 12.00
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        
        # Process item photos for the template
        if loan.item_photos:
            import json
            try:
                if isinstance(loan.item_photos, str):
                    context['item_photos_list'] = json.loads(loan.item_photos)
            except json.JSONDecodeError:
                print("Error decoding item_photos JSON")
                context['item_photos_list'] = []
                
        return context
    
    def form_valid(self, form):
        """Process the form submission when it's valid."""
        # Ensure scheme is properly set before saving
        if 'scheme' in form.cleaned_data:
            form.instance.scheme = form.cleaned_data['scheme']
            # Update interest rate based on scheme
            if form.instance.scheme == 'flexible':
                form.instance.interest_rate = 24.00
            else:
                form.instance.interest_rate = 12.00
        
        # Process customer photo - ensure we don't lose it when updating
        customer_photo = self.request.POST.get('customer_face_capture')
        if customer_photo:
            # Make sure it's a proper data URL
            if customer_photo.startswith('data:image/'):
                print(f"Found customer photo in POST data, length: {len(customer_photo)}")
                form.instance.customer_face_capture = customer_photo
            else:
                print("Received customer_face_capture but format is invalid")
        else:
            print("No customer_face_capture found in POST data")
            # If no photo submitted but there was one before, preserve it
            if form.instance.pk and form.instance.customer_face_capture:
                print("Preserving existing customer photo")
                # Don't change the existing photo
                pass
        
        # Process item photos
        item_photos_data = self.request.POST.get('item_photos')
        if item_photos_data:
            import json
            try:
                # Validate it's a valid JSON string
                json.loads(item_photos_data)
                form.instance.item_photos = item_photos_data
            except json.JSONDecodeError:
                print("Invalid item_photos JSON format, not saving")
        
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        
        # Add PAYMENT_METHOD_CHOICES to context for the template
        context['payment_method_choices'] = Payment.PAYMENT_METHOD_CHOICES
        
        # Use the loan's total_payable_till_date property
        from decimal import Decimal, ROUND_HALF_UP
        
        # Calculate payable amount (principal + interest till date)
        total_payable_today = loan.total_payable_till_date
        
        # Subtract already paid amount
        amount_paid = loan.amount_paid
        final_payable = max(Decimal('0.00'), total_payable_today - amount_paid)
        
        # Round off to nearest whole number (integer)
        rounded_payable = final_payable.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # Add to context - also include the total_payable_mature (at maturity) for comparison
        context['payable_amount'] = rounded_payable
        context['principal_amount'] = loan.principal_amount
        context['total_payable_mature'] = loan.total_payable_mature
        context['days_elapsed'] = loan.days_since_issue
        context['amount_paid'] = amount_paid
        
        # Calculate interest separately
        interest_amount = total_payable_today - loan.principal_amount
        context['interest_amount'] = max(0, interest_amount)
        
        return context
    
    def form_valid(self, form):
        loan = self.get_object()
        form.instance.status = 'foreclosed'
        
        # Get payment method from the form
        payment_method = self.request.POST.get('payment_method')
        
        response = super().form_valid(form)
        
        # If there's a valid payment method and payable amount (customer paid)
        if payment_method and self.request.POST.get('paid_amount', '0') != '0':
            from decimal import Decimal
            from django.utils import timezone
            
            # Create a payment record
            payment_amount = Decimal(self.request.POST.get('paid_amount', '0'))
            if payment_amount > 0:
                Payment.objects.create(
                    loan=loan,
                    amount=payment_amount,
                    payment_date=timezone.now().date(),
                    payment_method=payment_method,
                    reference_number=self.request.POST.get('reference_number', ''),
                    received_by=self.request.user,
                    notes="Payment received during loan foreclosure"
                )
                
                messages.success(self.request, 
                    f'Loan #{loan.loan_number} has been foreclosed with a payment of ₹{payment_amount}')
            else:
                messages.success(self.request, f'Loan #{loan.loan_number} has been foreclosed.')
        else:
            messages.success(self.request, f'Loan #{loan.loan_number} has been foreclosed.')
        
        return response
    
    def get_success_url(self):
        return reverse('loan_list')


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    template_name = 'transactions/payment_form.html'
    fields = ['amount', 'payment_method', 'payment_date', 'reference_number', 'notes']
    
    def get_initial(self):
        initial = super().get_initial()
        initial['payment_date'] = timezone.now().date()
        initial['payment_method'] = 'cash'  # Set default payment method to cash
        return initial
    
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
        loan = self.get_object_loan()
        context['loan'] = loan
        
        # Add payment history to context
        context['payments'] = loan.payments.order_by('-payment_date')
        
        # Check loan scheme restrictions
        if loan.scheme == 'standard':
            # For standard scheme, check if loan is at least 3 months old
            loan_age = (timezone.now().date() - loan.issue_date).days
            if loan_age < 90:  # 3 months = 90 days
                context['scheme_restriction'] = {
                    'message': f'This loan cannot be fully repaid until {loan.issue_date + timezone.timedelta(days=90)}',
                    'days_remaining': 90 - loan_age
                }
        elif loan.scheme == 'flexible':
            # For flexible scheme, check if loan is within 25 days for zero interest
            loan_age = (timezone.now().date() - loan.issue_date).days
            if loan_age <= 25:
                context['scheme_benefit'] = {
                    'message': 'Early repayment benefit: No interest will be charged if fully repaid today!',
                    'days_remaining': 25 - loan_age
                }
        
        return context
    
    def form_valid(self, form):
        loan = self.get_object_loan()
        form.instance.loan = loan
        form.instance.received_by = self.request.user
        
        # Get payment type from the form
        payment_type = self.request.POST.get('payment_type', 'partial')
        
        # Handle scheme-specific payment processing
        from decimal import Decimal, ROUND_HALF_UP
        from django.utils import timezone
        
        payment_amount = form.instance.amount
        current_date = timezone.now().date()
        loan_age = (current_date - loan.issue_date).days
        
        # Get the current outstanding balance
        current_total_paid = loan.amount_paid
        
        # Calculate current payable amount with interest till date
        principal_amount = loan.principal_amount
        
        # Calculate interest based on scheme and elapsed time
        if loan.scheme == 'flexible' and loan_age <= 25:
            interest_amount = Decimal('0.00')
        else:
            daily_rate = Decimal('0.0003287') if loan.scheme == 'standard' else Decimal('0.0006575')
            interest_amount = principal_amount * daily_rate * loan_age
        
        total_payable_till_today = principal_amount + interest_amount
        remaining_balance = max(Decimal('0.00'), total_payable_till_today - current_total_paid)
        rounded_payable = remaining_balance.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # Check if this is a full payment
        is_full_payment = (payment_type == 'full')
        
        if is_full_payment:
            # Check scheme restrictions for full payment
            if loan.scheme == 'standard' and loan_age < 90:
                # Standard scheme requires 3 months minimum period
                messages.error(self.request, 
                    f'This loan cannot be fully repaid until {loan.issue_date + timezone.timedelta(days=90)}')
                return redirect('loan_detail', loan_number=loan.loan_number)
            
            # Set amount to calculated payable amount
            form.instance.amount = rounded_payable
            
            if form.instance.notes:
                form.instance.notes += "\n\nFull payment (principal + interest till date). Loan closed. Gold items returned to customer."
            else:
                form.instance.notes = "Full payment (principal + interest till date). Loan closed. Gold items returned to customer."
                
            # Save the payment first
            response = super().form_valid(form)
            
            # Update loan status to repaid
            loan.status = 'repaid'
            loan.save()
            
            # Update all loan items status to 'returned'
            from inventory.models import Item
            loan_items = loan.loanitem_set.all()
            for loan_item in loan_items:
                item = loan_item.item
                item.status = 'returned'
                item.save()
            
            messages.success(self.request, 
                f'Payment of ₹{form.instance.amount} recorded. Loan has been fully repaid and gold items marked as returned to customer.')
            
            return response
        else:
            # Partial payment
            # Check if the partial payment actually completes the loan
            if current_total_paid + payment_amount >= total_payable_till_today:
                # This payment will actually complete the loan
                if loan.scheme == 'standard' and loan_age < 90:
                    messages.error(self.request, 
                        f'This payment would close the loan, but the loan cannot be fully repaid until {loan.issue_date + timezone.timedelta(days=90)}')
                    return redirect('loan_detail', loan_number=loan.loan_number)
                
                # Add a note about loan closure
                if form.instance.notes:
                    form.instance.notes += "\n\nThis payment completes the loan. Loan marked as repaid. Gold items returned to customer."
                else:
                    form.instance.notes = "This payment completes the loan. Loan marked as repaid. Gold items returned to customer."
                
                # Save the payment first
                response = super().form_valid(form)
                
                # Update loan status
                loan.status = 'repaid'
                loan.save()
                
                # Update all loan items status to 'returned'
                from inventory.models import Item
                loan_items = loan.loanitem_set.all()
                for loan_item in loan_items:
                    item = loan_item.item
                    item.status = 'returned'
                    item.save()
                
                messages.success(self.request, 
                    f'Payment of ₹{form.instance.amount} recorded. The loan has been fully repaid and gold items marked as returned to customer.')
                
                return response
            else:
                # Regular partial payment
                response = super().form_valid(form)
                messages.success(self.request, f'Partial payment of ₹{form.instance.amount} has been recorded successfully.')
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
                            item_photos.append(photo.replace('data:image/jpeg;base64, ' , ''))
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
