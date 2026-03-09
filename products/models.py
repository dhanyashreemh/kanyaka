from django.db import models

class Product(models.Model):
    shopify_product_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    collection = models.CharField(max_length=100, blank=True, null=True)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    jewelry_type = models.CharField(max_length=100, blank=True, null=True)
    metal_type = models.CharField(max_length=100, blank=True, null=True)
    occasion = models.CharField(max_length=100, blank=True, null=True)
    purity = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    sku = models.CharField(max_length=100, blank=True, null=True)
    stone_type = models.CharField(max_length=100, blank=True, null=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.title