from django.db import models

# Create your models here.


class CategoryButton(models.Model):
    name = models.CharField(max_length=250, verbose_name='Name')
    callback = models.CharField(max_length=250, verbose_name='Callback')
    text = models.TextField(verbose_name='Text', blank=True)
    parent = models.ForeignKey("CategoryButton", null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Parent')

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = 'Button'
        verbose_name_plural = 'Buttons'


class CategoryRegion(models.Model):
    name = models.CharField(max_length=250, verbose_name='Name')
    bomdod = models.CharField(max_length=250, verbose_name='bomdod', null=True, blank=True)
    quyosh = models.CharField(max_length=250, verbose_name='quyosh', null=True, blank=True)
    peshin = models.CharField(max_length=250, verbose_name='peshin', null=True, blank=True)
    asr = models.CharField(max_length=250, verbose_name='asr', null=True, blank=True)
    shom = models.CharField(max_length=250, verbose_name='shom', null=True, blank=True)
    xufton = models.CharField(max_length=250, verbose_name='xufton', null=True, blank=True)

    def __str__(self):
        return f'{self.name}'
        return f'{self.bomdod}'

    class Meta:

        verbose_name = 'Region'
        verbose_name_plural = 'Regions'


class CategoryDuo(models.Model):
    saharlik = models.TextField(verbose_name='Saharlik', help_text='Please write prayer for Saharlik', unique=True)
    ifftorlik = models.TextField(verbose_name='Ifftorlik', help_text='Please write prayer for Ifftorlik', unique=True)

    def __str__(self):
        return f'{self.saharlik}'

    class Meta:

        verbose_name = 'Prayer'
        verbose_name_plural = 'Prayers'


class CategoryQuestion(models.Model):
    name = models.CharField(max_length=250, verbose_name='Name')

    def __str__(self):
        return f'{self.name}'

    class Meta:

        verbose_name = 'Question'
        verbose_name_plural = 'Question'

