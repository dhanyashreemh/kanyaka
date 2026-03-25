from django.db import models
from django.core.cache import cache

CACHE_KEY = "gold_rate_latest"

class GoldRate(models.Model):

    rate_24k = models.DecimalField(max_digits=10, decimal_places=2)
    rate_22k = models.DecimalField(max_digits=10, decimal_places=2)

    making_charge_per_gram = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=3)

    making_type = models.CharField(
        max_length=10,
        choices=[("percent", "Percent"), ("fixed", "Per Gram")],
        default="percent"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"24K: {self.rate_24k} | 22K: {self.rate_22k}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)