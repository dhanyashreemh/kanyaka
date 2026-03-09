# from django import forms

# class ProductForm(forms.Form):

#     title = forms.CharField(max_length=255)

#     description = forms.CharField(
#         widget=forms.Textarea
#     )

#     price = forms.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )

#     tags = forms.CharField(
#         required=False
#     )

#     image = forms.ImageField(   # 👈 ADD THIS
#         required=False
#     )

#     image_url = forms.URLField(
#         required=False
#     )

#     def clean(self):
#         cleaned_data = super().clean()
#         image = cleaned_data.get("image")
#         image_url = cleaned_data.get("image_url")

#         if not image and not image_url:
#             raise forms.ValidationError(
#                 "Please upload an image or provide an image URL."
#             )

#         if image and image_url:
#             raise forms.ValidationError(
#                 "Please use only one: upload image OR image URL."
#             )

#         return cleaned_data

#2

# 

#3
from django import forms

class ProductForm(forms.Form):

    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea)

    jewelry_type = forms.CharField(required=False)
    metal_type = forms.CharField(required=False)
    purity = forms.CharField(required=False)
    weight = forms.DecimalField(required=False)
    stone_type = forms.CharField(required=False)

    collection = forms.CharField(required=False)
    occasion = forms.CharField(required=False)
    tags = forms.CharField(required=False)

    price = forms.DecimalField(max_digits=10, decimal_places=2)
    compare_price = forms.DecimalField(required=False)
    unit_price = forms.DecimalField(required=False)

    charge_tax = forms.BooleanField(required=False)

    cost_per_item = forms.DecimalField(required=False)

    inventory_tracked = forms.BooleanField(required=False)
    quantity = forms.IntegerField(required=False)

    sku = forms.CharField(required=False)
    barcode = forms.CharField(required=False)

    sell_out_of_stock = forms.BooleanField(required=False)