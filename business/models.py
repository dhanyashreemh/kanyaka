from django.db import models

# Create your models here.
from django.db import models

class GoldRate(models.Model):
    rate_24k = models.DecimalField(max_digits=10, decimal_places=2)
    rate_22k = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"24K: {self.rate_24k} | 22K: {self.rate_22k}"