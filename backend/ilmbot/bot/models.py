from django.db import models
from category.models import CategoryButton, CategoryRegion, CategoryDuo, CategoryQuestion

# Create your models here.


class Post(models.Model):
    idishka = models.PositiveIntegerField(null=True, verbose_name='ID')
    text = models.TextField(verbose_name='Text', blank=True)
    post = models.CharField(max_length=250, verbose_name='Post', blank=True)
    category = models.ForeignKey(CategoryButton, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.text

    class Meta:

        verbose_name = 'Post'
        verbose_name_plural = 'Posts'


class NamazUser(models.Model):
    user_id = models.IntegerField(verbose_name='User ID',unique=True)
    user_name = models.CharField(max_length=250, verbose_name='User Name')
    region = models.CharField(max_length=250, verbose_name='Region', null=True)
    subscribe = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user_name

    class Meta:

        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Comment(models.Model):
    user_id = models.PositiveIntegerField(verbose_name="User ID")
    user_name = models.CharField(max_length=250, verbose_name='User Name')
    comment = models.TextField(verbose_name='Comment')

    def __str__(self):
        return self.user_name

    class Meta:

        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'


class Ramadan(models.Model):
    region = models.ForeignKey(CategoryRegion, null=True, on_delete=models.SET_NULL, verbose_name="Region")
    day = models.CharField(max_length=250, verbose_name='Day')
    saharlik = models.CharField(max_length=250, verbose_name='Saharlik')
    ifftorlik = models.CharField(max_length=250, verbose_name='Ifftorlik')
    saharlik_prayer = models.ForeignKey(CategoryDuo, on_delete=models.CASCADE,
                                        related_name='saharlik_prayer', verbose_name='Saharlik Duo', to_field='saharlik')
    ifftorlik_prayer = models.ForeignKey(CategoryDuo, on_delete=models.CASCADE,
                                         related_name='ifftorlik_prayer', verbose_name='Ifftorlik Duo', to_field='ifftorlik')

    def __str__(self):
        return self.region

    class Meta:

        verbose_name = 'Ramadan'
        verbose_name_plural = 'Ramadan'


class Question(models.Model):
    question = models.TextField(verbose_name='Question')
    answer = models.TextField(verbose_name='Answer')
    option_1 = models.TextField(verbose_name='Option 1')
    option_2 = models.TextField(verbose_name='Option 2')
    option_3 = models.TextField(verbose_name='Option 3')
    category = models.ForeignKey(CategoryQuestion, null=True, on_delete=models.SET_NULL, verbose_name='Category')

    def __str__(self):
        return self.question

    class Meta:

        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
