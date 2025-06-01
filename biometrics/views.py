from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from .models import BiometricSetting, FaceEnrollment, CustomerFaceEnrollment, FaceAuthLog
from branches.models import Branch
from django.contrib.auth import get_user_model

User = get_user_model()

# Placeholder views for biometrics functionality
class UserFaceEnrollmentView(LoginRequiredMixin, TemplateView):
    template_name = 'biometrics/user_face_enrollment.html'


class UserFaceCaptureView(LoginRequiredMixin, View):
    def post(self, request):
        # This would implement the face capture logic
        return JsonResponse({'status': 'success'})


class UserFaceVerificationView(LoginRequiredMixin, View):
    def post(self, request):
        # This would implement face verification logic
        return JsonResponse({'status': 'success', 'verified': True})


class CustomerFaceEnrollmentView(LoginRequiredMixin, TemplateView):
    template_name = 'biometrics/customer_face_enrollment.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_id'] = self.kwargs.get('customer_id')
        return context


class CustomerFaceCaptureView(LoginRequiredMixin, View):
    def post(self, request, customer_id):
        # This would implement the customer face capture logic
        return JsonResponse({'status': 'success'})


class CustomerFaceVerificationView(LoginRequiredMixin, View):
    def post(self, request, customer_id):
        # This would implement customer face verification logic
        return JsonResponse({'status': 'success', 'verified': True})


class FaceLoginView(View):
    def get(self, request):
        return render(request, 'biometrics/face_login.html')
    
    def post(self, request):
        # This would implement face login logic
        return JsonResponse({'status': 'success'})


class CustomerIdentificationView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'biometrics/customer_identify.html')
    
    def post(self, request):
        # This would implement customer identification logic
        return JsonResponse({'status': 'success'})


class BiometricSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'biometrics/biometric_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get global settings (using first branch as default if exists)
        context['settings'] = BiometricSetting.objects.first()
        context['branches'] = Branch.objects.prefetch_related('biometric_settings').all()

        # Calculate enrollment statistics
        total_staff = User.objects.filter(is_staff=True).count()
        staff_enrolled = FaceEnrollment.objects.filter(user__is_staff=True, is_active=True).count()
        total_customers = User.objects.filter(is_staff=False).count()
        customers_enrolled = CustomerFaceEnrollment.objects.filter(is_active=True).count()

        context.update({
            'total_staff': total_staff,
            'staff_enrolled': staff_enrolled,
            'total_customers': total_customers,
            'customers_enrolled': customers_enrolled,
            'staff_enrolled_percentage': (staff_enrolled / total_staff * 100) if total_staff > 0 else 0,
            'customers_enrolled_percentage': (customers_enrolled / total_customers * 100) if total_customers > 0 else 0,
        })

        return context

    def post(self, request, *args, **kwargs):
        try:
            # Get or create global settings
            settings = BiometricSetting.objects.first()
            if not settings:
                # Create settings for the first branch if no settings exist
                first_branch = Branch.objects.first()
                if not first_branch:
                    messages.error(request, "No branches exist in the system. Please create a branch first.")
                    return redirect('biometric_settings')
                settings = BiometricSetting(branch=first_branch)

            # Update settings from form data
            settings.face_recognition_enabled = request.POST.get('face_recognition_enabled') == 'on'
            settings.face_recognition_required_for_staff = request.POST.get('face_recognition_required_for_staff') == 'on'
            settings.face_recognition_required_for_customers = request.POST.get('face_recognition_required_for_customers') == 'on'
            settings.fingerprint_enabled = request.POST.get('fingerprint_enabled') == 'on'
            
            # Handle threshold value
            threshold = request.POST.get('face_recognition_threshold')
            if threshold:
                settings.face_recognition_threshold = float(threshold)

            settings.updated_by = request.user
            settings.save()

            messages.success(request, "Biometric settings updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating settings: {str(e)}")

        return redirect('biometric_settings')


class BranchBiometricSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'biometrics/branch_biometric_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['branch_id'] = self.kwargs.get('branch_id')
        return context


class BiometricLogListView(LoginRequiredMixin, ListView):
    template_name = 'biometrics/biometric_logs.html'
    context_object_name = 'logs'
    
    def get_queryset(self):
        # This would fetch actual biometric logs
        return []
