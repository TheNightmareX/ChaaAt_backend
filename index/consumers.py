import json
from typing import Any, Callable, Literal, Optional, TypedDict, TypeVar, Union

from channels.generic.websocket import WebsocketConsumer
from django.db.models import Model
from django.db.models.signals import ModelSignal, post_delete, post_save

from . import models

post_delete: ModelSignal
post_save: ModelSignal


_M = TypeVar('_M', bound=Model)


ModelUpdateEvent = Literal['create', 'update', 'delete']


class UpdateModelMessage(TypedDict):
    model: str
    pk: Union[str, int]
    event: ModelUpdateEvent
    parents: dict[str, Union[str, int]]


class UpdateConsumer(WebsocketConsumer):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.signal_receivers: list[Callable[..., None]] = []

    def connect(self):
        if self.scope['user'].is_anonymous:
            self.close()
            return

        self.accept()

        self.signal_receivers = [
            self.subscribe_model_updates(
                model=models.Message,
                condition=lambda instance, event:
                    instance.sender_membership.user != self.scope['user']
                    and instance.chatroom.memberships
                    .filter(user=self.scope['user'])
                    .exists(),
                parent_fields=[],
            ),
            self.subscribe_model_updates(
                model=models.FriendshipRequest,
                condition=lambda instance, event:
                    event != 'update'
                    and instance.target == self.scope['user'],
                parent_fields=[],
            ),
            self.subscribe_model_updates(
                model=models.ChatroomMembershipRequest,
                condition=lambda instance, event: (
                    event != 'update'
                    or instance.user != self.scope['user']
                ) and (
                    instance.user == self.scope['user']
                    or instance.chatroom.memberships
                    .filter(chatroom=instance.chatroom, user=self.scope['user'], is_manager=True)
                    .exists()
                ),
                parent_fields=[],
            ),
            self.subscribe_model_updates(
                model=models.Friendship,
                condition=lambda instance, event:
                    instance.user == self.scope['user'],
                parent_fields=[],
            ),
            self.subscribe_model_updates(
                model=models.ChatroomMembership,
                condition=lambda instance, event:
                    instance.user == self.scope['user']
                    or instance.chatroom.memberships
                    .filter(user=self.scope['user'])
                    .exists(),
                parent_fields=[],
            )
        ]

    def subscribe_model_updates(self, *, model: type[_M], condition: Callable[[_M, ModelUpdateEvent], bool], parent_fields: list[str]):
        def receiver(sender: type[_M], instance: _M, created: Optional[bool] = None, **kwargs: Any):
            event: ModelUpdateEvent = 'delete' if created is None else 'create' if created else 'update'

            if not condition(instance, event):
                return

            parents = {name: getattr(instance, name).pk
                       for name in parent_fields}

            message: UpdateModelMessage = {
                'model': sender.__name__,
                'pk': instance.pk,
                'event': event,
                'parents': parents,
            }

            self.send(json.dumps(message))

        for signal in [post_save, post_delete]:
            signal.connect(receiver, sender=model)  # type: ignore

        return receiver
