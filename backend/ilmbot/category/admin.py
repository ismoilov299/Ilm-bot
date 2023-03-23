from django.contrib import admin
from .models import CategoryButton, CategoryRegion, CategoryDuo, CategoryQuestion
# Register your models here.


@admin.register(CategoryButton)
class CategoryButtonAndmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'callback', 'text', 'parent')
    search_fields = ('id', 'name', 'callback', 'parent')
    list_filter = ('id', 'parent', 'callback', 'parent')
    save_on_top = True


@admin.register(CategoryRegion)
class CategoryRegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'bomdod','quyosh','peshin','asr','shom','xufton')
    search_fields = ('id', 'name')
    list_filter = ('id', 'name')
    save_on_top = True


@admin.register(CategoryDuo)
class CategoryDuoAdmin(admin.ModelAdmin):
    list_display = ('id', 'saharlik', 'ifftorlik')
    save_on_top = True


@admin.register(CategoryQuestion)
class CategoryQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('id', 'name')
    list_filter = ('id', 'name')
    save_on_top = True



