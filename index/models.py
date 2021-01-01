from typing import Any
from django.contrib.auth.models import User
from django.db import models as m


class Profile(m.Model):
    user = m.OneToOneField(User, on_delete=m.CASCADE)


class Chatroom(m.Model):
    members = m.ManyToManyField(User)


class FriendRelation(m.Model):
    source_user = m.ForeignKey(User, on_delete=m.CASCADE,
                               related_name='friend_relations_sent')
    target_user = m.ForeignKey(User, on_delete=m.CASCADE,
                               related_name='friend_relations_received')
    accepted = m.BooleanField(default=False)
    chatroom = m.ForeignKey(Chatroom, on_delete=m.CASCADE)

    class Meta:
        constraints = [
            m.UniqueConstraint(fields=['source_user', 'target_user'],
                               name='unique_relation')
        ]

    def delete(self, using: Any, keep_parents: bool):
        """Destroy the chatroom after the relation is deleted.
        """
        chatroom: Chatroom = self.chatroom
        result = super().delete(using, keep_parents)
        chatroom.delete()
        return result


class Message(m.Model):
    text = m.TextField(max_length=300)
    sender = m.ForeignKey(User, on_delete=m.CASCADE)
    chatroom = m.ForeignKey(Chatroom, on_delete=m.CASCADE)
    creation_time = m.DateTimeField(auto_now_add=True)
