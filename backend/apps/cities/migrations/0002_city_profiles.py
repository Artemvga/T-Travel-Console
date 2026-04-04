from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="has_international_airport",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="city",
            name="is_bus_hub",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="city",
            name="is_rail_hub",
            field=models.BooleanField(default=False),
        ),
    ]
