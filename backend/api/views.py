import io

from djoser import views
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    SAFE_METHODS
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
from users.models import Subscription, User
from api.paginations import CustomPagination
from api.serializers import (
    FavoriteCreateDeleteSerializer,
    SubscriptionSerializer,
    IngredientSerializer, RecipeCreateSerializer,
    RecipeReadSerializer,
    ShoppingCartCreateDeleteSerializer,
    TagSerializer
)
from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAdminOrReadOnly, AuthorOrReadOnly


class UserViewSet(views.UserViewSet):
    """Вьюсет для создания обьектов класса User."""

    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Список авторов, на которых подписан пользователь."""

        user = self.request.user
        queryset = user.follower.all()
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
    )
    def subscribe(self, request, id=None):
        """Подписка на автора."""

        user = self.request.user
        author = get_object_or_404(User, pk=id)

        if user == author:
            return Response(
                {'errors': 'Нельзя подписаться или отписаться от себя!'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if self.request.method == 'POST':
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подписались на данного автора.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            queryset = Subscription.objects.create(author=author, user=user)
            serializer = SubscriptionSerializer(
                queryset, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == 'DELETE':
            if not Subscription.objects.filter(
                user=user, author=author
            ).exists():
                return Response(
                    {'errors': 'Вы уже отписаны!'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            subscription = get_object_or_404(
                Subscription, user=user, author=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Ingredient."""

    queryset = Ingredient.objects.all()
    pagination_class = None
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для создания обьектов класса Recipe."""

    queryset = Recipe.objects.select_related(
        'author'
    ).prefetch_related('tags', 'ingredients')
    permission_classes = (AuthorOrReadOnly | IsAdminOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
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

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        return self.create_favorite_or_shoppingcart(
            FavoriteCreateDeleteSerializer, request.user, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        return self.delete_favorite_or_shoppingcart(
            Favorite, request.user, pk)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self.create_favorite_or_shoppingcart(
            ShoppingCartCreateDeleteSerializer, request.user, pk)

    @shopping_cart.mapping.delete
    def del_shopping_cart(self, request, pk=None):
        return self.delete_favorite_or_shoppingcart(
            ShoppingCart, request.user, pk)

    @action(methods=('get',), detail=False)
    def download_shopping_cart(self, request):
        shopping_cart = (
            RecipeIngredient.objects.select_related(
                'recipe',
                'ingredient'
            )
            .filter(recipe__recipes_shoppingcart_related__user=request.user)
            .values_list(
                'ingredient__name',
                'ingredient__measurement_unit',
            )
            .annotate(amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        return self.create_file_response(shopping_cart)

    @staticmethod
    def create_file_response(shopping_cart):
        buffer = io.StringIO()
        buffer.write(
            '\n'.join('\t'.join(map(str, item)) for item in shopping_cart)
        )
        response = FileResponse(buffer.getvalue(), content_type='text/plain')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'
        return response
