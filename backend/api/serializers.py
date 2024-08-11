from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.serializers import ModelSerializer, BooleanField

from recipes.models import (
    Ingredient, IngredientInRecipe, Recipe,
    Tag, UserRecipeDependence, Favorite, ShoppingCart)
from recipes.constants import MIN_VALUE, MAX_VALUE
from users.models import Subscribe

User = get_user_model()


class NewUserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = tuple(User.REQUIRED_FIELDS) + (
            User.USERNAME_FIELD,
            'password',
        )


class NewUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.subscriber.filter(id=obj.id).exists())


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class SubscribeSerializer(NewUserSerializer):
    recipes_count = serializers.ReadOnlyField(source='recipes.count')
    recipes = SerializerMethodField()

    class Meta(NewUserSerializer.Meta):
        fields = NewUserSerializer.Meta.fields + (
            'recipes_count',
            'recipes'
        )
        read_only_fields = ('email', 'username')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = obj.recipes.all()
        try:
            if limit and limit.isdigit():
                queryset = queryset[:int(limit)]
            return RecipeShortSerializer(queryset,
                                         many=True,
                                         context=self.context).data
        except ValueError:
            print('Невозможно преобразовать строку в число.')


class SubscribeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscribe
        fields = (
            'user',
            'author'
        )
        validators = [
            UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=('author', 'user'),
                message='Вы уже подписаны на этого пользователя',
            )
        ]

    def validate(self, author):
        if self.context['request'].user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя')
        return author

    def to_representation(self, instance):
        return SubscribeSerializer(instance.author, context=self.context).data


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = NewUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(many=True,
                                               source='ingredient_list')
    image = Base64ImageField()
    is_favorited = BooleanField(read_only=True, default=False)
    is_in_shopping_cart = BooleanField(read_only=True, default=False)

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
        return self.get_is_in_user_field(obj, 'recipes_favorite_related')

    def get_is_in_shopping_cart(self, obj):
        return self.get_is_in_user_field(obj, 'recipes_shoppingcart_related')

    def get_is_in_user_field(self, obj, field):
        request = self.context.get('request')
        return (request.user.is_authenticated and getattr(
            request.user, field).filter(recipe=obj).exists())


class IngredientInRecipeWriteSerializer(ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            'min_value': 'Значение должно быть не меньше {min_value}.',
            'max_value': 'Количество ингредиента не больше {max_value}'}
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeWriteSerializer(ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    author = NewUserSerializer(read_only=True)
    ingredients = IngredientInRecipeWriteSerializer(
        many=True, write_only=True)
    image = Base64ImageField()

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
        # defult = ingredients = data.get('ingredients')
        ingredients = data.get('ingredient')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужен хотя бы один ингредиент'}
            )
        if (len(set(item["id"] for item in ingredients)) != len(ingredients)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты должны быть уникальными'}
            )

        tags = data.get("tags")
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужно выбрать хотя бы один тег'}
            )

        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                {'tags': 'Теги должны быть уникальными!'}
            )
        return data

    @staticmethod
    def create_ingredients_amounts(recipe, ingredients):
        create_ingredients_amounts = [IngredientInRecipe(
            recipe=recipe, ingredient=ingredient['id'],
            amount=ingredient['amount']
        ) for ingredient in ingredients]
        IngredientInRecipe.objects.bulk_create(create_ingredients_amounts)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amounts(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.tags.clear()
        instance.tags.set(validated_data.pop('tags'))
        instance.ingredients.clear()
        ingredients = validated_data.pop('ingredients')
        self.create_ingredients_amounts(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, recipe):
        return RecipeReadSerializer(recipe, context=self.context).data


class RecipeShortSerializer(ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )


class UserRecipeDependenceSerializer(serializers.ModelSerializer):
    """Добавлен ли рецепт в избранное"""
    class Meta:
        model = UserRecipeDependence
        fields = ('user', 'recipe')

    def validate(self, data):
        user_id = data.get('user').id
        recipe_id = data.get('recipe').id
        if self.Meta.model.objects.filter(user=user_id,
                                          recipe=recipe_id).exists():
            raise serializers.ValidationError(
                'Вы уже добавили этот рецепт'
            )
        return data

    def to_representation(self, instance):
        serializer = RecipeShortSerializer(
            instance.recipe, context=self.context
        )
        return serializer.data


class FavoriteCreateSerializer(UserRecipeDependenceSerializer):
    """Добавлен ли рецепт в корзину"""
    class Meta(UserRecipeDependenceSerializer.Meta):
        model = Favorite


class ShoppingCartCreateSerializer(UserRecipeDependenceSerializer):
    """Добавлен ли рецепт в корзину"""
    class Meta(UserRecipeDependenceSerializer.Meta):
        model = ShoppingCart
