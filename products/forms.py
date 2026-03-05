from django import forms

class ProductForm(forms.Form):

    title = forms.CharField(max_length=255)

    description = forms.CharField(
        widget=forms.Textarea
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    tags = forms.CharField(
        required=False
    )

    image_url = forms.URLField(
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("image")
        image_url = cleaned_data.get("image_url")

        if not image and not image_url:
            raise forms.ValidationError(
                "Please upload an image or provide an image URL."
            )

        if image and image_url:
            raise forms.ValidationError(
                "Please use only one: upload image OR image URL."
            )

        return cleaned_data