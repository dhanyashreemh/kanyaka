from django import forms

class ProductForm(forms.Form):

    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea)

    jewelry_type = forms.CharField(required=False)
    metal_type = forms.CharField(required=False)
    purity = forms.CharField(required=False)

    weight = forms.DecimalField(max_digits=8, decimal_places=2, required=False)

    stone_type = forms.CharField(required=False)

    collection = forms.CharField(required=False)
    occasion = forms.CharField(required=False)
    tags = forms.CharField(required=False)

    price = forms.DecimalField(max_digits=10, decimal_places=2)

    compare_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    unit_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)

    charge_tax = forms.BooleanField(required=False, widget=forms.CheckboxInput)

    cost_per_item = forms.DecimalField(max_digits=10, decimal_places=2, required=False)

    inventory_tracked = forms.BooleanField(required=False, widget=forms.CheckboxInput)

    quantity = forms.IntegerField(required=False)

    sku = forms.CharField(required=False)
    barcode = forms.CharField(required=False)

    sell_out_of_stock = forms.BooleanField(required=False, widget=forms.CheckboxInput)