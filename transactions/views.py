from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from .models import Loan, Payment, LoanExtension, Sale
from .forms import LoanForm, SaleForm, LoanExtensionForm
from .utils import ManagerPermissionMixin
from django.db.models import Q
from num2words import num2words
from django.core.files.base import ContentFile
import base64
import json
import ast

# Basic placeholder views for the transactions app
# These will need to be implemented properly with the correct models

class LoanListView(LoginRequiredMixin, ListView):
    template_name = 'transactions/loan_list.html'
    context_object_name = 'loans'
    paginate_by = 10

    def get_queryset(self):
        queryset = Loan.objects.all()

        # Branch filter for non-superusers
        if not self.request.user.is_superuser:
            queryset = queryset.filter(branch=self.request.user.branch)

        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(loan_number__icontains=search) |
                Q(loanitem_set__item__name__icontains=search)
            ).distinct()

        # Date range filter
        date_range = self.request.GET.get('date_range')
        today = timezone.now().date()
        
        if date_range == 'today':
            queryset = queryset.filter(issue_date=today)
        elif date_range == 'this_week':
            week_start = today - timezone.timedelta(days=today.weekday())
            queryset = queryset.filter(issue_date__gte=week_start)
        elif date_range == 'this_month':
            queryset = queryset.filter(issue_date__year=today.year, issue_date__month=today.month)
        elif date_range == 'this_year':
            queryset = queryset.filter(issue_date__year=today.year)

        return queryset.select_related('customer', 'branch').prefetch_related('loanitem_set', 'loanitem_set__item')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_date_range'] = self.request.GET.get('date_range', '')
        return context


class LoanCreateView(LoginRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = 'transactions/loan_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Set created_by
        form.instance.created_by = self.request.user
        
        # Set branch if not specified
        if not form.instance.branch and self.request.user.branch:
            form.instance.branch = self.request.user.branch
            
        # Ensure interest rate is set based on scheme before saving
        form.instance.interest_rate = 24.00 if form.instance.scheme == 'flexible' else 12.00
            
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('loan_detail', kwargs={'loan_number': self.object.loan_number})


class LoanDetailView(LoginRequiredMixin, DetailView):
    model = Loan
    template_name = 'transactions/loan_detail.html'
    slug_field = 'loan_number'
    slug_url_kwarg = 'loan_number'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        loan = self.get_object()
        
        # Add payments and other related data to context
        context['payments'] = loan.payments.all().order_by('-payment_date')
        context['extensions'] = loan.extensions.all().order_by('-extension_date')
        context['loan_items'] = loan.loanitem_set.all()
        
        # Process item photos for the template
        if loan.item_photos:
            try:
                # If it's a base64 string, keep it as is
                if isinstance(loan.item_photos, str) and loan.item_photos.startswith('data:image/'):
                    context['item_photos_list'] = [loan.item_photos]
                else:
                    # Handle different types of stored photo data
                    photo_list = []
                    if isinstance(loan.item_photos, str):
                        # Clean up the string
                        cleaned_data = loan.item_photos.strip()
                        if (cleaned_data.startswith('"') and cleaned_data.endswith('"')) or \
                           (cleaned_data.startswith("'") and cleaned_data.endswith("'")):
                            cleaned_data = cleaned_data[1:-1]
                        
                        try:
                            # Try parsing as JSON
                            parsed_data = json.loads(cleaned_data)
                            if isinstance(parsed_data, list):
                                photo_list.extend(parsed_data)
                            elif isinstance(parsed_data, str):
                                # Could be a JSON string within a JSON string
                                try:
                                    nested_data = json.loads(parsed_data)
                                    if isinstance(nested_data, list):
                                        photo_list.extend(nested_data)
                                    else:
                                        photo_list.append(parsed_data)
                                except json.JSONDecodeError:
                                    photo_list.append(parsed_data)
                            else:
                                photo_list.append(str(parsed_data))
                        except json.JSONDecodeError:
                            # Try ast.literal_eval as last resort
                            try:
                                import ast
                                if cleaned_data.startswith('[') and cleaned_data.endswith(']'):
                                    photo_list.extend(ast.literal_eval(cleaned_data))
                                else:
                                    photo_list.append(cleaned_data)
                            except Exception:
                                photo_list.append(cleaned_data)
                    elif isinstance(loan.item_photos, list):
                        photo_list.extend(loan.item_photos)
                    else:
                        photo_list.append(str(loan.item_photos))
                    
                    # Clean up the photo list
                    photo_list = [str(photo).strip() for photo in photo_list if photo]
                    photo_list = [photo for photo in photo_list if photo.strip()]
                    
                    # Convert any remaining base64 photos to files
                    for i, photo in enumerate(photo_list):
                        if photo.startswith('data:image/'):
                            try:
                                url = self._save_base64_photo(loan, photo, i)
                                if url:
                                    photo_list[i] = url
                            except Exception as e:
                                print(f"Error converting base64 photo {i}: {e}")
                    
                    context['item_photos_list'] = photo_list
                    
                    # Update loan's item_photos if we processed any base64 images
                    if any(not p.startswith('data:image/') for p in photo_list):
                        loan.item_photos = json.dumps(photo_list)
                        loan.save()
                    
            except Exception as e:
                print(f"Error processing photos: {str(e)}")
                context['photo_processing_error'] = str(e)
                if loan.item_photos and isinstance(loan.item_photos, str) and loan.item_photos.startswith('data:image/'):
                    context['item_photos_list'] = [loan.item_photos]
                else:
                    context['item_photos_list'] = []
        else:
            context['item_photos_list'] = []
        
        return context
    
    def _save_base64_photo(self, loan, base64_data, index):
        """Save a base64 photo to file and return the URL"""
        try:
            if not base64_data.startswith('data:image/'):
                return None
            
            format, imgstr = base64_data.split(';base64,')
            ext = format.split('/')[-1]
            
            # Decode base64 image data
            image_data = base64.b64decode(imgstr)
            
            # Generate unique filename
            filename = f"loan_{loan.loan_number}_item_{index}_{timezone.now().timestamp()}.{ext}"
            
            # Create directory path
            import os
            from django.conf import settings
            
            dir_path = os.path.join(settings.MEDIA_ROOT, 'inventory_images', str(loan.loan_number))
            os.makedirs(dir_path, exist_ok=True)
            
            # Save file
            file_path = os.path.join(dir_path, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Return URL
            return os.path.join(settings.MEDIA_URL, 'inventory_images', str(loan.loan_number), filename)
            
        except Exception as e:
            print(f"Error saving base64 photo: {str(e)}")
            return None
    


class LoanUpdateView(LoginRequiredMixin, ManagerPermissionMixin, UpdateView):
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
        
        # Process item photos for the template - Using the IMPROVED VERSION from LoanDetailView
        if loan.item_photos:
            import json
            try:
                # First, check if it's a valid JSON string
                if isinstance(loan.item_photos, str):
                    # Clean up any potential whitespace or extra quotes
                    cleaned_json = loan.item_photos.strip()
                    
                    # If the string is wrapped in extra quotes, remove them
                    if (cleaned_json.startswith('"') and cleaned_json.endswith('"')) or \
                       (cleaned_json.startswith("'") and cleaned_json.endswith("'")):
                        cleaned_json = cleaned_json[1:-1]
                    
                    # Try to parse the JSON
                    photo_list = json.loads(cleaned_json)
                    
                    # Handle the case where we get a string instead of a list
                    if isinstance(photo_list, str):
                        # It might be a JSON string within a JSON string
                        try:
                            photo_list = json.loads(photo_list)
                        except json.JSONDecodeError:
                            # If it's not valid JSON, use it as a single item in a list
                            photo_list = [photo_list]
                    
                    # Ensure it's a list
                    if not isinstance(photo_list, list):
                        photo_list = [str(photo_list)]
                    
                    # Debug output
                    print(f"Successfully parsed item photos for edit. Found {len(photo_list)} photos")
                    print(f"First photo sample: {photo_list[0][:30]}..." if photo_list else "No photos found")
                    
                    context['item_photos_list'] = photo_list
                elif isinstance(loan.item_photos, list):
                    # If it's already a list, use it directly
                    context['item_photos_list'] = loan.item_photos
                else:
                    # If it's neither a string nor a list, convert to string representation
                    context['item_photos_list'] = [str(loan.item_photos)]
            except json.JSONDecodeError as e:
                print(f"JSON decode error in edit view: {e}")
                # Last resort: try with ast.literal_eval for string representations of lists
                try:
                    import ast
                    if loan.item_photos.startswith('[') and loan.item_photos.endswith(']'):
                        photo_list = ast.literal_eval(loan.item_photos)
                        context['item_photos_list'] = photo_list
                        print(f"Parsed with ast in edit view: {len(photo_list)} photos")
                    else:
                        # Handle as a single item
                        context['item_photos_list'] = [loan.item_photos]
                except Exception as e2:
                    print(f"Fallback parsing failed in edit view: {e2}")
                    context['item_photos_list'] = [loan.item_photos]
        else:
            print("No item photos found for this loan in edit view")
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
                photos_array = json.loads(item_photos_data)
                
                # Ensure it's a properly formatted array of strings
                if isinstance(photos_array, list):
                    # Limit the size of each photo if needed
                    limited_photos = []
                    for photo in photos_array:
                        if isinstance(photo, str):
                            # Add to the limited photos list
                            limited_photos.append(photo)
                    
                    # Save as JSON string
                    form.instance.item_photos = json.dumps(limited_photos)
                else:
                    form.instance.item_photos = "[]"  # Empty array if format is incorrect
            except json.JSONDecodeError:
                print("Invalid item_photos JSON format, not saving")
                # Preserve existing photos
                if form.instance.pk and form.instance.item_photos:
                    # Don't modify existing photos
                    pass
                else:
                    form.instance.item_photos = "[]"  # Empty array as fallback
        
        # Record who updated the loan
        form.instance.last_updated_by = self.request.user
        
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
            if isinstance(loan.customer_face_capture, str):
                # Handle various formats of base64 images
                if loan.customer_face_capture.startswith('data:image/'):
                    # Extract the base64 part after the comma
                    format_prefix, base64_data = loan.customer_face_capture.split(';base64,', 1)
                    customer_photo = base64_data
                else:
                    # Maybe it's already just the base64 string without prefix
                    customer_photo = loan.customer_face_capture
                
        # Process item photos (parse JSON string if needed)
        item_photos = []
        if hasattr(loan, 'item_photos') and loan.item_photos:
            import json
            try:
                # If stored as JSON string
                if isinstance(loan.item_photos, str):
                    # Clean up any potential whitespace or extra quotes
                    cleaned_data = loan.item_photos.strip()
                    if (cleaned_data.startswith('"') and cleaned_data.endswith('"')) or \
                       (cleaned_data.startswith("'") and cleaned_data.endswith("'")):
                        cleaned_data = cleaned_data[1:-1]
                    
                    # Try parsing as JSON
                    photo_list = json.loads(cleaned_data)
                    
                    # Process each photo in the list
                    for photo in photo_list:
                        if isinstance(photo, str):
                            if photo.startswith('data:image/'):
                                # Extract the base64 part after the comma
                                format_prefix, base64_data = photo.split(';base64,', 1)
                                item_photos.append(base64_data)
                            elif photo.startswith('/media/'):
                                # For file URLs, we need to read the file and convert to base64
                                try:
                                    import os
                                    from django.conf import settings
                                    import base64
                                    
                                    # Clean up the URL to get the file path
                                    file_path = os.path.join(settings.MEDIA_ROOT, photo.replace('/media/', ''))
                                    
                                    # Read the file and convert to base64
                                    if os.path.exists(file_path):
                                        with open(file_path, 'rb') as f:
                                            file_data = f.read()
                                            base64_data = base64.b64encode(file_data).decode('utf-8')
                                            item_photos.append(base64_data)
                                    else:
                                        print(f"Image file not found: {file_path}")
                                except Exception as e:
                                    print(f"Error processing image at path {photo}: {str(e)}")
                            else:
                                # Assume it's already a base64 string
                                item_photos.append(photo)
                
                # If no photos were successfully processed, try alternate methods
                if not item_photos:
                    # If we failed to process JSON, maybe it's a single base64 string
                    if loan.item_photos.startswith('data:image/'):
                        format_prefix, base64_data = loan.item_photos.split(';base64,', 1)
                        item_photos.append(base64_data)
            
            except (json.JSONDecodeError, AttributeError, ValueError) as e:
                # Log the error
                print(f"Error processing item_photos in loan agreement: {str(e)}")
                
                # If it's not valid JSON, maybe it's a direct base64 string
                if isinstance(loan.item_photos, str) and loan.item_photos.startswith('data:image/'):
                    format_prefix, base64_data = loan.item_photos.split(';base64,', 1)
                    item_photos.append(base64_data)
        
        # Debug logging
        print(f"Item photos processed for loan agreement: {len(item_photos)} photos found")
        
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
            
            # Generate filename with customer name and loan item name only (no loan ID)
            customer_name = f"{loan.customer.first_name}_{loan.customer.last_name}"
            
            # Get the first item name as part of the filename
            item_name = "NoItem"
            if loan_items:
                # If there are multiple items, use the first one's name
                first_item = loan_items.first()
                if first_item and first_item.item:
                    # Clean the item name to make it URL-safe
                    item_name = first_item.item.name.replace(' ', '_')
            
            # Format the filename: CustomerName_ItemName.pdf (removed loan number)
            filename = f"{customer_name}_{item_name}.pdf"
            
            # Make the filename URL-safe (replace special characters)
            import re
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # If PDF generation fails
        return HttpResponse("Error generating PDF", status=400)

def number_to_words(request, number):
    """Convert number to words in Indian format"""
    try:
        # Convert to float and then format to handle decimals properly
        amount = float(number)
        words = num2words(amount, lang='en_IN').title()
        return JsonResponse({'words': words})
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid number'}, status=400)
