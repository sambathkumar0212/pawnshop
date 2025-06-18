from django.urls import path
from . import views

urlpatterns = [
    path('', views.SchemeListView.as_view(), name='scheme_list'),
    path('<int:pk>/', views.SchemeDetailView.as_view(), name='scheme_detail'),
    path('create/', views.SchemeCreateView.as_view(), name='scheme_create'),
    path('<int:pk>/update/', views.SchemeUpdateView.as_view(), name='scheme_update'),
    path('<int:pk>/delete/', views.SchemeDeleteView.as_view(), name='scheme_delete'),
    path('<int:pk>/json/', views.SchemeJsonView.as_view(), name='scheme_json'),
]