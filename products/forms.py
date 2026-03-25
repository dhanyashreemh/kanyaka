from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ["shopify_product_id", "shopify_variant_id"]

        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "jewelry_type": forms.TextInput(attrs={"class": "form-control"}),
            "metal_type": forms.TextInput(attrs={"class": "form-control"}),
            "purity": forms.TextInput(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={"class": "form-control"}),
            "stone_type": forms.TextInput(attrs={"class": "form-control"}),
            "collection": forms.TextInput(attrs={"class": "form-control"}),
            "occasion": forms.TextInput(attrs={"class": "form-control"}),
            "tags": forms.TextInput(attrs={"class": "form-control"}),

            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "compare_price": forms.NumberInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control"}),
            "cost_per_item": forms.NumberInput(attrs={"class": "form-control"}),

            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "barcode": forms.TextInput(attrs={"class": "form-control"}),

            "charge_tax": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "inventory_tracked": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sell_out_of_stock": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }