from typing import Literal

from rest_access_policy.access_policy import AccessPolicy
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from index import models


class AuthAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>', '<method:delete>'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['<method:post>'],
            'principal': ['anonymous'],
            'effect': 'allow',
            'condition': [],
        },
    ]


class UserAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['update', 'partial_update'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['is_self'],
        },
        {
            'action': ['create'],
            'principal': ['anonymous'],
            'effect': 'allow',
            'condition': [],
        },
    ]

    def is_self(self, request: Request, view: GenericViewSet, action: str):
        instance: models.User = view.get_object()
        return request.user == instance


class GenericGroupAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['*'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
    ]


class ChatroomAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>', 'create'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['destroy'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['as_creator'],
        },
        {
            'action': ['update', 'partial_update'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['as_manager'],
        },
        {
            'action': ['destroy', 'update', 'partial_update'],
            'principal': ['authenticated'],
            'effect': 'deny',
            'condition': ['is_exclusive'],
        },
    ]

    def as_creator(self, request: Request, view: GenericViewSet, action: str):
        instance: models.Chatroom = view.get_object()
        return request.user == instance.creator

    def as_manager(self, request: Request, view: GenericViewSet, action: str):
        instance: models.Chatroom = view.get_object()
        return instance.memberships.filter(user=request.user, is_manager=True).exists()

    def is_exclusive(self, request: Request, view: GenericViewSet, action: str):
        instance: models.Chatroom = view.get_object()
        return instance.friendship_exclusive == True


class ChatroomMembershipAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['destroy', 'update', 'partial_update', 'read'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['as_owner']
        },
        {
            'action': ['destroy', 'promote', 'demote'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['level_comparison:gt'],
        },
        {
            'action': ['destroy', 'promote', 'demote'],
            'principal': ['authenticated'],
            'effect': 'deny',
            'condition': ['is_exclusive'],
        },
    ]

    def is_exclusive(self, request: Request, view: GenericViewSet, action: str):
        instance: models.ChatroomMembership = view.get_object()
        return instance.chatroom.friendship_exclusive

    def level_comparison(self, request: Request, view: GenericViewSet, action: str, type: Literal['gt', 'lte']):
        target_membership: models.ChatroomMembership = view.get_object()

        try:
            own_membership = target_membership.__class__.objects.get(
                user=request.user, chatroom=target_membership.chatroom)
        except target_membership.__class__.DoesNotExist:
            return False

        return {
            'gt': own_membership.level > target_membership.level,
            'lte': own_membership.level <= target_membership.level,
        }[type]


class ChatroomMembershipRequestAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>', 'create'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['accept', 'reject'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['state_is:P', 'as_manager'],
        },
        {
            'action': ['destroy'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['state_is:P', 'as_owner'],
        }
    ]

    def as_manager(self, request: Request, view: GenericViewSet, action: str):
        instance: models.ChatroomMembershipRequest = view.get_object()
        return instance.chatroom.memberships.filter(user=request.user, is_manager=True).exists()


class FriendshipAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['*'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
    ]


class FriendshipRequestAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['<safe_methods>', 'create'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
        {
            'action': ['destroy'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['state_is:P', 'as_owner'],
        },
        {
            'action': ['accept', 'reject'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': ['state_is:P', 'as_target'],
        },
    ]

    def as_target(self, request: Request, view: GenericViewSet, action: str):
        instance: models.FriendshipRequest = view.get_object()
        return request.user == instance.target


class MessageAccessPolicy(AccessPolicy):
    statements = [
        {
            'action': ['*'],
            'principal': ['authenticated'],
            'effect': 'allow',
            'condition': [],
        },
    ]
