[![Main Foodgram workflow](https://github.com/QussaQu/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/QussaQu/foodgram/actions/workflows/main.yml)

# FoodGram
 
Ознакомиться с проекто можете по [ссылке](http://fooodgram-new.zapto.org)

## Описание
«Фудграм» — это сайт, на котором можно публиковать собственные рецепты, добавлять чужие рецепты в избранное, подписываться на других авторов и создавать список покупок для заданных блюд.
Вот, что было сделано в ходе работы над проектом:
- настроено взаимодействие Python-приложения с внешними API-сервисами;
- создан собственный API-сервис на базе проекта Django;
- подключено SPA к бэкенду на Django через API;
- созданы образы и запущены контейнеры Docker;
- созданы, развёрнуты и запущены на сервере мультиконтейнерные приложения;
- закреплены на практике основы DevOps, включая CI&CD.

**Инструменты и стек:** #python #JSON #YAML #Django #React #API #Docker #Nginx #PostgreSQL #Gunicorn #JWT #Postman #Djoser #PyJWT #Pillow

### Запуск проекта на локальной машине:

- Клонировать репозиторий:
```
https://github.com/QussaQu/foodgram.git
```

- В директории infra создать файл .env и заполнить своими данными по аналогии с example.env:
```
SECRET_KEY='django-insecure-******'
DEBUG=True / False
ALLOWED_HOSTS=00.000.000.000 127.0.0.1 localhost *******.org
DB_ENGINE=django.db.backends.postgresql # работаем с БД postgresql
POSTGRES_DB=foodgram_db # имя БД
POSTGRES_USER=foodgram_user # имя пользователя БД
POSTGRES_PASSWORD=foodgram_password # пароль от БД
DB_HOST=db
DB_PORT=5432
```

- Создать и запустить контейнеры Docker, последовательно выполнить команды по созданию миграций, сбору статики, 
созданию суперпользователя, как указано выше.
```
docker-compose -f docker-compose-local.yml up -d
```


- После запуска проект будут доступен по адресу: [http://localhost/](http://localhost/)

## Запуск приложения в контейнере на сервере

- Установить на сервере Docker, Docker Compose:

```
sudo apt install curl                                   # установка утилиты для скачивания файлов
curl -fsSL https://get.docker.com -o get-docker.sh      # скачать скрипт для установки
sh get-docker.sh                                        # запуск скрипта
sudo apt-get install docker-compose-plugin              # последняя версия docker compose
```

- Скопировать на сервер файлы docker-compose.yml, nginx.conf из папки infra (команды выполнять находясь в папке infra):

```
scp docker-compose.yml nginx.conf username@IP:/home/username/   # username - имя пользователя на сервере
                                                                # IP - публичный IP сервера
```

1. Скачайте foodgram-проект с [github](https://github.com/QussaQu/foodgram) - в консоли (терминале) нужно прописать git clone git@github.com:QussaQu/foodgram.git;
2. После скачивания проекта перейтите в дерикторию foodgram, затем в infra (cd foodgram/infra);
3. Создайте в данной дериктории файл .env (sudo touch .env). Откройте созданный файл .env (sudo nano .env);
4. В открывшимся окне пропишите "секреты" для backend.settings:
```
SECRET_KEY='django-insecure-******'
DEBUG=True / False
ALLOWED_HOSTS=00.000.000.000 127.0.0.1 localhost *******.org
DB_ENGINE=django.db.backends.postgresql # работаем с БД postgresql
POSTGRES_DB=foodgram_db # имя БД
POSTGRES_USER=foodgram_user # имя пользователя БД
POSTGRES_PASSWORD=foodgram_password # пароль от БД
DB_HOST=db
DB_PORT=5432
```
5. Перейдите в дерикторию foodgram/backend для создания образа
```cd .. ``` -> ```cd backend```;
6. Создайте образ командой ```sudo docker build -t [Ваш ник на https://hub.docker.com/]/foodgram_backend .```;
7. Поступите также с frontend -->  ```cd ..```, ```cd frontend```, ```sudo docker build -t [Ваш ник на https://hub.docker.com/]/foodgram_frontend .```;
8. Запуште образы на сервер: ```sudo docker push [Ваш ник на https://hub.docker.com/]/foodgram_backend```, ```sudo docker push [Ваш ник на https://hub.docker.com/]/foodgram_frontend```;
9. Перейдя в дерикторию infra ```cd ...```, ```cd infra``` 'стяните' образы: ```sudo docker compose -f docker-compose.yml pull```;
10. Затем запустите сервер: ```sudo docker compose -f docker-compose.yml up -d```;
11. Создайте миграции командой ```sudo docker compose -f docker-compose.yml exec backend python manage.py makemigrations```;
12. Мигрируйте созданные поля в базу данных: ```sudo docker compose -f docker-compose.yml exec backend python manage.py migrate```;
13. Подключите статику: ```sudo docker compose exec backend python manage.py collectstatic --noinput```;
14. Загрузите готовые ингредиенты и теги: ```sudo docker compose exec backend python manage.py load```;
15. Для создания суперпользователя воспользуйтесь клмандой: ```sudo docker-compose exec backend python manage.py createsuperuser```;
16. Перейдите на выбранный Вами url для ознакомления с проектом.
-------

Секретные данные:
username: admin
pass: Praktikum+123
email: admin@admin.com

-------
- Для остановки контейнеров Docker:
```
sudo docker compose down -v      # с их удалением
sudo docker compose stop         # без удаления
```

- Для работы с GitHub Actions необходимо в репозитории в разделе Secrets > Actions создать переменные окружения:
```
SECRET_KEY              # секретный ключ Django проекта
DOCKER_PASSWORD         # пароль от Docker Hub
DOCKER_USERNAME         # логин Docker Hub
HOST                    # публичный IP сервера
USER                    # имя пользователя на сервере
PASSPHRASE              # *если ssh-ключ защищен паролем
SSH_KEY                 # приватный ssh-ключ
TELEGRAM_TO             # ID телеграм-аккаунта для посылки сообщения
TELEGRAM_TOKEN          # токен бота, посылающего сообщение

DB_ENGINE               # django.db.backends.postgresql
POSTGRES_DB             # postgres
POSTGRES_USER           # postgres
POSTGRES_PASSWORD       # postgres
DB_HOST                 # db
DB_PORT                 # 5432 (порт по умолчанию)
```
------------------------------------------------------------------

## Инфраструктура проекта
**Главная** - https://localhost/recipes/ \
**API** - https://localhost/api/ \
**Redoc** - https://localhost/api/docs/ \
**Админка** -https://localhost/admin/

## Примеры запросов
1. Получение списка рецептов: \
   **GET** `/api/recipes/` \
   REQUEST
   ```json
   {
     "count": 123,
     "next": "http://127.0.0.1:9090/api/recipes/?page=2",
     "previous": "http://127.0.0.1:9090/api/recipes/?page=1",
     "results": [
       {
         "id": 0,
         "tags": [
           {
             "id": 0,
             "name": "Завтрак",
             "color": "yellow",
             "slug": "breakfast"
           }
         ],
         "author": {
           "email": "ya@ya.ru",
           "id": 0,
           "username": "user",
           "first_name": "Robert",
           "last_name": "Anderson",
           "is_subscribed": false
         },
         "ingredients": [
           {
             "id": 0,
             "name": "Курица",
             "measurement_unit": "г",
             "amount": 100
           }
         ],
         "is_favorite": false,
         "is_in_shopping_cart": false,
         "name": "string",
         "image": "https://backend:9090/media/recipes/images/image.jpeg",
         "text": "string",
         "cooking_time": 10
       }
     ]
   }
   ```
2. Регистрация пользователя: \
   **POST** `/api/users/` \
   RESPONSE
   ```json
   {
     "email": "ya@ya.ru",
     "username": "user",
     "first_name": "Robert",
     "last_name": "Anderson",
     "password": "super_password1"
   }
   ```
   REQUEST
   ```json
   {
   "email": "ya@ya.ru",
   "id": 0,
   "username": "user",
   "first_name": "Robert",
   "last_name": "Anderson"
   }
   ```
3. Подписаться на пользователя: \
   **POST** `/api/users/{id}/subscribe/`
   REQUEST
   ```json
   {
     "email": "user@example.com",
     "id": 0,
     "username": "user",
     "first_name": "Robert",
     "last_name": "Anderson",
     "is_subscribed": true,
     "recipes": [
       {
         "id": 0,
         "name": "string",
         "image": "https://backend:9090/media/recipes/images/image.jpeg",
         "cooking_time": 10
       }
     ],
     "recipes_count": 1
   }
   ```
## Об авторе
Python-разработчик
>[QussaQu](https://github.com/QussaQu).
