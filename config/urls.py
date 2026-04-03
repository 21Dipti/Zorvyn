from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('', include('frontend.urls')),
] + static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
