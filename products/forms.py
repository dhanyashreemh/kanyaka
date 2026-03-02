from django import forms

class ProductForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea)
    price = forms.DecimalField(max_digits=10, decimal_places=2)