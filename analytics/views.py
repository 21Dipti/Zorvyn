import csv
from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAnalystOrAdmin
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer


def _build_queryset(request):
    """
    Return a transaction queryset scoped to the appropriate user.

    - Admin: all transactions; optionally filtered by ?user_id=
    - Everyone else: only their own transactions.
    """
    qs = Transaction.objects.select_related('user', 'category')
    user = request.user

    if user.is_admin_role:
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
    else:
        qs = qs.filter(user=user)

    return qs


class SummaryView(APIView):
    """
    Financial summary accessible to all authenticated users.

    Viewers and analysts see their own data; admins see all (or a specific
    user's data when ?user_id= is provided).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _build_queryset(request)

        total_income = (
            qs.filter(transaction_type=Transaction.INCOME).aggregate(total=Sum('amount'))['total']
            or Decimal('0')
        )
        total_expenses = (
            qs.filter(transaction_type=Transaction.EXPENSE).aggregate(total=Sum('amount'))['total']
            or Decimal('0')
        )

        return Response({
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': total_income - total_expenses,
            'transaction_count': qs.count(),
            'income_count': qs.filter(transaction_type=Transaction.INCOME).count(),
            'expense_count': qs.filter(transaction_type=Transaction.EXPENSE).count(),
        })


class CategoryBreakdownView(APIView):
    """
    Per-category totals; available to analysts and admins only.
    Returns overall totals plus separate income/expense breakdowns.
    """

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        qs = _build_queryset(request)

        overall = (
            qs.values('category__id', 'category__name')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )

        income_by_category = (
            qs.filter(transaction_type=Transaction.INCOME)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        expense_by_category = (
            qs.filter(transaction_type=Transaction.EXPENSE)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        return Response({
            'overall': [
                {
                    'category_id': row['category__id'],
                    'category_name': row['category__name'] or 'Uncategorized',
                    'total': row['total'],
                    'count': row['count'],
                }
                for row in overall
            ],
            'income_by_category': [
                {
                    'category': row['category__name'] or 'Uncategorized',
                    'total': row['total'],
                }
                for row in income_by_category
            ],
            'expense_by_category': [
                {
                    'category': row['category__name'] or 'Uncategorized',
                    'total': row['total'],
                }
                for row in expense_by_category
            ],
        })


class MonthlyTotalsView(APIView):
    """
    Month-by-month income, expenses, and balance for a given year.
    Defaults to the current year. Pass ?year=YYYY to change.
    Analysts and admins only.
    """

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        qs = _build_queryset(request)

        try:
            year = int(request.query_params.get('year', date.today().year))
        except (ValueError, TypeError):
            year = date.today().year

        monthly_qs = (
            qs.filter(date__year=year)
            .annotate(month=TruncMonth('date'))
            .values('month')
            .annotate(
                income=Sum('amount', filter=Q(transaction_type=Transaction.INCOME)),
                expenses=Sum('amount', filter=Q(transaction_type=Transaction.EXPENSE)),
                count=Count('id'),
            )
            .order_by('month')
        )

        months = []
        for row in monthly_qs:
            income = row['income'] or Decimal('0')
            expenses = row['expenses'] or Decimal('0')
            months.append({
                'month': row['month'].strftime('%Y-%m'),
                'income': income,
                'expenses': expenses,
                'balance': income - expenses,
                'count': row['count'],
            })

        return Response({'year': year, 'months': months})


class RecentActivityView(APIView):
    """
    Latest N transactions, ordered by date descending.
    Accessible to all authenticated users. Pass ?limit=N (max 100, default 10).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            limit = min(int(request.query_params.get('limit', 10)), 100)
        except (ValueError, TypeError):
            limit = 10

        qs = _build_queryset(request).order_by('-date', '-created_at')[:limit]
        serializer = TransactionSerializer(qs, many=True)
        return Response(serializer.data)


class ExportView(APIView):
    """
    Export transactions as a CSV file.
    Analysts and admins only. Supports the same ?user_id filter for admins.
    """

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        qs = _build_queryset(request).order_by('-date')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'User', 'Date', 'Type', 'Amount', 'Category', 'Notes', 'Created At'])

        for txn in qs:
            writer.writerow([
                str(txn.id),
                txn.user.username,
                txn.date.isoformat(),
                txn.transaction_type,
                str(txn.amount),
                txn.category.name if txn.category else '',
                txn.notes,
                txn.created_at.isoformat(),
            ])

        return response
