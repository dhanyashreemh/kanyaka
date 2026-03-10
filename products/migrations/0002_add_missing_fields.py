from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='inventory_tracked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='cost_per_item',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='product',
            name='charge_tax',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='sell_out_of_stock',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]