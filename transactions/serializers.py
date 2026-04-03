from rest_framework import serializers

from .models import Category, Transaction


class CategorySerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'transaction_count', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_transaction_count(self, obj):
        return obj.transactions.count()


class CategoryMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class TransactionSerializer(serializers.ModelSerializer):
    category_detail = CategoryMinimalSerializer(source='category', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Transaction
        fields = (
            'id',
            'user',
            'user_username',
            'amount',
            'transaction_type',
            'category',
            'category_detail',
            'date',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'user_username', 'created_at', 'updated_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_transaction_type(self, value):
        if value not in (Transaction.INCOME, Transaction.EXPENSE):
            raise serializers.ValidationError(
                f'transaction_type must be "{Transaction.INCOME}" or "{Transaction.EXPENSE}".'
            )
        return value
