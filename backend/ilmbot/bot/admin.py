from django.contrib import admin
from .models import Post, Ramadan, Comment, NamazUser, Question
# Register your models here.


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'idishka', 'text', 'post', 'category')
    search_fields = ('idishka', 'text', 'post')
    list_filter = ('category', 'idishka')
    # readonly_fields = ('idishka', 'text')
    save_on_top = True


@admin.register(Ramadan)
class RamadanAdmin(admin.ModelAdmin):
    list_display = ('id', 'day', 'region', 'saharlik', 'ifftorlik')
    search_fields = ('id', 'day', 'region', 'saharlik', 'ifftorlik')
    list_filter = ('day', 'saharlik', 'ifftorlik')
    # readonly_fields = ('id',)
    save_on_top = True


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'user_name', 'comment')
    search_fields = ('user_id', 'user_name', 'comment')
    list_filter = ('comment',)
    # readonly_fields = ('user_id', 'user_name')
    save_on_top = True


@admin.register(NamazUser)
class NamazUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'user_name', 'region', 'subscribe')
    search_fields = ('user_id', 'user_name', 'region')
    list_filter = ('region', 'subscribe')
    # readonly_fields = ('user_id', 'user_name')
    save_on_top = True


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer')
    search_fields = ('id', 'question', 'answer')
    list_filter = ('id', 'question', 'answer')
    # readonly_fields = ('id', 'question', 'answer')
    save_on_top = True



