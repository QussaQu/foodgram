import io

from django.db.models import Sum
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from recipes.models import (
    RecipeIngredient, Favorite,
    Ingredient, Recipe,
    ShoppingCart, Tag
)
from api.filters import IngredientFilter, RecipeFilter
from api.paginations import CustomPagination
from api.permissions import AuthorOrReadOnly, IsAdminOrReadOnly
from ..serializers.recipes import (
    FavoriteCreateDeleteSerializer,
    IngredientSerializer, RecipeCreateSerializer,
    RecipeReadSerializer,
    ShoppingCartCreateDeleteSerializer,
    TagSerializer
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


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
        permission_classes=[permissions.IsAuthenticated],
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
        permission_classes=[permissions.IsAuthenticated],
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
