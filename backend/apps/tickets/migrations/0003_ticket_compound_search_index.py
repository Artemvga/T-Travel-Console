from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0002_rename_tickets_tic_from_ci_ba4455_idx_tickets_tic_from_ci_85bbfa_idx_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("from_city", "departure_datetime", "transport_type", "is_active"),
                name="tickets_tic_from_ci_transport_active_idx",
            ),
        ),
    ]
