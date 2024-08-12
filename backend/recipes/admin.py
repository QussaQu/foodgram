from django import forms
from django.contrib import admin
from django.contrib.admin import display

from recipes.constants import MIN_VALUE
from .models import (Favorite, Ingredient,
                     IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)


class IngredientsInRecipeInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        count = 0
        for form in self.forms:
            try:
                if form.cleaned_data and not form.cleaned_data.get('DELETE',
                                                                   False):
                    count += 1
            except AttributeError:
                pass
        if count < 1:
            raise forms.ValidationError('Выберите хотя бы один ингредиент')


class IngredientInRecipeInline(admin.StackedInline):
    model = IngredientInRecipe
    formset = IngredientsInRecipeInlineFormset
    extra = 1
    min_num = MIN_VALUE
    validate_min = True

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientInRecipeInline]
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
