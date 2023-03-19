# Generated by Django 4.1.7 on 2023-03-11 12:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0002_alter_categoryduo_ifftorlik_and_more'),
        ('bot', '0002_remove_ramadan_prayer_ramadan_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='ramadan',
            name='ifftorlik_prayer',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='ifftorlik_prayer', to='category.categoryduo', to_field='ifftorlik', verbose_name='Ifftorlik Duo'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ramadan',
            name='saharlik_prayer',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='saharlik_prayer', to='category.categoryduo', to_field='saharlik', verbose_name='Saharlik Duo'),
            preserve_default=False,
        ),
    ]
