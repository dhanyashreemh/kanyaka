from django import forms

class ProductForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        label="Product Title"
    )

    description = forms.CharField(
        widget=forms.Textarea,
        label="Product Description"
    )

    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Price"
    )

    tags = forms.CharField(
        required=False,
        label="Tags",
        help_text="Example: gold, necklace, bridal"
    )

    image_url = forms.URLField(
        required=False,
        label="Image URL"
    )