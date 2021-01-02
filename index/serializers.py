from collections import OrderedDict
from typing import Any

from django.db.models.query import QuerySet
from drfutils.decorators import validation
from rest_framework import serializers as s
from rest_framework import validators as v
from rest_framework.request import Request

from . import models as m


def ensure_quota(qs: QuerySet[m.m.Model], quota: int):
    if qs.exists() and qs.count() > quota:
        for obj in qs[quota + 1:]:
            obj.delete()


class UserSerializer(s.ModelSerializer[m.User]):
    class Meta:
        model = m.User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data: dict[str, str]):
        user = m.User.objects.create_user(username=validated_data['username'],
                                          password=validated_data['password'])
        return user


class FriendRelationSerializer(s.ModelSerializer[m.FriendRelation]):
    class Meta:
        model = m.FriendRelation
        fields = ['id', 'source_user', 'target_user', 'accepted', 'chatroom']
        read_only_fields = ['source_user', 'accepted', 'chatroom']
        validators = [v.UniqueTogetherValidator(
            queryset=m.FriendRelation.objects.all(),
            fields=['source_user', 'target_user'],
            message='The relation has already existed.',
        )]

    def to_internal_value(self, data: dict[str, str]):
        """Use the current user as `source_user`.
        """
        internal_data: OrderedDict[str, Any] = super().to_internal_value(data)
        internal_data['source_user'] = self.context['request'].user
        return internal_data

    @validation
    def validate_target_user(self, user: m.User):
        """Prevent building relation with self.
        """
        current_user: m.User = self.context['request'].user
        assert user != current_user, \
            '`target_user` can not be the same as `source_user`'

    @validation
    def validate(self, data: dict[str, Any]):
        """Prevent the inverse request if the relation has already accepted.
        """
        assert not m.FriendRelation.objects.filter(source_user=data['target_user'],
                                                   target_user=data['source_user'],
                                                   accepted=True).exists(), \
            'The relation has already existed and accepted.'

    def to_representation(self, instance: m.FriendRelation):
        """Serialize the user fields.
        """
        ret: dict[str, Any] = super().to_representation(instance)
        for key in ['source_user', 'target_user']:
            ret[key] = UserSerializer(getattr(instance, key)).data
        return ret

    def create(self, validated_data: dict[str, Any]):
        """Accept the relation if both of the users have requested the relation towards each other.
        """
        inverse_relations = m.FriendRelation.objects.filter(
            source_user=validated_data['target_user'],
            target_user=validated_data['source_user'],
            accepted=False,
        )
        if inverse_relations.exists():
            inverse_relation = inverse_relations[0]
            inverse_relation.accepted = True
            inverse_relation.save()
            return inverse_relation
        else:
            chatroom = m.Chatroom.objects.create()
            chatroom.members.add(validated_data['source_user'],
                                 validated_data['target_user'])
            chatroom.save()
            validated_data['chatroom'] = chatroom
            relation: m.FriendRelation = super().create(validated_data)
            return relation


class ChatroomSerializer(s.ModelSerializer[m.Chatroom]):
    class Meta:
        model = m.Chatroom
        fields = ['id', 'members']

    @validation
    def validate_members(self, value: list[int]):
        MAX_MEMBERS = 10
        assert len(value) <= MAX_MEMBERS, \
            f'There should be at most {MAX_MEMBERS} members in a chatroom.'


class MessageSerializer(s.ModelSerializer[m.Message]):
    class Meta:
        model = m.Message
        fields = ['id', 'text', 'sender', 'chatroom', 'creation_time']
        read_only_fields = ['sender']

    @validation
    def validate_chatroom(self, chatroom: m.Chatroom):
        request: Request = self.context['request']
        # `ManyRelatedManager` actually
        assert chatroom.members.filter(pk=request.user.pk).exists(), \
            f"Require the user to be a member of the chatroom."

    def to_internal_value(self, data: dict[str, str]):
        internal_data = super().to_internal_value(data)
        internal_data['sender'] = self.context['request'].user
        return internal_data

    def create(self, validated_data: dict[str, Any]):
        message = super().create(validated_data)

        # Delete the messages which are over quota.
        chatroom = message.chatroom
        # 500 messages take up about 10kb of space
        ensure_quota(chatroom.messages, 500)

        return message
