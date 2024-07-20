from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from recipes.constants import MAX_VALUE, MIN_VALUE
from recipes.models import (
    RecipeIngredient, Favorite,
    Ingredient, Recipe,
    ShoppingCart, Tag
)

admin.site.site_header = 'Администрирование Foodgram'
admin.site.unregister(Group)


class RecipeIngredientInline(admin.TabularInline):
    """Админ-модель рецептов_ингредиентов"""

    model = RecipeIngredient
    extra = 1
    min_num = MIN_VALUE
    max_num = MAX_VALUE
    validate_min = True
    validate_max = True


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'get_image',
        'cooking_time',
        'count_favorites',
        'get_ingredients',
    )
    fields = (
        (
            'name',
            'cooking_time',
        ),
        (
            'author',
            'tags',
        ),
        ('text',),
        ('image',),
    )
    raw_id_fields = ('author',)
    search_fields = (
        'name',
        'author__username',
        'tags__name',
    )
    list_filter = ('name', 'author__username', 'tags__name')

    inlines = (RecipeIngredientInline,)
    list_display_links = ('name', 'author')
    empty_value_display = '-пусто-'
    save_on_top = True


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ-модель ингредиентов"""

    list_display = (
        'name',
        'measurement_unit',
    )
    search_fields = ('name',)
    list_filter = ('name',)
    empty_value_display = '-пусто-'
    save_on_top = True

    @admin.display(description="Фотография")
    def get_image(self, obj):
        return mark_safe(f"<img src={obj.image.url} width='80' hieght='30'")

    @admin.display(description="В избранном")
    def count_favorites(self, obj):
        """Метод выводит общее число добавлений рецепта в избранное"""
        return obj.recipes_favorite_related.count()

    @admin.display(description="Ингредиенты")
    def get_ingredients(self, obj):
        return ", ".join(
            ingredient.name for ingredient in obj.ingredients.all())

    list_display_links = ("name", "author")

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'color',
        'slug',
    )
    search_fields = ('name',)
    list_display_links = ('name',)
    empty_value_display = '-пусто-'
    save_on_top = True


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )
    search_fields = ('user__username', 'recipe__name')
    list_display_links = ('user', 'recipe')
    empty_value_display = '-пусто-'
    save_on_top = True


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
        'date_added',
    )
    search_fields = ('user__username', 'recipe__name')
    list_display_links = ('user', 'recipe')
    empty_value_display = '-пусто-'
    save_on_top = True


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = (
        'recipe',
        'ingredient',
        'amount',
    )
    list_display_links = ('recipe', 'ingredient')
    empty_value_display = '-пусто-'
    save_on_top = True
