"""Custom error handlers (Unit II - Error Handling).

They are wired up in urls.py (handler400/403/404/500) and are only used when
DEBUG=False. Each renders monitoring/templates/errors/<code>.html.
"""
from django.shortcuts import render


def bad_request(request, exception=None):
    return render(request, "errors/400.html", status=400)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", {"message": str(exception) if exception else ""}, status=403)


def page_not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error(request):
    return render(request, "errors/500.html", status=500)
