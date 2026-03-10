from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_add_missing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]