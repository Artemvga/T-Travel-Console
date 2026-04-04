from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0004_ticket_generation_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("from_city", "departure_datetime"),
                name="tickets_act_from_dep_idx",
                condition=models.Q(available_seats__gt=0, is_active=True),
            ),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("from_city", "transport_type", "departure_datetime"),
                name="tickets_act_from_ttype_dep_idx",
                condition=models.Q(available_seats__gt=0, is_active=True),
            ),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("from_city", "to_city", "departure_datetime"),
                name="tickets_act_from_to_dep_idx",
                condition=models.Q(available_seats__gt=0, is_active=True),
            ),
        ),
    ]
