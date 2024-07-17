from colorfield.fields import ColorField
from django.core.validators import (
    MaxValueValidator, MinValueValidator, RegexValidator
)
from django.db import models
from django.db.models.functions import Length

from recipes.constants import (
    MAX_VALUE, MIN_VALUE
)
from users.models import User

models.CharField.register_lookup(Length)


class Ingredient(models.Model):
    """ Модель Ингридиент """

    name = models.CharField(
        verbose_name='Название',
        max_length=200
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=200,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_unit'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Tag(models.Model):
    """ Модель Тэг """

    name = models.CharField(
        verbose_name='Название тега',
        unique=True,
        max_length=200
    )
    color = ColorField(
        verbose_name='Цветовой HEX-код',
        max_length=7,
        unique=True,
        validators=[
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message='Введенное значение не является цветом в формате HEX!'
            )
        ]
    )
    slug = models.SlugField(
        verbose_name='Уникальный слаг',
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
    """ Модель Рецепт """

    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=200
    )
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.SET_NULL,
        verbose_name='Автор рецепта',
        null=True
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipes/images/',
    )
    text = models.TextField(
        verbose_name='Описание',
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
        editable=False,
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            MinValueValidator(MIN_VALUE,
                              message=f'Минимум {MIN_VALUE} минута!'),
            MaxValueValidator(MAX_VALUE,
                              message=f'Максимум {MAX_VALUE} минут!'),
        ],
        help_text='Введите время приготовления рецепта в минутах'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
        related_name='recipes',
        blank=True,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингридиенты',
        related_name='recipes',
        through='IngredientAmount',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']
        constraints = (
            models.CheckConstraint(
                check=models.Q(name__length__gt=0),
                name='\n%(app_label)s_%(class)s_name is empty\n',
            ),
        )

    def __str__(self):
        return f'{self.name}. Автор: {self.author.username}'


class IngredientAmount(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredient',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        help_text='Выберите рецепт, к которому относится ингредиент'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        help_text='Выберите ингредиент, который используется в рецепте'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        help_text='Введите количество ингредиента в единицах измерения',
        validators=(
            MinValueValidator(
                MIN_VALUE,
                message=f'Должно быть {MIN_VALUE} и больше'),
            MaxValueValidator(
                MAX_VALUE,
                message='Число должно быть меньше чем {settings.MAX_VALUE}')),
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
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_related',
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_related',
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
    """ Модель Избранное """

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
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Корзину покупок'
