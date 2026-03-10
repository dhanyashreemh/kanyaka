from django.shortcuts import render
from .forms import WhyForm

def why_view(request):

    form = WhyForm()

    if request.method == "POST":

        form = WhyForm(request.POST)

        if form.is_valid():

            title = form.cleaned_data["title"]
            description = form.cleaned_data["description"]
            price = form.cleaned_data["price"]
            track_inventory = form.cleaned_data["track_inventory"]

            print(title, description, price, track_inventory)

    return render(request, "why.html", {"form": form})