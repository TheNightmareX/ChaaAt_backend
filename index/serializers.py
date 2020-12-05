from rest_framework import serializers as s, validators as v
from . import models as m


class ProfileSerializer(s.ModelSerializer):
    class Meta:
        model = m.Profile
        fields = ['friends']


class UserSerializer(s.ModelSerializer):
    class Meta:
        model = m.User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user: m.User = m.User.objects.create_user(username=validated_data['username'],
                                                  password=validated_data['password'])
        return user


class FriendRelationSerializer(s.ModelSerializer):
    class Meta:
        model = m.FriendRelation
        fields = ['id', 'source_user', 'target_user', 'accepted', 'chatroom']
        read_only_fields = ['source_user', 'accepted', 'chatroom']
        validators = [v.UniqueTogetherValidator(
            queryset=m.FriendRelation.objects.all(),
            fields=['source_user', 'target_user'],
            message='The relation has already existed.',
        )]

    def to_internal_value(self, data):
        """Use the current user as `source_user`.
        """
        data = super().to_internal_value(data)
        data['source_user'] = self.context['request'].user
        return data

    def validate_target_user(self, value):
        """Prevent building relation with self.
        """
        if value == self.context['request'].user:
            raise s.ValidationError(
                '`target_user` can not be the same as `source_user`')
        return value

    def validate(self, data):
        """Prevent the inverse request if the relation has already accepted.
        """
        if m.FriendRelation.objects.filter(source_user=data['target_user'],
                                           target_user=data['source_user'],
                                           accepted=True).exists():
            raise s.ValidationError(
                'The relation has already existed and accepted.')
        return data

    def to_representation(self, instance):
        """Serialize the user fields.
        """
        ret = super().to_representation(instance)
        for key in ['source_user', 'target_user']:
            ret[key] = UserSerializer(getattr(instance, key)).data
        return ret

    def create(self, validated_data):
        """Accept the relation if both of the users have requested the relation towards each other.
        """
        inverse_relation = m.FriendRelation.objects.filter(source_user=validated_data['target_user'],
                                                           target_user=validated_data['source_user'],
                                                           accepted=False)
        if inverse_relation.exists():
            inverse_relation: m.FriendRelation = inverse_relation[0]
            inverse_relation.accepted = True
            inverse_relation.save()
            return inverse_relation
        else:
            chatroom: m.Chatroom = m.Chatroom.objects.create()
            chatroom.members.add(
                validated_data['source_user'], validated_data['target_user'])
            chatroom.save()
            validated_data['chatroom'] = chatroom
            return super().create(validated_data)


class ChatroomSerializer(s.ModelSerializer):
    class Meta:
        model = m.Chatroom
        fields = ['id', 'members']


class MessageSerializer(s.ModelSerializer):
    class Meta:
        model = m.Message
        fields = ['id', 'text', 'sender', 'chatroom', 'creation_time']
        read_only_fields = ['sender']

    def create(self, validated_data):
        """Set `sender` as the current user.
        """
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)
