from rest_framework import serializers, validators

from users.models import Subscription, User


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели User."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )
        read_only_fields = ('id',)

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на автора аккаунта."""

        request = self.context.get('request')
        return (request.user.is_authenticated
                and request.user.followed_users.filter(author=obj).exists())


class SubscribeSerializer(UserSerializer):
    """Сериализатор для модели Subscription."""

    recipes_count = serializers.ReadOnlyField(source='recipes.count')
    recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )
        read_only_fields = (
            'email',
            'username',
            'first_name',
            'last_name'
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Subscription."""

    class Meta:
        model = Subscription
        fields = '__all__'
        validators = [
            validators.UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('author', 'subscriber'),
                message='Вы уже подписывались на этого автора'
            )
        ]

    def validate(self, data):
        """Проверяем, что пользователь не подписывается на самого себя."""

        if data['subscriber'] == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        return data

    def to_representation(self, instance):
        return SubscribeSerializer(
            instance.author, context=self.context
        ).data
