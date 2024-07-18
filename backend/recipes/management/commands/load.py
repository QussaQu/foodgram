import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from recipes.models import (
    IngredientAmount, Favorite,
    Ingredient, Recipe,
    ShoppingCart, Tag
)
from users.models import Subscription, User


class Command(BaseCommand):
    help = 'Загрузить данные в модели ингредиентов и тегов'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            '--files',
            nargs='+',
            type=str,
            default=['ingredients.json', 'tags.json'],
        )
        parser.add_argument(
            '-m',
            '--models',
            nargs='+',
            type=str,
            default=['Ingredient', 'Tag'],
        )

    def load_data(self, file_name, model):
        with open(
            f'{settings.BASE_DIR}/data/{file_name}', encoding='utf-8'
        ) as data_file:
            data = json.load(data_file)
            for item in data:
                model.objects.get_or_create(**item)

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Начало загрузки'))
        files = kwargs['files']
        models = kwargs['models']
        if len(files) != len(models):
            raise CommandError(
                'Количество файлов и моделей не должно различаться'
            )
        model_dict = {
            'Ingredient': Ingredient,
            'Tag': Tag,
            'Recipe': Recipe,
            'ShoppingCart': ShoppingCart,
            'AmountIngredient': IngredientAmount,
            'Favorite': Favorite,
            'User': User,
            'Subscription': Subscription,
        }
        for file_name, model_name in zip(files, models):
            model = model_dict.get(model_name)
            if not model:
                raise CommandError(f'Модель {model_name} не найдена')
            self.load_data(file_name, model)
        self.stdout.write(
            self.style.SUCCESS('Загрузка успешно завершена')
        )
