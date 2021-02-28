from functools import wraps
from typing import Any, Callable, Optional, Sequence, TypeVar, Union
from rest_framework.fields import empty
from rest_framework.request import Request
from rest_framework.serializers import BaseSerializer, Serializer, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import GenericViewSet
from django.db.models import Model

_T = TypeVar('_T')
_IN = TypeVar('_IN', bound=Model)


def validation(fn: Callable[..., None]):
    """Provide a more convenient way to validate.

    It will convert the AssertionError into ValidationError and return the value
    automatically if there's no error.
    """
    @wraps(fn)
    def wrap(self: Serializer[Any], value: _T, *args: Any, **kwargs: Any) -> _T:
        try:
            fn(self, value, *args, **kwargs)
            return value
        except AssertionError as e:
            raise ValidationError(str(e))
    return wrap


class FieldActionPermissionsMixin(Serializer[_IN]):
    """Provide field action permissions support.

    Example:

            class MySerializer(FieldActionPermissionsMixinp[MyModel], ModelSerializer[MyModel]):
                class Meta(FieldActionPermissionsMixin.Meta):
                    ...
                    permissions = {
                        'user': {
                            '__default__': [AllowAny],
                            'update': [MyPermission],
                            'partial_update': 'update',
                        }
                    }
                ...

    """
    __permissions_checked = False

    class Meta:
        # {<field_name>: {<viewset_action>: <list_of_permission_classes> | <another_viewset_action>}
        permissions: (
            dict[str, dict[str, Union[str, list[type[BasePermission]]]]]
        ) = {}

    def __init__(self, instance: Optional[Union[_IN, Sequence[_IN]]] = None, data: Any = empty, partial: bool = False,
                 many: bool = False, context: dict[str, Any] = {}, read_only: bool = False,
                 write_only: bool = False, required: Optional[bool] = None, default: Any = empty,
                 initial: Any = empty, source: Optional[str] = None, label: Optional[str] = None,
                 help_text: Optional[str] = None, style: Optional[dict[str, Any]] = None,
                 error_messages: Optional[dict[str, str]] = None, validators: Optional[Sequence[Callable[..., None]]] = None,
                 allow_null: bool = False):
        super().__init__(instance=instance, data=data, partial=partial, many=many, context=context, read_only=read_only, write_only=write_only, required=required, default=default,  # type: ignore
                         initial=initial, source=source, label=label, help_text=help_text, style=style, error_messages=error_messages, validators=validators, allow_null=allow_null)  # type: ignore

        # When it is a list serialization, the `instance` argument will be a list of instances,
        # but as a child serialier, only one instance will be serialized, which can only be
        # determined inside the `to_representation` method.
        if not isinstance(instance, Sequence):
            self.check_permissions(instance)

    def to_representation(self, instance: _IN) -> dict[str, Union[str, int]]:
        # (see above)
        self.check_permissions(instance)
        return super().to_representation(instance)

    def check_permissions(self, instance: Optional[_IN]):
        """Check the permission for each field and remove the failed fields.

        Pass directly if it has already been performed or `self.context` is empty.
        """
        if self.__permissions_checked or not self.context:
            return

        for field_name in self.perform_permissions_check(instance):
            del self.fields[field_name]

        self.__permissions_checked = True

    def perform_permissions_check(self, instance: Optional[_IN]):
        request: Request = self.context['request']
        view: GenericViewSet = self.context['view']
        forbidden_fields: set[str] = set()

        for field_name in self.Meta.permissions:
            if field_name not in self.fields:
                continue
            for permission_class in self.get_permission_classes(field_name, view.action):
                permission = permission_class()
                if not permission.has_permission(
                    request=request, view=view
                ) or instance and not permission.has_object_permission(
                    request=request, view=view, obj=instance
                ):
                    forbidden_fields.add(field_name)
                    break

        return forbidden_fields

    def get_permission_classes(self, field_name: str, action: str) -> list[type[BasePermission]]:
        permission_classes = (self.Meta.permissions
                              .get(field_name, {})
                              .get(action, []))
        if isinstance(permission_classes, list):
            if action == '__default__':
                return permission_classes
            return permission_classes or self.get_permission_classes(field_name, '__default__')
        else:
            return self.get_permission_classes(field_name, permission_classes)


class SerializedOutputFieldsMixin(Serializer[_IN]):
    """Serialize the specified `PrimaryKeyRelatedField` when outputting.

    Example:

            class MySerializer(SerializedOutputFieldsMixin[MyModel], ModelSerializer[MyModel]):
                class Meta(SerializedOutputFieldsMixin.Meta):
                    ...
                    serialized_output_fields = {
                        'user': UserSerializer,
                    }
                ...
    """
    class Meta:
        serialized_output_fields: (
            dict[str, type[BaseSerializer[Any]]]
        ) = {}

    def to_representation(self, instance: _IN) -> Any:
        serialized_output_fields: dict[str, type[BaseSerializer[Any]]] = getattr(
            self.Meta, 'serialized_output_fields', {})
        repr: dict[str, Any] = super().to_representation(instance)
        for field_name, serializer_class in serialized_output_fields.items():
            if field_name not in self.fields:
                continue
            repr[field_name] = serializer_class(
                instance=getattr(instance, field_name),
                context=self.context
            ).data
        return repr
