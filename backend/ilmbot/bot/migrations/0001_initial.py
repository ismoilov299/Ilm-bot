# Generated by Django 4.1.7 on 2023-03-11 12:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('category', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.PositiveIntegerField(verbose_name='User ID')),
                ('user_name', models.CharField(max_length=250, verbose_name='User Name')),
                ('comment', models.TextField(verbose_name='Comment')),
            ],
        ),
        migrations.CreateModel(
            name='NamazUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=250, verbose_name='User ID')),
                ('user_name', models.CharField(max_length=250, verbose_name='User Name')),
                ('region', models.CharField(max_length=250, verbose_name='Region')),
                ('subscribe', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Ramadan',
            fields=[
                ('day', models.CharField(max_length=250, verbose_name='Day')),
                ('saharlik', models.CharField(max_length=250, verbose_name='Saharlik')),
                ('ifftorlik', models.CharField(max_length=250, verbose_name='Ifftorlik')),
                ('prayer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='category.categoryduo', verbose_name='Saharlik VA Ifftorlik Duo')),
                ('region', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='category.categoryregion', verbose_name='Region')),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('option_1', models.TextField(verbose_name='Option 1')),
                ('option_2', models.TextField(verbose_name='Option 2')),
                ('option_3', models.TextField(verbose_name='Option 3')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='category.categoryquestion', verbose_name='Category')),
            ],
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idishka', models.PositiveIntegerField(null=True, verbose_name='ID')),
                ('text', models.TextField(blank=True, verbose_name='Text')),
                ('post', models.CharField(blank=True, max_length=250, verbose_name='Post')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='category.categorybutton')),
            ],
        ),
    ]
