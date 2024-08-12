from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import UniqueConstraint

from recipes.constants import MAX_CHAR_LENGTH, MIN_VALUE, MAX_HEX_CHARACTERS

User = get_user_model()


class Ingredient(models.Model):
    """ Модель Ингридиент """

    name = models.CharField('Название',
                            max_length=MAX_CHAR_LENGTH)
    measurement_unit = models.CharField('Единица измерения',
                                        max_length=MAX_CHAR_LENGTH)

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

    name = models.CharField('Название', unique=True,
                            max_length=MAX_CHAR_LENGTH)
    color = models.CharField(
        'Цветовой HEX-код',
        unique=True,
        max_length=MAX_HEX_CHARACTERS,
        validators=[
            RegexValidator(
                regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
                message='Введенное значение не является цветом в формате HEX!'
            )
        ]
    )
    slug = models.SlugField('Уникальный слаг', unique=True,
                            max_length=MAX_CHAR_LENGTH)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """ Модель Рецепт """

    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    author = models.ForeignKey(
        User,
        related_name='recipes',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Автор',
    )
    text = models.TextField('Описание')
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(
            MIN_VALUE,
            message=f'Минимальное значение {MIN_VALUE}!'
        )]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """ Модель для связи Ингридиента и Рецепта """

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[MinValueValidator(
            MIN_VALUE,
            message=f'Минимальное количество {MIN_VALUE}!')]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} ({self.ingredient.measurement_unit}) -'
            f'{self.amount} '
        )


class UserRecipeDependence(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_related',
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        constraints = [
            UniqueConstraint(
                fields=['user', 'recipe'],
                name='\n%(app_label)s_%(class)s уже добавлен\n'
            )
        ]


class Favorite(UserRecipeDependence):
    """ Модель Избранное """

    class Meta(UserRecipeDependence.Meta):
        verbose_name = 'Избранное'

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Избранное'


class ShoppingCart(UserRecipeDependence):
    """ Модель Корзина покупок """

    class Meta(UserRecipeDependence.Meta):
        verbose_name = 'Корзина покупок'

    def __str__(self):
        return f'{self.user} добавил "{self.recipe}" в Корзину покупок'
