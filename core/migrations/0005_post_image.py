# Generated by Django 5.2 on 2025-04-20 11:43

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_rename_user_comments_author'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='post_images/', validators=[core.models.validate_image_size]),
        ),
    ]
