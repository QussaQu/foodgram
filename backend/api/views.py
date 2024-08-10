from django.db.models import (Sum, BooleanField, Case,
                              When, Value, OuterRef, Exists)
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (NewUserSerializer, SubscribeSerializer,
                             SubscribeCreateSerializer,
                             IngredientSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, TagSerializer,
                             ShoppingCartCreateSerializer,
                             FavoriteCreateSerializer,
                             AvatarSerializer
                             )
from recipes.models import (Favorite, Ingredient, IngredientInRecipe,
                            Recipe, ShoppingCart, Tag)
from users.models import Subscribe, User


class NewUserViewSet(UserViewSet):
    serializer_class = NewUserSerializer
    pagination_class = CustomPagination

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id):
        if request.method == 'POST':
            serializer = SubscribeCreateSerializer(
                data={
                    'user': request.user.id,
                    'author': id
                },
                context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = Subscribe.objects.filter(user=request.user, author=id)
        if subscription.exists():
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"error": 'Вы не подписаны на пользователя'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(page, many=True,
                                         context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated],
            url_name='me',)
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(methods=['post', 'delete'],
            detail=False,
            permission_classes=[IsAuthenticated],
            url_path='me/avatar', url_name='me-avatar',)
    def avatar(self, request):
        data = request.data
        if request.method == 'POST':
            serializer = self.avatar_manipulation(request.data)
            return Response(serializer.data)
        if 'avatar' not in data:
            data = {'avatar': None}
        self.avatar_manipulation(data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def avatar_manipulation(self, data):
        instance = self.get_instance()
        serializer = AvatarSerializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    permission_classes = (IsAuthorOrReadOnly | IsAdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        return Recipe.objects.annotate(
            is_favorited=Case(
                When(
                    Exists(Favorite.objects.filter(
                        recipe=OuterRef('pk'), user=self.request.user.pk
                    )),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
            is_in_shopping_cart=Case(
                When(
                    Exists(ShoppingCart.objects.filter(
                        recipe=OuterRef('pk'), user=self.request.user.pk
                    )),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField()
            )
        ).select_related('author').prefetch_related('tags', 'ingredient_list')

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @staticmethod
    def add_to(serializer_class, request, id):
        serializer = serializer_class(
            data={'user': request.user.id, 'recipe': id},
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_from(model, request, id):
        obj = model.objects.filter(user=request.user, recipe__id=id)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт уже удален!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.add_to(FavoriteCreateSerializer, request, pk)
        return self.delete_from(Favorite, request, pk)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_to(ShoppingCartCreateSerializer, request, pk)
        return self.delete_from(ShoppingCart, request, pk)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        if not request.user.recipes_shoppingcart_related.exists():
            return Response(status=HTTP_400_BAD_REQUEST)

        shopping_cart = ShoppingCart.objects.filter(user=request.user)
        recipes = [item.recipe.id for item in shopping_cart]
        ingredients = (
            IngredientInRecipe.objects.filter(recipe__in=recipes)
            .values('ingredient')
            .annotate(amount=Sum('amount'))
        )
        purchased = ["Список покупок:", ]
        for item in ingredients:
            ingredient = Ingredient.objects.get(pk=item['ingredient'])
            amount = item['amount']
            purchased.append(f'{ingredient.name}: {amount}, '
                             f'{ingredient.measurement_unit}')
        purchased_in_file = '\n'.join(purchased)
        response = HttpResponse(purchased_in_file, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename=shopping_list.txt'
        )
        return response
