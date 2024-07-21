from colorfield.fields import ColorField
from django.core.validators import (
    MaxValueValidator, MinValueValidator, RegexValidator
)
from django.db import models
from django.db.models.functions import Length

from recipes.constants import (
    MIN_VALUE, MAX_VALUE, INGR_NAME_HELPER,
    MEASUREMENT_UNIT_HELPER, TAG_NAME_HELPER,
    COLOR_HELPER, SLUG_HELPER, REC_NAME_HELPER,
    AUTHOR_HELPER, IMAGE_HELPER, TEXT_HELPER,
    PUB_DATE_HELPER, COOKING_TIME_HELPER,
    TAGS_OF_REC_HELPER, INGREDIENT_RECIPE_HELPER,
    INGREDIENT_AMOUNT_HELPER
)
from users.models import User

models.CharField.register_lookup(Length)


class Ingredient(models.Model):
    """Модель Ингридиент"""

    name = models.CharField(
        verbose_name='Название ингредиента',
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
    color = ColorField(
        verbose_name='Цветовой HEX-код',
        help_text=COLOR_HELPER,
        max_length=7,
        unique=True,
        validators=[
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message='Введенное значение не является цветом в формате HEX!',
            )
        ]
    )
    slug = models.SlugField(
        verbose_name="Идентификатор тега",
        help_text=SLUG_HELPER,
        unique=True,
        max_length=200,
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель Рецепт"""

    name = models.CharField(
        verbose_name='Название рецепта',
        help_text=REC_NAME_HELPER,
        max_length=200,
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        related_name='recipes',
        help_text=AUTHOR_HELPER,
        on_delete=models.CASCADE,
    )
    image = models.ImageField(
        verbose_name='Изображение',
        help_text=IMAGE_HELPER,
        upload_to='recipes/images/',
    )
    text = models.TextField(
        verbose_name='Описание',
        help_text=TEXT_HELPER,
        null=True,
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        help_text=PUB_DATE_HELPER,
        auto_now_add=True,
        editable=False,
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
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Список тегов',
        related_name='recipes',
        help_text=TAGS_OF_REC_HELPER,
        blank=True,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингридиенты',
        related_name='recipes',
        help_text=INGREDIENT_RECIPE_HELPER,
        through='RecipeIngredient',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)
        constraints = (
            models.CheckConstraint(
                check=models.Q(name__length__gt=0),
                name='\n%(app_label)s_%(class)s_name is empty\n',
            ),
        )

    def __str__(self):
        return f'{self.name}. Автор: {self.author.username}'


class RecipeIngredient(models.Model):
    """Модель рецептов/ингредиентов"""

    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredient',
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
    )
    amount = models.PositiveSmallIntegerField(
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
        ordering = ('recipe',)

    def __str__(self) -> str:
        return (
            f'{self.ingredient.name} ({self.ingredient.measurement_unit}) - '
            f'{self.amount} '
        )


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='%(app_label)s_%(class)s_related',
        help_text='Пользователь',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        related_name='%(app_label)s_%(class)s_related',
        help_text='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name=('\n%(app_label)s_%(class)s recipe is'
                      ' already related to user\n'),
            ),
        )


class Favorite(UserRecipeRelation):
    """Модель избранных рецептов"""

    date_added = models.DateTimeField(
        verbose_name='Дата добавления',
        auto_now_add=True,
        editable=False,
    )

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Избранное'


class ShoppingCart(UserRecipeRelation):
    """ Модель Корзина покупок """

    class Meta(UserRecipeRelation.Meta):
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзина покупок'

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Корзину покупок'
