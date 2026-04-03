from django.shortcuts import render


def app_view(request):
    """Single entry-point — the JS router handles everything client-side."""
    return render(request, 'frontend/app.html')
