from django.db import models

class Order(models.Model):
    shopify_order_id = models.BigIntegerField(unique=True)
    email = models.EmailField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    raw_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.shopify_order_id}"