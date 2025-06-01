from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required

from .models import Item, Category, ItemImage
from .forms import ItemForm, CategoryForm, ItemImageForm


class ItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    permission_required = 'inventory.view_item'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user's branch if not a superuser
        if not self.request.user.is_superuser and self.request.user.branch:
            queryset = queryset.filter(branch=self.request.user.branch)
        
        # Filter by search query
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(item_id__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query)
            )
        
        # Filter by category
        category_id = self.request.GET.get('category', '')
        if category_id and category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # Sort results
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by:
            queryset = queryset.order_by(sort_by)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['total_items'] = self.get_queryset().count()
        context['available_items'] = self.get_queryset().filter(status='available').count()
        context['pawned_items'] = self.get_queryset().filter(status='pawned').count()
        context['sold_items'] = self.get_queryset().filter(status='sold').count()
        
        # Add search params for maintaining filters during pagination
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['sort_by'] = self.request.GET.get('sort', '-created_at')
        
        return context


class ItemDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'
    permission_required = 'inventory.view_item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        
        # Add loan information if item is pawned
        if item.status == 'pawned' and hasattr(item, 'loan'):
            context['loan'] = item.loan
            
        # Add related items (same category)
        context['related_items'] = Item.objects.filter(
            category=item.category, 
            status='available'
        ).exclude(pk=item.pk)[:4]
        
        # Add item images
        context['images'] = item.images.all()
        
        return context


class ItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Item
    template_name = 'inventory/item_form.html'
    form_class = ItemForm
    permission_required = 'inventory.add_item'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the user to filter branches
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Set the created_by field
        form.instance.created_by = self.request.user
        
        # If user belongs to a branch and no branch selected, use user's branch
        if not form.instance.branch and self.request.user.branch:
            form.instance.branch = self.request.user.branch
            
        response = super().form_valid(form)
        messages.success(self.request, f'Item "{form.instance.name}" has been created successfully.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('item_detail', kwargs={'pk': self.object.pk})


class ItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Item
    template_name = 'inventory/item_form.html'
    form_class = ItemForm
    permission_required = 'inventory.change_item'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Update the modified_by and modified_at fields
        form.instance.modified_by = self.request.user
        form.instance.modified_at = timezone.now()
        
        response = super().form_valid(form)
        messages.success(self.request, f'Item "{form.instance.name}" has been updated successfully.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('item_detail', kwargs={'pk': self.object.pk})


class ItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Item
    template_name = 'inventory/item_confirm_delete.html'
    context_object_name = 'item'
    permission_required = 'inventory.delete_item'
    success_url = reverse_lazy('item_list')
    
    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        messages.success(request, f'Item "{item.name}" has been deleted successfully.')
        return super().delete(request, *args, **kwargs)


class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    permission_required = 'inventory.view_category'
    
    def get_queryset(self):
        return Category.objects.annotate(item_count=Count('items'))
    

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Category
    template_name = 'inventory/category_form.html'
    form_class = CategoryForm
    permission_required = 'inventory.add_category'
    success_url = reverse_lazy('category_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Category "{form.instance.name}" has been created successfully.')
        return response


class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Category
    template_name = 'inventory/category_form.html'
    form_class = CategoryForm
    permission_required = 'inventory.change_category'
    success_url = reverse_lazy('category_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Category "{form.instance.name}" has been updated successfully.')
        return response


class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    context_object_name = 'category'
    permission_required = 'inventory.delete_category'
    success_url = reverse_lazy('category_list')
    
    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(request, f'Category "{category.name}" has been deleted successfully.')
        return super().delete(request, *args, **kwargs)


def add_item_image(request, item_id):
    if not request.user.has_perm('inventory.change_item'):
        messages.error(request, "You don't have permission to add images.")
        return redirect('item_detail', pk=item_id)
    
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        form = ItemImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.item = item
            image.uploaded_by = request.user
            image.save()
            messages.success(request, "Image added successfully.")
            return redirect('item_detail', pk=item_id)
    else:
        form = ItemImageForm()
    
    return render(request, 'inventory/add_item_image.html', {'form': form, 'item': item})


def delete_item_image(request, image_id):
    if not request.user.has_perm('inventory.change_item'):
        messages.error(request, "You don't have permission to delete images.")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    image = get_object_or_404(ItemImage, id=image_id)
    item_id = image.item.id
    image.delete()
    
    if request.is_ajax():
        return JsonResponse({'success': True})
        
    messages.success(request, "Image deleted successfully.")
    return redirect('item_detail', pk=item_id)


@login_required
@permission_required('inventory.view_item')
def inventory_search(request):
    """Search inventory items and return results"""
    search_query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    items = Item.objects.all()
    
    # Filter by user's branch if not a superuser
    if not request.user.is_superuser and request.user.branch:
        items = items.filter(branch=request.user.branch)
    
    # Apply search filters
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(item_id__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(model__icontains=search_query)
        )
    
    # Filter by category if provided
    if category_id and category_id.isdigit():
        items = items.filter(category_id=category_id)
    
    # Filter by status if provided
    if status:
        items = items.filter(status=status)
    
    # Get all categories for the filter dropdown
    categories = Category.objects.all()
    
    context = {
        'items': items,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_status': status,
        'total_results': items.count()
    }
    
    return render(request, 'inventory/search_results.html', context)
