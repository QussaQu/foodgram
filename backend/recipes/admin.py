from django import forms
from django.contrib import admin
from django.contrib.admin import display

from recipes.constants import MIN_VALUE
from .models import (Favorite, Ingredient,
                     IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)


class IngredientInRecipeInline(admin.StackedInline):
    model = IngredientInRecipe
    extra = 1
    min_num = MIN_VALUE


class RecipesAdminForm(forms.ModelForm):
    def quantity_limit(self):
        ingredients = self.cleaned_data['ingredient']
        if len(ingredients) == 0:
            raise forms.ValidationError(
                'Нельзя создать/сохранить рецепт без ингредиента'
            )
        return ingredients


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientInRecipeInline]
    form = RecipesAdminForm
    list_display = ('name', 'id', 'author')
    readonly_fields = ('added_in_favorites',)
    list_filter = ('author', 'name', 'tags',)
    empty_value_display = '-пусто-'

    @display(description='Количество в избранных')
    def added_in_favorites(self, obj):
        return obj.recipes_favorite_related.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)
    empty_value_display = '-пусто-'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug',)
    empty_value_display = '-пусто-'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    empty_value_display = '-пусто-'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    empty_value_display = '-пусто-'
