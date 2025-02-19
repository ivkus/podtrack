# Generated by Django 5.0 on 2025-02-12 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="audio_file",
            field=models.FileField(blank=True, null=True, upload_to="articles/audio/"),
        ),
        migrations.AddField(
            model_name="article",
            name="text_file",
            field=models.FileField(blank=True, null=True, upload_to="articles/texts/"),
        ),
        migrations.AlterField(
            model_name="article",
            name="content",
            field=models.TextField(blank=True),
        ),
    ]
