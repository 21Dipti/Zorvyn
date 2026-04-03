from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListCreateView,
    TransactionDetailView,
    TransactionListCreateView,
)

urlpatterns = [
    path('', TransactionListCreateView.as_view(), name='transaction_list'),
    path('<uuid:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('categories/', CategoryListCreateView.as_view(), name='category_list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
]
