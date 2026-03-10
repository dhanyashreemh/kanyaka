from django.db import models


class Product(models.Model):

    shopify_product_id = models.CharField(max_length=255, unique=True)
    shopify_variant_id = models.CharField(max_length=255, blank=True, null=True)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    collection = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)

    jewelry_type = models.CharField(max_length=100, blank=True, null=True)
    metal_type = models.CharField(max_length=100, blank=True, null=True)
    stone_type = models.CharField(max_length=100, blank=True, null=True)
    purity = models.CharField(max_length=20, blank=True, null=True)
    occasion = models.CharField(max_length=100, blank=True, null=True)

    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    sku = models.CharField(max_length=100, blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)

    quantity = models.IntegerField(default=0)
    cost_per_item = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    inventory_tracked  = models.BooleanField(default=True)
    sell_out_of_stock = models.BooleanField(default=False)
    charge_tax = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title