
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
    

    

