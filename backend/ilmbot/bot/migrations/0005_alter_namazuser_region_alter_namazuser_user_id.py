# Generated by Django 4.1.7 on 2023-03-18 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0004_alter_comment_options_alter_namazuser_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='namazuser',
            name='region',
            field=models.CharField(max_length=250, null=True, verbose_name='Region'),
        ),
        migrations.AlterField(
            model_name='namazuser',
            name='user_id',
            field=models.IntegerField(verbose_name='User ID'),
        ),
    ]
