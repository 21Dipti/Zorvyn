from django.urls import path

from .views import (
    CategoryBreakdownView,
    ExportView,
    MonthlyTotalsView,
    RecentActivityView,
    SummaryView,
)

urlpatterns = [
    path('summary/', SummaryView.as_view(), name='analytics_summary'),
    path('by-category/', CategoryBreakdownView.as_view(), name='analytics_by_category'),
    path('monthly/', MonthlyTotalsView.as_view(), name='analytics_monthly'),
    path('recent/', RecentActivityView.as_view(), name='analytics_recent'),
    path('export/', ExportView.as_view(), name='analytics_export'),
]
