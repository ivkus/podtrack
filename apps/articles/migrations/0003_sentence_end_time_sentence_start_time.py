# Generated by Django 5.0 on 2025-02-15 02:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0002_article_audio_file_article_text_file_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sentence",
            name="end_time",
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name="sentence",
            name="start_time",
            field=models.FloatField(null=True),
        ),
    ]
