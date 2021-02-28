from typing import Any, Callable

from django.db.models.query import QuerySet
from django.http.request import QueryDict
from drfutils.serializers import validation
from rest_flex_fields.serializers import FlexFieldsModelSerializer
from rest_framework import serializers, validators

from . import models


class QuotaValidator:
    requires_context = True

    def __init__(self, get_queryset: Callable[[serializers.ModelSerializer[Any]], QuerySet[Any]], quota: int):
        self.get_queryset = get_queryset
        self.quota = quota

    @validation
    def __call__(self, data: Any, serializer: serializers.ModelSerializer[Any]):
        queryset = self.get_queryset(serializer)
        assert ((count := queryset.count()) < self.quota), (
            f'Quota exceeded: {count}/{self.quota}'
        )


class UserSerializer(FlexFieldsModelSerializer[models.User]):
    class Meta:
        model = models.User
        fields = ['pk', 'username', 'password', 'sex', 'bio']
        read_only_fields = []
        extra_kwargs = {'password': {'write_only': True}}
        expandable_fields = {}
        validators = []

    def create(self, validated_data: dict[str, str]):
        user = self.Meta.model.objects.create_user(username=validated_data['username'],
                                                   password=validated_data['password'])
        return user

    def update(self, instance: models.User, validated_data: dict[str, Any]):
        if password := validated_data.pop('password', None):
            instance.set_password(password)
        return super().update(instance, validated_data)


class ChatroomSerializer(FlexFieldsModelSerializer[models.Chatroom]):
    class Meta:
        model = models.Chatroom
        fields = ['pk', 'creator', 'name',
                  'friendship_exclusive', 'creation_time']
        read_only_fields = ['creator', 'friendship_exclusive']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'creator': UserSerializer,
        }
        validators = [
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    creator=s.context['request'].user
                ),
                quota=10,
            ),
        ]

    def to_internal_value(self, data: QueryDict):
        ret = super().to_internal_value(data)
        if not self.instance:
            ret['creator'] = self.context['request'].user
        return ret


class ChatroomMembershipGroupSerializer(FlexFieldsModelSerializer[models.ChatroomMembershipGroup]):
    class Meta:
        model = models.ChatroomMembershipGroup
        fields = ['pk', 'user', 'name', 'item_count']
        read_only_fields = []
        extra_kwargs = {}
        expandable_fields = {}
        validators = [
            validators.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=['user', 'name'],
                message='The group name had already existed.',
            ),
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user,
                ),
                quota=15,
            ),
        ]

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    item_count = serializers.SerializerMethodField()

    def get_item_count(self, instance: models.ChatroomMembershipGroup):
        return instance.chatroom_memberships.count()


class ChatroomMembershipSerializer(FlexFieldsModelSerializer[models.ChatroomMembership]):
    class Meta:
        model = models.ChatroomMembership
        fields = ['pk', 'user', 'chatroom', 'groups', 'is_manager',
                  'creation_time']
        read_only_fields = ['user', 'chatroom', 'is_manager']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'user': UserSerializer,
            'chatroom': ChatroomSerializer,
        }
        validators = [
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user,
                ),
                quota=30,
            ),
        ]

    def to_representation(self, instance: models.ChatroomMembership):
        ret: dict[str, Any] = super().to_representation(instance)
        if self.context['request'].user != instance.user:
            ret['groups'] = None
        return ret


class ChatroomMembershipRequestSerializer(FlexFieldsModelSerializer[models.ChatroomMembershipRequest]):
    class Meta:
        model = models.ChatroomMembershipRequest
        fields = ['pk', 'user', 'chatroom',
                  'message', 'state', 'creation_time']
        read_only_fields = ['user', 'state']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'user': UserSerializer,
            'chatroom': ChatroomSerializer,
        }
        validators = [
            validators.UniqueTogetherValidator(
                queryset=model.objects.filter(state='P'),
                fields=['user', 'chatroom'],
                message='There is already a pending request.'
            ),
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user,
                    state='P',
                ),
                quota=20,
            ),
        ]

    def to_internal_value(self, data: QueryDict):
        ret = super().to_internal_value(data)
        if not self.instance:
            ret['user'] = self.context['request'].user
            ret['state'] = 'P'
        return ret

    @validation
    def validate_chatroom(self, value: models.Chatroom):
        assert not models.ChatroomMembership.objects.filter(
            user=self.context['request'].user,
            chatroom=value,
        ).exists(), (
            'The membership has already existed.'
        )


class FriendshipGroupSerializer(FlexFieldsModelSerializer[models.FriendshipGroup]):
    class Meta:
        model = models.FriendshipGroup
        fields = ['pk', 'user', 'name', 'item_count']
        read_only_fields = []
        extra_kwargs = {}
        expandable_fields = {}
        validators = [
            validators.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=['user', 'name'],
                message='The group name had already existed.',
            ),
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user,
                ),
                quota=15,
            ),
        ]

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    item_count = serializers.SerializerMethodField()

    def get_item_count(self, instance: models.FriendshipGroup):
        return instance.friendships.count()


class FriendshipSerializer(FlexFieldsModelSerializer[models.Friendship]):
    class Meta:
        model = models.Friendship
        fields = ['pk', 'user', 'target', 'chatroom',
                  'groups', 'nickname', 'important', 'creation_time']
        read_only_fields = ['chatroom']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'target': UserSerializer,
            'chatroom': ChatroomSerializer,
        }
        validators = [
            validators.UniqueTogetherValidator(
                queryset=model.objects.all(),
                fields=['user', 'target'],
                message='The friendship had already existed.',
            ),
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user,
                ),
                quota=50,
            ),
        ]

    @validation
    def validate_target(self, value: models.User):
        assert not isinstance(self.instance, self.Meta.model) or self.instance.target == value, (
            '`target` is immutable'
        )

        assert self.context['request'].user != value, (
            'Cannot create friendship with yourself'
        )

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    creation_time = serializers.DateTimeField(read_only=True,
                                              source='chatroom.creation_time')


class FriendshipRequestSerializer(FlexFieldsModelSerializer[models.FriendshipRequest]):
    class Meta:
        model = models.FriendshipRequest
        fields = ['pk', 'user', 'target', 'message', 'state', 'creation_time']
        read_only_fields = ['user', 'state']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'user': UserSerializer,
            'target': UserSerializer,
        }
        validators = [
            validators.UniqueTogetherValidator(
                queryset=model.objects.filter(state='P'),
                fields=['user', 'target'],
                message='There is already a pending request.'
            ),
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    user=s.context['request'].user
                ),
                quota=50,
            ),
        ]

    def to_internal_value(self, data: QueryDict):
        ret = super().to_internal_value(data)
        if not self.instance:
            ret['user'] = self.context['request'].user
            ret['state'] = 'P'
        return ret

    @validation
    def validate_target(self, value: models.User):
        cur_user = self.context['request'].user

        assert not value == cur_user, (
            'Cannot sent friendship request to yourself.'
        )

        assert not self.Meta.model.objects.filter(
            user=value,
            target=cur_user,
            state='P',
        ).exists(), (
            'There is already an inverse pending request.'
        )

        assert not models.Friendship.objects.filter(
            user=cur_user,
            target=value,
        ).exists(), (
            'The friendship has already existed.'
        )


class MessageSerializer(FlexFieldsModelSerializer[models.Message]):
    class Meta:
        model = models.Message
        fields = ['pk', 'sender_membership',
                  'chatroom', 'text', 'read', 'creation_time']
        read_only_fields = ['sender_membership']
        extra_kwargs = {}
        expandable_fields = {  # type: ignore
            'sender_membership': ChatroomMembershipSerializer,
        }
        validators = [
            QuotaValidator(
                get_queryset=lambda s: s.Meta.model.objects.filter(
                    sender_membership__user=s.context['request'].user,
                ),
                quota=500,
            ),
        ]

    read = serializers.SerializerMethodField()

    def get_read(self, instance: models.Message):
        membership = instance.chatroom.memberships.get(
            user=self.context['request'].user)
        return instance.sender_membership.user == self.context['request'].user or instance.creation_time <= membership.last_read

    def to_internal_value(self, data: QueryDict):
        ret = super().to_internal_value(data)
        if not self.instance:
            ret['sender_membership'] = models.ChatroomMembership.objects.get(
                user=self.context['request'].user,
                chatroom=ret['chatroom'],
            )
        return ret

    @validation
    def validate_chatroom(self, value: models.Chatroom):
        assert value.memberships.filter(user=self.context['request'].user).exists(), (
            'You are not a member of the chatroom.'
        )
