from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Integration, POSIntegration, AccountingIntegration, CRMIntegration, WebhookEndpoint, IntegrationLog
from .forms import IntegrationForm, POSIntegrationForm, AccountingIntegrationForm, CRMIntegrationForm

class IntegrationListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/integration_list.html'
    context_object_name = 'integrations'
    model = Integration

class IntegrationDetailView(LoginRequiredMixin, DetailView):
    template_name = 'integrations/integration_detail.html'
    context_object_name = 'integration'
    model = Integration

class IntegrationCreateView(LoginRequiredMixin, CreateView):
    model = Integration
    form_class = IntegrationForm
    template_name = 'integrations/integration_form.html'
    success_url = reverse_lazy('integration_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            if self.request.POST.get('integration_type') == 'pos':
                context['pos_form'] = POSIntegrationForm(self.request.POST)
            elif self.request.POST.get('integration_type') == 'accounting':
                context['accounting_form'] = AccountingIntegrationForm(self.request.POST)
            elif self.request.POST.get('integration_type') == 'crm':
                context['crm_form'] = CRMIntegrationForm(self.request.POST)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        integration_type = form.cleaned_data['integration_type']
        
        # Create the specific integration type details
        if integration_type == 'pos':
            pos_form = POSIntegrationForm(self.request.POST)
            if pos_form.is_valid():
                pos_integration = pos_form.save(commit=False)
                pos_integration.integration = self.object
                pos_integration.save()
        elif integration_type == 'accounting':
            accounting_form = AccountingIntegrationForm(self.request.POST)
            if accounting_form.is_valid():
                accounting_integration = accounting_form.save(commit=False)
                accounting_integration.integration = self.object
                accounting_integration.save()
        elif integration_type == 'crm':
            crm_form = CRMIntegrationForm(self.request.POST)
            if crm_form.is_valid():
                crm_integration = crm_form.save(commit=False)
                crm_integration.integration = self.object
                crm_integration.save()

        messages.success(self.request, f'Integration "{self.object.name}" has been created successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class IntegrationUpdateView(LoginRequiredMixin, UpdateView):
    model = Integration
    form_class = IntegrationForm
    template_name = 'integrations/integration_form.html'
    success_url = reverse_lazy('integration_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            if self.request.POST.get('integration_type') == 'pos':
                context['pos_form'] = POSIntegrationForm(self.request.POST, instance=self.object.pos_details)
            elif self.request.POST.get('integration_type') == 'accounting':
                context['accounting_form'] = AccountingIntegrationForm(self.request.POST, instance=self.object.accounting_details)
            elif self.request.POST.get('integration_type') == 'crm':
                context['crm_form'] = CRMIntegrationForm(self.request.POST, instance=self.object.crm_details)
        else:
            if self.object.integration_type == 'pos':
                context['pos_form'] = POSIntegrationForm(instance=self.object.pos_details)
            elif self.object.integration_type == 'accounting':
                context['accounting_form'] = AccountingIntegrationForm(instance=self.object.accounting_details)
            elif self.object.integration_type == 'crm':
                context['crm_form'] = CRMIntegrationForm(instance=self.object.crm_details)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        integration_type = form.cleaned_data['integration_type']
        
        # Update the specific integration type details
        if integration_type == 'pos':
            pos_form = POSIntegrationForm(self.request.POST, instance=self.object.pos_details)
            if pos_form.is_valid():
                pos_integration = pos_form.save(commit=False)
                pos_integration.integration = self.object
                pos_integration.save()
        elif integration_type == 'accounting':
            accounting_form = AccountingIntegrationForm(self.request.POST, instance=self.object.accounting_details)
            if accounting_form.is_valid():
                accounting_integration = accounting_form.save(commit=False)
                accounting_integration.integration = self.object
                accounting_integration.save()
        elif integration_type == 'crm':
            crm_form = CRMIntegrationForm(self.request.POST, instance=self.object.crm_details)
            if crm_form.is_valid():
                crm_integration = crm_form.save(commit=False)
                crm_integration.integration = self.object
                crm_integration.save()

        messages.success(self.request, f'Integration "{self.object.name}" has been updated successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class IntegrationDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/integration_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['integration_id'] = self.kwargs.get('pk')
        return context


class IntegrationToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Will be implemented with actual Integration model
        return JsonResponse({'status': 'success'})


class POSIntegrationListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/pos_integration_list.html'
    context_object_name = 'integrations'
    
    def get_queryset(self):
        # Will be implemented with actual POSIntegration model
        return []


class POSIntegrationCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/pos_integration_form.html'


class POSIntegrationUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/pos_integration_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['integration_id'] = self.kwargs.get('pk')
        return context


class AccountingIntegrationListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/accounting_integration_list.html'
    context_object_name = 'integrations'
    
    def get_queryset(self):
        # Will be implemented with actual AccountingIntegration model
        return []


class AccountingIntegrationCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/accounting_integration_form.html'


class AccountingIntegrationUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/accounting_integration_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['integration_id'] = self.kwargs.get('pk')
        return context


class CRMIntegrationListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/crm_integration_list.html'
    context_object_name = 'integrations'
    
    def get_queryset(self):
        # Will be implemented with actual CRMIntegration model
        return []


class CRMIntegrationCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/crm_integration_form.html'


class CRMIntegrationUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/crm_integration_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['integration_id'] = self.kwargs.get('pk')
        return context


class WebhookListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/webhook_list.html'
    context_object_name = 'webhooks'
    
    def get_queryset(self):
        # Will be implemented with actual Webhook model
        return []


class WebhookCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/webhook_form.html'


class WebhookUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/webhook_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['webhook_id'] = self.kwargs.get('pk')
        return context


class WebhookDeleteView(LoginRequiredMixin, TemplateView):
    template_name = 'integrations/webhook_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['webhook_id'] = self.kwargs.get('pk')
        return context


class WebhookReceiveView(View):
    def post(self, request, endpoint_url):
        # This would process incoming webhook data
        return JsonResponse({'status': 'received'})


class IntegrationLogListView(LoginRequiredMixin, ListView):
    template_name = 'integrations/integration_log_list.html'
    context_object_name = 'logs'
    
    def get_queryset(self):
        # Will be implemented with actual IntegrationLog model
        return []


class IntegrationLogDetailView(LoginRequiredMixin, ListView):
    template_name = 'integrations/integration_log_detail.html'
    context_object_name = 'logs'
    
    def get_queryset(self):
        # Will be implemented with actual IntegrationLog model
        return []


class IntegrationSyncView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # This would implement integration sync logic
        return JsonResponse({'status': 'success'})
