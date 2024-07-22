import base64
import uuid

from django.db import transaction
from django.core.files.base import ContentFile
from rest_framework import serializers, status
from rest_framework.relations import PrimaryKeyRelatedField

from recipes.constants import MAX_VALUE, MIN_VALUE
from recipes.models import (
    RecipeIngredient, Favorite, Ingredient,
    Recipe, ShoppingCart, Tag
)
from users.models import Subscription, User


class Base64ImageField(serializers.ImageField):
    """Serializer поля image"""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            img_format, img_str = data.split(';base64,')
            ext = img_format.split('/')[-1]
            if ext.lower() not in ('jpeg', 'jpg', 'png'):
                raise serializers.ValidationError(
                    'Формат изображения не поддерживается. \
                    Используйте форматы JPEG или PNG.'
                )

            uid = uuid.uuid4()
            data = ContentFile(
                base64.b64decode(img_str), name=uid.urn[9:] + '.' + ext
            )

        return super(Base64ImageField, self).to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer модели User"""

    is_subscribed = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (request.user.is_authenticated
                and request.user.followed_users.filter(
                    author=obj
                ).exists())


class SubscribeSerializer(UserSerializer):
    recipes_count = serializers.ReadOnlyField(
        source="recipes.count")
    recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            "recipes",
            "recipes_count",
        )
        read_only_fields = (
            "email", "username",
            "first_name", "last_name"
        )

    def get_recipes(self, obj):
        queryset = obj.recipes.all()
        recipes_limit = self.context[
            "request"
        ].GET.get("recipes_limit")
        if recipes_limit and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]
        return RecipeShortSerializer(
            queryset, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        """Количество рецептов автора."""
        return Recipe.objects.filter(author=obj.id).count()


class SubscribeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ("user", "author")

    def validate(self, data):
        user_id = data.get("user").id
        author_id = data.get("author").id
        if Subscription.objects.filter(
                author=author_id, user=user_id).exists():
            raise serializers.ValidationError(
                detail="Вы уже подписаны на этого пользователя!",
                code=status.HTTP_400_BAD_REQUEST,
            )
        if user_id == author_id:
            raise serializers.ValidationError(
                detail="Вы не можете подписаться на самого себя!",
                code=status.HTTP_400_BAD_REQUEST,
            )
        return data

    def to_representation(self, instance):
        return SubscribeSerializer(
            instance.author, context=self.context
        ).data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer модели RecipeIngredient"""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount"
        )


class CreateRecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer создания объектов в модели RecipeIngredient"""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    amount = serializers.IntegerField(
        min_value=MIN_VALUE,
        max_value=MAX_VALUE,
        error_messages={
            "min_value": "Значение должно быть не меньше {min_value}.",
            "max_value": "Количество ингредиента не больше {max_value}."
        }
    )

    class Meta:
        fields = ("id", "amount")
        model = RecipeIngredient


class RecipeReadSerializer(serializers.ModelSerializer):
    """Serializer модели Recipe"""

    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source="recipe_ingredient",
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        return self.get_is_in_user_field(
            obj, "recipes_favorite_related"
        )

    def get_is_in_shopping_cart(self, obj):
        return self.get_is_in_user_field(
            obj, "recipes_shoppingcart_related"
        )

    def get_is_in_user_field(self, obj, field):
        request = self.context.get("request")
        return (request.user.is_authenticated and getattr(
            request.user, field).filter(recipe=obj).exists())


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Serializer создания объектов в модели Recipe"""

    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = CreateRecipeIngredientSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'name',
            'tags',
            'image',
            'ingredients',
            'text',
            'cooking_time',
            'pub_date'
        )

    def validate(self, data):
        ingredients = data.get("ingredients")
        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Поле ингредиентов не может быть пустым!"}
            )
        if (len(set(item["id"] for item in ingredients)) != len(ingredients)):
            raise serializers.ValidationError(
                "Ингридиенты не должны повторяться!")
        tags = data.get("tags")
        if not tags:
            raise serializers.ValidationError(
                {"tags": "Поле тегов не может быть пустым!"}
            )
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                {"tags": "Теги не должны повторяться!"}
            )
        return data

    @transaction.atomic
    def create_ingredients_amounts(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create(
            [RecipeIngredient(
                ingredient=Ingredient.objects.get(
                    id=ingredient['id']),
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )

    @transaction.atomic
    def create(self, validated_data):
        current_user = self.context["request"].user
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(
            **validated_data,
            author=current_user
        )
        recipe.tags.set(tags)
        self.create_ingredients_amounts(ingredients, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.tags.clear()
        instance.tags.set(validated_data.pop("tags"))
        instance.ingredients.clear()
        ingredients = validated_data.pop("ingredients")
        self.create_ingredients_amounts(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance, context=self.context
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )
        read_only_fields = ('id',)


class ShoppingCartCreateDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ("user", "recipe")

    def validate(self, data):
        user_id = data.get("user").id
        recipe_id = data.get("recipe").id
        if self.Meta.model.objects.filter(
            user=user_id,
            recipe=recipe_id
        ).exists():
            raise serializers.ValidationError("Рецепт уже добавлен")
        return data

    def to_representation(self, instance):
        serializer = RecipeShortSerializer(
            instance.recipe, context=self.context
        )
        return serializer.data


class FavoriteCreateDeleteSerializer(ShoppingCartCreateDeleteSerializer):
    class Meta(ShoppingCartCreateDeleteSerializer.Meta):
        model = Favorite
