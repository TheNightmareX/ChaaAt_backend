from typing import Any

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models as m
from django.db.models.manager import BaseManager

from datetime import datetime


class User(AbstractUser):
    objects: UserManager['User']
    
    friend_relations_sent: BaseManager['FriendRelation']
    friend_relations_received: BaseManager['FriendRelation']
    messages_sent: BaseManager['Message']


class Chatroom(m.Model):
    objects: BaseManager['Chatroom']

    messages: BaseManager['Message']

    members: BaseManager[User] = m.ManyToManyField(User)


class FriendRelation(m.Model):
    objects: BaseManager['FriendRelation']

    source_user: User = m.ForeignKey(User, on_delete=m.CASCADE,
                                     related_name='friend_relations_sent')
    target_user: User = m.ForeignKey(User, on_delete=m.CASCADE,
                                     related_name='friend_relations_received')
    accepted: bool = m.BooleanField(default=False)
    chatroom: Chatroom = m.ForeignKey(Chatroom, on_delete=m.CASCADE,
                                      related_name='+')

    class Meta:
        constraints = [
            m.UniqueConstraint(fields=['source_user', 'target_user'],
                               name='unique_relation')
        ]

    def delete(self, using: Any = None, keep_parents: bool = False):
        """Destroy the chatroom after the relation is deleted.
        """
        chatroom: Chatroom = self.chatroom
        result = super().delete(using, keep_parents)
        chatroom.delete()
        return result


class Message(m.Model):
    objects: BaseManager['Message']

    text: str = m.TextField(max_length=300)
    sender: User = m.ForeignKey(User, on_delete=m.CASCADE,
                                related_name='messages_sent')
    chatroom: Chatroom = m.ForeignKey(Chatroom, on_delete=m.CASCADE,
                                      related_name='messages')
    creation_time: datetime = m.DateTimeField(auto_now_add=True)
