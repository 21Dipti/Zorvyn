from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsAdminRole, IsAnalystOrAdmin, IsOwnerOrAdmin
from .filters import TransactionFilter
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer


# ── Category views ─────────────────────────────────────────────────────────────

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  — any authenticated user may list categories.
    POST — admin only (categories are shared, system-level resources).
    """

    serializer_class = CategorySerializer
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        return Category.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [IsAuthenticated()]


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET          — any authenticated user.
    PATCH/DELETE — admin only.
    """

    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.transactions.exists():
            return Response(
                {'detail': 'Cannot delete a category that has associated transactions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


# ── Transaction views ──────────────────────────────────────────────────────────

class TransactionListCreateView(generics.ListCreateAPIView):
    """
    GET  — viewers, analysts, and admins may list their own transactions.
           Admins see all transactions.
    POST — analysts and admins only (viewers are read-only).
    """

    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TransactionFilter
    search_fields = ['notes', 'category__name']
    ordering_fields = ['date', 'amount', 'created_at', 'transaction_type']
    ordering = ['-date']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAnalystOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Transaction.objects.select_related('user', 'category')
        if user.is_admin_role:
            return qs.all()
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET          — owner or admin.
    PATCH        — analyst (owner) or admin; viewers are forbidden.
    DELETE       — analyst (owner) or admin; viewers are forbidden.
    """

    serializer_class = TransactionSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        return [IsAuthenticated(), IsOwnerOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = Transaction.objects.select_related('user', 'category')
        if user.is_admin_role:
            return qs.all()
        return qs.filter(user=user)

    def update(self, request, *args, **kwargs):
        if not request.user.is_analyst_or_above:
            return Response(
                {'detail': 'Viewers cannot modify transactions.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        kwargs['partial'] = True  # always partial (PATCH only)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_analyst_or_above:
            return Response(
                {'detail': 'Viewers cannot delete transactions.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
