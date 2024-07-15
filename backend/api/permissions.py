from rest_framework import permissions


class AuthorOrReadOnly(permissions.BasePermission):
    """Предоставляет права на осуществление опасных методов запроса
    только автору объекта, в остальных случаях
    доступ запрещен."""

    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
            and request.user == obj.author
        )
