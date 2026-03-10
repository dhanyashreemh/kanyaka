from django import forms

class WhyForm(forms.Form):

    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Enter title"
        })
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-input",
            "placeholder": "Enter description",
            "rows": 4
        })
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-input",
            "placeholder": "Enter price"
        })
    )

    track_inventory = forms.BooleanField(
        required=False
    )