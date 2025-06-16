from django.urls import path
from . import views

urlpatterns = [
    # Scheme CRUD
    path('schemes/', views.SchemeListView.as_view(), name='scheme_list'),
    path('schemes/create/', views.SchemeCreateView.as_view(), name='scheme_create'),
    path('schemes/<int:pk>/', views.SchemeDetailView.as_view(), name='scheme_detail'),
    path('schemes/<int:pk>/edit/', views.SchemeUpdateView.as_view(), name='scheme_update'),
    path('schemes/<int:pk>/delete/', views.SchemeDeleteView.as_view(), name='scheme_delete'),
    path('schemes/<int:pk>/toggle/', views.toggle_scheme_status, name='toggle_scheme_status'),
    
    # Scheme Statistics
    path('schemes/stats/', views.SchemeStatsView.as_view(), name='scheme_stats'),
    
    # API endpoints
    path('api/schemes/<int:scheme_id>/', views.SchemeAPIView.as_view(), name='scheme_api'),
    
    # Scheme notification management
    path('notifications/', views.SchemeNotificationListView.as_view(), name='scheme_notification_list'),
    path('notifications/add/', views.SchemeNotificationCreateView.as_view(), name='scheme_notification_create'),
    path('notifications/<int:pk>/', views.SchemeNotificationDetailView.as_view(), name='scheme_notification_detail'),
    path('notifications/<int:pk>/edit/', views.SchemeNotificationUpdateView.as_view(), name='scheme_notification_update'),
    path('notifications/<int:pk>/delete/', views.SchemeNotificationDeleteView.as_view(), name='scheme_notification_delete'),
]