from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, BooleanField

from recipes.models import (
    Ingredient, IngredientInRecipe, Recipe,
    Tag, Favorite, ShoppingCart)
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
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user.id
        return Subscribe.objects.filter(
            author=obj.id, user=user
        ).exists()


class SubscribeSerializer(NewUserSerializer):
    recipes_count = serializers.ReadOnlyField(source='recipes.count')
    recipes = SerializerMethodField()

    class Meta(NewUserSerializer.Meta):
        fields = NewUserSerializer.Meta.fields + (
            'recipes_count',
            'recipes'
        )
        read_only_fields = ('email', 'username')

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        author_recipes = obj.author.recipes.all()

        if author_recipes:
            serializer = RecipeShortSerializer(
                author_recipes,
                context={'request': self.context.get('request')},
                many=True,
            )
            return serializer.data
        return []


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
        fields = ("id", "name", "measurement_unit")


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = NewUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(many=True,
                                               source='ingredient_list')
    image = Base64ImageField()
    is_favorite = BooleanField(read_only=True, default=False)
    is_in_shopping_cart = BooleanField(read_only=True, default=False)

    def get_ingredients(self, obj):
        ingredients = IngredientInRecipe.objects.filter(recipe=obj)
        serializer = IngredientInRecipeSerializer(ingredients, many=True)
        return serializer.data

    def get_is_favorited(self, obj):
        user_id = self.context.get("request").user.id
        return Favorite.objects.filter(user=user_id, recipe=obj.id).exists()

    def get_is_in_shopping_cart(self, obj):
        user_id = self.context.get("request").user.id
        return ShoppingCart.objects.filter(
            user=user_id, recipe=obj.id
        ).exists()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorite',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )


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
        many=True, write_only=True
    )
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

    def validate_ingredients(self, value):
        if not value:
            raise ValidationError({
                'ingredients': 'Нужен хотя бы один ингредиент!'
            })

        ingredients = [item["id"] for item in value]
        for ingredient in ingredients:
            if ingredients.count(ingredient) > MIN_VALUE:
                raise ValidationError({
                    'ingredients': 'Ингридиенты не могут повторяться!'
                })
        return value

    def validate_tags(self, value):
        tags = value
        if not tags:
            raise ValidationError(
                {'tags': 'Нужно выбрать хотя бы один тег!'}
            )
        tags_list = []
        for tag in tags:
            if tag in tags_list:
                raise ValidationError(
                    {'tags': 'Теги должны быть уникальными!'}
                )
            tags_list.append(tag)
        return value

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        create_ingredients = [IngredientInRecipe(
            recipe=recipe, ingredient=ingredient["id"],
            amount=ingredient["amount"]
        ) for ingredient in ingredients]
        IngredientInRecipe.objects.bulk_create(create_ingredients)

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_amounts(recipe=recipe, ingredients=ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients_amounts(
            recipe=instance,
            ingredients=ingredients
        )
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return RecipeReadSerializer(representation, context=self.context).data


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
