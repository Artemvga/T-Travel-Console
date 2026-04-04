from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("routes", "0002_routesearchlog_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="RouteFavorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("departure_at", models.DateTimeField()),
                ("priority_mode", models.CharField(default="optimal", max_length=24)),
                ("route_title", models.CharField(blank=True, default="", max_length=120)),
                ("route_signature", models.CharField(max_length=1024)),
                ("route_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "from_city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="favorite_from_routes",
                        to="cities.city",
                    ),
                ),
                (
                    "to_city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="favorite_to_routes",
                        to="cities.city",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favorite_routes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "via_city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="favorite_via_routes",
                        to="cities.city",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="routefavorite",
            constraint=models.UniqueConstraint(
                fields=("user", "route_signature", "departure_at"),
                name="unique_user_route_favorite",
            ),
        ),
    ]
