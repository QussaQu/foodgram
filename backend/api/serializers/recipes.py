from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, validators

from api.serializers.users import UserSerializer
from recipes.constants import MAX_VALUE, MIN_VALUE
from recipes.models import (
    RecipeIngredient, Favorite,
    Ingredient, Recipe,
    ShoppingCart, Tag
)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = '__all__',


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели RecipeIngredient."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class CreateRecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Recipe/Ingredient при POST запросах."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), )
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value': 'Значение должно быть не меньше {min_value}.',
            'max_value': 'Количество ингредиента не больше {max_value}'}
    )

    class Meta:
        fields = ('id', 'amount')
        model = RecipeIngredient


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Recipe при GET запросах."""

    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredient',
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        """Проверяет, добавил ли текущий пользователь рецепт в избанное."""

        return self.get_is_in_user_field(obj, 'recipes_favorite_related')

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, добавил ли текущий пользователь
        рецепт в список покупок."""

        return self.get_is_in_user_field(obj, 'recipes_shoppingcart_related')

    def get_is_in_user_field(self, obj, field):
        """Проверяет, добавилен ли текущий пользователь
        в список пользователей."""

        request = self.context.get('request')
        return (request.user.is_authenticated and getattr(
            request.user, field).filter(recipe=obj).exists())


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(use_url=True, max_length=None)
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = CreateRecipeIngredientSerializer(many=True, write_only=True)
    cooking_time = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value':
            f'Время приготовления не может быть меньше {MIN_VALUE} минуты.',
            'max_value':
            f'Время приготовления не может быть больше {MAX_VALUE} минут.'
        }
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, data):
        """Проверяем, что рецепт содержит уникальные ингредиенты
        и их количество не меньше 1."""

        ingredients = data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Кол-во ингредиента не может быть меньше 1'}
            )
        if (len(set(item['id'] for item in ingredients)) != len(ingredients)):
            raise serializers.ValidationError(
                'Ингредиенты рецепта должны быть уникальными')
        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Поле тегов не может быть пустым!'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги рецепта должны быть уникальными'}
            )
        return data

    def validate_image(self, image):
        """Проверяем, что поле image не пустое."""

        if not image:
            raise serializers.ValidationError(
                {'image': 'Поле изображения не может быть пустым!'}
            )
        return image

    @staticmethod
    def create_ingredients(recipe, ingredients):
        """Добавляет ингредиенты."""

        create_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient.get('id'),
                amount=ingredient.get('amount')
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(create_ingredients)

    @transaction.atomic
    def update(self, instance, validated_data):
        recipe = instance
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.name)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.tags.clear()
        instance.ingredients.clear()
        tags_data = validated_data.get('tags')
        instance.tags.set(tags_data)
        ingredients_data = validated_data.get('ingredients')
        RecipeIngredient.objects.filter(recipe=recipe).delete()
        self.create_ingredients(ingredients_data, recipe)
        instance.save()
        return instance

    def to_representation(self, recipe):
        """Определяет какой сериализатор будет использоваться для чтения."""

        serializer = RecipeReadSerializer(recipe)
        return serializer.data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для компактного отображения рецептов."""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class ShoppingCartCreateDeleteSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ShoppingCart."""

    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [
            validators.UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Вы уже добавляли это рецепт в список покупок'
            )
        ]

    def to_representation(self, instance):
        serializer = RecipeShortSerializer(
            instance.recipe, context=self.context
        )
        return serializer.data


class FavoriteCreateDeleteSerializer(ShoppingCartCreateDeleteSerializer):
    """Сериализатор для модели Favorite."""

    class Meta(ShoppingCartCreateDeleteSerializer.Meta):
        model = Favorite
