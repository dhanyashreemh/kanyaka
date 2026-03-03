from django.db import models

class Product(models.Model):
    shopify_product_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    raw_data = models.JSONField()

    def __str__(self):
        return self.title