
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from .models import GoldRate


#Dashboard View
@login_required
def dashboard(request):
    rate = GoldRate.objects.order_by('-updated_at').first()
    return render(request, "staff/dashboard.html", {"rate": rate})


#Update Rate View
@login_required
def update_rate(request):
    if request.method == "POST":
        rate_24k = request.POST["rate_24k"]
        rate_22k = request.POST["rate_22k"]

        GoldRate.objects.create(
            rate_24k=rate_24k,
            rate_22k=rate_22k
        )

        return redirect("dashboard")
    

    

#Create API Endpoint in Django
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import GoldRate

@csrf_exempt
def gold_rate_api(request):
    if request.method == "GET":
        rate = GoldRate.objects.order_by('-updated_at').first()

        if not rate:
            return JsonResponse({"error": "No rate available"}, status=404)

        return JsonResponse({
            "rate_24k": str(rate.rate_24k),
            "rate_22k": str(rate.rate_22k),
        })

    return JsonResponse({"error": "Only GET allowed"}, status=405)
# def gold_rate_api(request):
#     return JsonResponse({"debug": "THIS VIEW IS HIT"})