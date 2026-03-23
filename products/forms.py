from django import forms

from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ["shopify_product_id", "shopify_variant_id"]

    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={"class":"form-control"})
    )

    jewelry_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    metal_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    purity = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    weight = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    stone_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    collection = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    occasion = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    compare_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    cost_per_item = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class":"form-control"})
    )

    sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    barcode = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class":"form-control"})
    )

    charge_tax = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class":"form-check-input"})
    )

    inventory_tracked = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class":"form-check-input"})
    )

    sell_out_of_stock = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class":"form-check-input"})
    )