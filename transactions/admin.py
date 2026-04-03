from django.contrib import admin

from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'category', 'date', 'created_at')
    list_filter = ('transaction_type', 'category', 'date')
    search_fields = ('user__username', 'notes', 'category__name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    raw_id_fields = ('user', 'category')
