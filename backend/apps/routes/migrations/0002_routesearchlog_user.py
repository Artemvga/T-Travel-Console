from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("routes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="routesearchlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="route_search_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
