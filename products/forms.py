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



from django import forms


class ProductForm(forms.Form):

    # BASIC PRODUCT
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"})
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    compare_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    unit_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    charge_tax = forms.BooleanField(
        required=False
    )

    # JEWELRY DETAILS

    jewelry_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    metal_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    purity = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    weight = forms.DecimalField(
        required=False,
        max_digits=6,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    stone_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    collection = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    occasion = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    # INVENTORY

    cost_per_item = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    inventory_tracked = forms.BooleanField(required=False)

    quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    barcode = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    sell_out_of_stock = forms.BooleanField(required=False)