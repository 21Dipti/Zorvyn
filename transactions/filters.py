import django_filters

from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte', label='Date from (YYYY-MM-DD)')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte', label='Date to (YYYY-MM-DD)')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte', label='Minimum amount')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte', label='Maximum amount')
    category_name = django_filters.CharFilter(
        field_name='category__name', lookup_expr='icontains', label='Category name (partial match)'
    )
    year = django_filters.NumberFilter(field_name='date', lookup_expr='year', label='Year')
    month = django_filters.NumberFilter(field_name='date', lookup_expr='month', label='Month (1-12)')

    class Meta:
        model = Transaction
        fields = {
            'transaction_type': ['exact'],
            'category': ['exact'],
        }
