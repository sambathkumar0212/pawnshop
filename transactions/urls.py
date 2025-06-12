from django.urls import path
from . import views

urlpatterns = [
    # Loans
    path('loans/', views.LoanListView.as_view(), name='loan_list'),
    path('loans/add/', views.LoanCreateView.as_view(), name='loan_create'),
    path('loans/<str:loan_number>/', views.LoanDetailView.as_view(), name='loan_detail'),
    path('loans/<str:loan_number>/edit/', views.LoanUpdateView.as_view(), name='loan_update'),
    path('loans/<str:loan_number>/payment/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('loans/<str:loan_number>/extend/', views.LoanExtensionCreateView.as_view(), name='loan_extend'),
    path('loans/<str:loan_number>/foreclose/', views.LoanForecloseView.as_view(), name='loan_foreclose'),
    path('loans/<str:loan_number>/document/', views.LoanDocumentView.as_view(), name='loan_document'),
    
    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    
    # Sales
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/add/', views.SaleCreateView.as_view(), name='sale_create'),
    path('sales/<str:transaction_number>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('sales/<str:transaction_number>/edit/', views.SaleUpdateView.as_view(), name='sale_update'),
    path('sales/<str:transaction_number>/cancel/', views.SaleCancelView.as_view(), name='sale_cancel'),
    path('sales/<str:transaction_number>/receipt/', views.SaleReceiptView.as_view(), name='sale_receipt'),

    # Utilities
    path('number_to_words/<str:number>/', views.number_to_words, name='number_to_words'),
]