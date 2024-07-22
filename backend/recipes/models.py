from django.core.validators import (
    MaxValueValidator, MinValueValidator
)
from django.db import models
from django.db.models.functions import Length

from recipes.constants import (
    MIN_VALUE, MAX_VALUE, INGR_NAME_HELPER,
    MEASUREMENT_UNIT_HELPER, TAG_NAME_HELPER,
    SLUG_HELPER, REC_NAME_HELPER, AUTHOR_HELPER,
    IMAGE_HELPER, TEXT_HELPER, COOKING_TIME_HELPER,
    TAGS_OF_REC_HELPER, INGREDIENT_RECIPE_HELPER,
    INGREDIENT_AMOUNT_HELPER
)
from users.models import User

models.CharField.register_lookup(Length)


class Ingredient(models.Model):
    """Модель Ингридиент"""

    name = models.CharField(
        verbose_name='Название.',
        help_text=INGR_NAME_HELPER,
        max_length=200,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        help_text=MEASUREMENT_UNIT_HELPER,
        max_length=200,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_unit',
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """ Модель Тэг """

    name = models.CharField(
        verbose_name='Название тега',
        help_text=TAG_NAME_HELPER,
        unique=True,
        max_length=200,
    )
    color = models.CharField(
        verbose_name='HEX-цвет тега',
        max_length=7,
    )
    slug = models.SlugField(
        verbose_name="Слаг",
        help_text=SLUG_HELPER,
        unique=True,
        max_length=200,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель Рецепт"""

    author = models.ForeignKey(
        User,
        verbose_name='Автор публикации',
        related_name='recipes',
        help_text=AUTHOR_HELPER,
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name='Название',
        help_text=REC_NAME_HELPER,
        max_length=200,
    )
    image = models.ImageField(
        verbose_name='Картинка',
        help_text=IMAGE_HELPER,
        upload_to='recipes/images/',
    )
    text = models.TextField(
        verbose_name='Текстовое описание',
        help_text=TEXT_HELPER,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингридиенты',
        related_name='recipes',
        help_text=INGREDIENT_RECIPE_HELPER,
        through='RecipeIngredient',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
        related_name='recipes',
        blank=True,
        help_text=TAGS_OF_REC_HELPER,
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления (в минутах)',
        help_text=COOKING_TIME_HELPER,
        validators=[
            MinValueValidator(
                MIN_VALUE,
                message=f'Минимум {MIN_VALUE} минута!'
            ),
            MaxValueValidator(
                MAX_VALUE,
                message=f'Максимум {MAX_VALUE} минут!'
            ),
        ],
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
        db_index=True,
        editable=False
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Модель количества ингредиентов в рецепте"""

    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredient',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        help_text=INGREDIENT_AMOUNT_HELPER,
        validators=(
            MinValueValidator(
                MIN_VALUE,
                message=f'Должно быть {MIN_VALUE} и больше'),
            MaxValueValidator(
                MAX_VALUE,
                message=f'Число должно быть больше {MAX_VALUE}')),
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты рецепта'
        ordering = ('id',)
        unique_together = ('recipe', 'ingredient')

    def __str__(self) -> str:
        return (
            f'{self.ingredient.name} ({self.ingredient.measurement_unit}) - '
            f'{self.amount} '
        )


class Favorite(models.Model):
    """Модель избранных рецептов"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorite",
        verbose_name="Рецепт",
    )
    date_added = models.DateTimeField(
        verbose_name="Дата добавления",
        auto_now_add=True,
        editable=False,
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

        constraints = (
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_favorite_recipe"
            ),
        )

    def __str__(self):
        return f"Рецепт {self.recipe} в избранном у пользователя {self.user}"


class ShoppingCart(models.Model):
    """Модель корзины покупок"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_list",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_list",
        verbose_name="Рецепт",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Список покупок"

        constraints = (
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_shopping_list_recipe"
            ),
        )

    def __str__(self):
        return (
            f"Рецепт {self.recipe} в списке покупок у пользователя {self.user}"
        )
