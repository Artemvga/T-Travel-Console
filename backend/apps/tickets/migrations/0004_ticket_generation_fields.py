from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0003_ticket_compound_search_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="generation_batch",
            field=models.CharField(blank=True, default="", max_length=96),
        ),
        migrations.AddField(
            model_name="ticket",
            name="generation_meta",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="ticket",
            name="route_signature",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("generation_batch", "departure_datetime"),
                name="tickets_tic_gen_batch_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ticket",
            index=models.Index(
                fields=("route_signature", "departure_datetime"),
                name="tickets_tic_route_sig_idx",
            ),
        ),
    ]
