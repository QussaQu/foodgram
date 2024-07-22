from django.contrib import admin

from .models import Subscription, CustomUser


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    """Админ-модель пользователей"""

    list_display = (
        'username',
        'id',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'get_recipes_count',
        'get_subscribers_count',
    )
    list_filter = (
        'email',
        'first_name',
        'is_active',
    )
    list_fields = ('first_name',)
    search_fields = (
        'username',
        'email',
    )
    empty_value_display = '-пусто-'
    save_on_top = True

    @admin.display(description='Количество рецептов')
    def get_recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Количество подписчиков')
    def get_subscribers_count(self, obj):
        return obj.author.count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админ-модель подписок"""

    list_display = (
        'id',
        'user',
        'author',
    )
    search_fields = (
        'user',
        'author',
    )
    list_filter = (
        'user',
        'author',
    )
    empty_value_display = '-пусто-'
