from datetime import datetime

from djoser import views
from django.db.models import Sum
from django.http import HttpResponse

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.permissions import (
    SAFE_METHODS, IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from recipes.models import (
    Ingredient,
    Tag,
    Favorite,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscription, CustomUser
from api.paginations import CustomPagination
from api.permissions import AuthorOrReadOnly
from api.serializers import (
    FavoriteCreateDeleteSerializer,
    IngredientSerializer, RecipeCreateSerializer,
    RecipeReadSerializer,
    ShoppingCartCreateDeleteSerializer,
    SubscribeCreateSerializer, SubscribeSerializer,
    TagSerializer, RecipeShortSerializer,
)
from api.filters import IngredientFilter, RecipeFilter


class CustomUserViewSet(views.UserViewSet):
    """Вьюсет для создания обьектов класса User."""

    queryset = CustomUser.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        serializer = SubscribeCreateSerializer(
            data={"user": request.user.id, "author": id},
            context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        subscription = Subscription.objects.filter(
            user=request.user, author=id)
        if subscription.exists():
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"error": "Вы не подписаны на этого пользователя"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = CustomUser.objects.filter(
            author__user=request.user
        )
        page = self.paginate_queryset(subscriptions)
        serializer = SubscribeSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Ingredient."""

    queryset = Ingredient.objects.all()
    pagination_class = None
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для создания обьектов класса Recipe."""

    queryset = Recipe.objects.select_related(
        'author'
    ).prefetch_related('tags', 'ingredients')
    permission_classes = [AuthorOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    @staticmethod
    def create_favorite_or_shoppingcart(serializer_class, id, request):
        """Позволяет текущему пользователю добавлять рецепты
        в список покупок/ избранное."""

        serializer = serializer_class(
            data={
                'user': request.user.id,
                'recipe': id
            },
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @staticmethod
    def delete_favorite_or_shoppingcart(model, id, request):
        object = model.objects.filter(
            user=request.user, recipe_id=id
        )
        if object.exists():
            object.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Этого рецепта нет в списке'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"],
            permission_classes=[IsAuthenticated],)
    def favorite(self, request, pk=None):
        return self.create_favorite_or_shoppingcart(
            FavoriteCreateDeleteSerializer, request.user, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        return self.delete_favorite_or_shoppingcart(
            Favorite, request.user, pk)

    @action(detail=True, methods=["post"], url_path='shopping_cart',
            url_name='add_to_shopping_cart',
            permission_classes=[IsAuthenticated])
    def add_shopping_cart(self, request, pk=None):
        serializer = ShoppingCartCreateDeleteSerializer(
            data={'recipe': pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        shopping_cart = serializer.save(user=request.user)
        shopping_cart_data = RecipeShortSerializer(
            shopping_cart.recipe,
            context={'request': request}).data
        return Response(
            data=shopping_cart_data,
            status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path='shopping_cart',
            url_name='remove_from_shopping_cart',
            permission_classes=[IsAuthenticated])
    def remove_shopping_cart(self, request, pk=None):
        serializer = ShoppingCartCreateDeleteSerializer(
            data={'recipe': pk},
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        favorite = ShoppingCart.objects.get(
            user=request.user,
            recipe=serializer.validated_data["recipe"])
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        self.request.user.save()


class ShoppingCartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecipeShortSerializer
    pagination_class = None

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return Response(status=HTTP_400_BAD_REQUEST)

        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        today = datetime.today()
        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
            f'Дата: {today:%Y-%m-%d}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        shopping_list += f'\n\nFoodgram ({today:%Y})'

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
