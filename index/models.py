from datetime import datetime
from typing import Iterable, Literal, Optional

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.manager import Manager
from django.utils import timezone
from drfutils.models import RelatedManager
from rest_framework.authtoken.models import Token


class User(AbstractUser):
    objects: UserManager['User']

    auth_token: Token

    friendships: RelatedManager['Friendship']
    friendship_groups: RelatedManager['FriendshipGroup']
    friendship_requests_sent: RelatedManager['FriendshipRequest']
    friendship_requests_received: RelatedManager['FriendshipRequest']

    chatrooms_created: RelatedManager['Chatroom']
    chatroom_membership_groups: RelatedManager['ChatroomMembershipGroup']
    chatroom_memberships: RelatedManager['ChatroomMembership']
    chatroom_membership_requests: RelatedManager['ChatroomMembershipRequest']

    bio: str = models.TextField(max_length=50, blank=True,  # type: ignore
                                default='')
    sex: str = models.CharField(max_length=1,  # type: ignore
                                choices=[('M', 'Male'),
                                         ('F', 'Female'),
                                         ('X', 'Secret')],
                                default='X')

    def save(self, force_insert: bool = False, force_update: bool = False, using: Optional[str] = None, update_fields: Optional[Iterable[str]] = None):
        is_creation = not bool(self.pk)

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

        if is_creation:
            Token.objects.create(user=self)


class Chatroom(models.Model):
    objects: Manager['Chatroom']
    messages: RelatedManager['Message']
    memberships: RelatedManager['ChatroomMembership']
    membership_requests: RelatedManager['ChatroomMembershipRequest']

    name: str = models.CharField(max_length=20)  # type: ignore
    creator: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                      related_name='chatrooms_created')
    friendship_exclusive: bool = models.BooleanField(  # type: ignore
        default=False)
    creation_time: datetime = models.DateTimeField(  # type: ignore
        auto_now_add=True)

    def __str__(self):
        return f'{self.pk}: {self.name}'

    def save(self, force_insert: bool = False, force_update: bool = False, using: Optional[str] = None, update_fields: Optional[Iterable[str]] = None):
        """Create a membership for the creator during creation.
        """
        is_creation = not bool(self.pk)

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

        if is_creation:
            self.memberships.add(
                ChatroomMembership.objects.create(
                    user=self.creator,
                    chatroom=self,
                    is_manager=True,
                )
            )


class ChatroomMembershipGroup(models.Model):
    objects: Manager['ChatroomMembershipGroup']
    chatroom_memberships: RelatedManager['ChatroomMembership']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='chatroom_membership_groups')
    name: str = models.CharField(max_length=20)  # type: ignore

    class Meta:  # type: ignore
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'],
                                    name='chatroom_group__unique_group_name')
        ]

    def __str__(self):
        return self.name


class ChatroomMembership(models.Model):
    class Meta:  # type: ignore
        constraints = [
            models.UniqueConstraint(fields=['user', 'chatroom'],
                                    name='chatroom_membership__unique_chatroom_membership'),
        ]

    objects: Manager['ChatroomMembership']
    messages_sent: RelatedManager['Message']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='chatroom_memberships')
    chatroom: Chatroom = models.ForeignKey(Chatroom, on_delete=models.CASCADE,  # type: ignore
                                           related_name='memberships')
    groups: RelatedManager[ChatroomMembershipGroup] = models.ManyToManyField(ChatroomMembershipGroup,  # type: ignore
                                                                             blank=True,
                                                                             related_name='chatroom_memberships')
    is_manager: bool = models.BooleanField(default=False)  # type: ignore
    last_read: datetime = models.DateTimeField(  # type: ignore
        default=timezone.now)
    creation_time: datetime = models.DateTimeField(  # type: ignore
        auto_now_add=True)

    @property
    def level(self):
        if not self.is_manager:
            return 0
        elif self.chatroom.creator != self.user:
            return 1
        else:
            return 2


class ChatroomMembershipRequest(models.Model):
    class Meta:  # type: ignore
        ordering = ['-pk']
        constraints = [
            models.UniqueConstraint(fields=['user', 'chatroom'],
                                    name='chatroom_membership_request__unique_pending_request',
                                    condition=models.Q(state='P'))
        ]

    object: Manager['ChatroomMembershipRequest']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='chatroom_membership_requests')
    chatroom: Chatroom = models.ForeignKey(Chatroom, on_delete=models.CASCADE,  # type: ignore
                                           related_name='membership_requests')
    message: str = models.TextField(max_length=50, default='')  # type: ignore
    state: Literal['P', 'A', 'R'] = models.CharField(max_length=1,  # type: ignore
                                                     choices=[('P', 'Pending'),
                                                              ('A', 'Accepted'),
                                                              ('R', 'Rejected')],
                                                     default='P')
    creation_time: datetime = models.DateTimeField(  # type: ignore
        auto_now_add=True)


class FriendshipGroup(models.Model):
    class Meta:  # type: ignore
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'],
                                    name='friend_group__unique_group_name'),
        ]

    objects: Manager['FriendshipGroup']
    friendships: RelatedManager['Friendship']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='friendship_groups')
    name: str = models.CharField(max_length=20)  # type: ignore

    def __str__(self):
        return self.name


class Friendship(models.Model):
    class Meta:  # type: ignore
        constraints = [
            models.UniqueConstraint(fields=['user', 'target'],
                                    name='friend__no_duplicate_friend')
        ]

    objects: Manager['Friendship']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='friendships')
    target: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                     related_name='+')
    groups: RelatedManager[FriendshipGroup] = models.ManyToManyField(FriendshipGroup,  # type: ignore
                                                                     blank=True,
                                                                     related_name='friendships')
    nickname: str = models.CharField(max_length=20,  # type: ignore
                                     null=True,
                                     blank=True)
    important: bool = models.BooleanField(default=False)  # type: ignore
    chatroom: Chatroom = models.ForeignKey(Chatroom, on_delete=models.CASCADE,  # type: ignore
                                           related_name='+')

    @property
    def symmetrical_object(self):
        qs = self.__class__.objects.filter(user=self.target, target=self.user)
        return qs[0] if qs.exists() else None

    def __str__(self):
        return f'{self.user} -> {self.target}'

    def save(self, force_insert: bool = False, force_update: bool = False, using: Optional[str] = None, update_fields: Optional[Iterable[str]] = None):
        """Create the required related objects during creation.
        """
        is_creation = not bool(self.pk) and not self.symmetrical_object

        if is_creation:
            # exclusive chatroom
            self.chatroom = Chatroom.objects.create(
                name='',
                creator=self.user,
                friendship_exclusive=True,
            )

            # exclusive chatroom membership
            self.chatroom.memberships.add(
                ChatroomMembership.objects.create(
                    user=self.target,
                    chatroom=self.chatroom,
                    is_manager=True
                )
            )

        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

        if is_creation:
            # symmetrical object
            self.__class__.objects.create(
                user=self.target,
                target=self.user,
                chatroom=self.chatroom,
            )

    def delete(self, using: Optional[str] = None, keep_parents: bool = True):
        """Delete the related objects.
        """
        ret = super().delete(using=using, keep_parents=keep_parents)
        if symmetrical_object := self.symmetrical_object:
            symmetrical_object.delete()
            self.chatroom.delete()
        return ret


class FriendshipRequest(models.Model):
    class Meta:  # type: ignore
        ordering = ['-pk']
        constraints = [
            models.UniqueConstraint(fields=['user', 'target'],
                                    name='friend_request__unique_pending_request',
                                    condition=models.Q(state='P'))
        ]

    objects: Manager['FriendshipRequest']

    user: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                   related_name='friendship_requests_sent')
    target: User = models.ForeignKey(User, on_delete=models.CASCADE,  # type: ignore
                                     related_name='friendship_requests_received')
    message: str = models.TextField(max_length=50, default='')  # type: ignore
    state: Literal['P', 'A', 'R'] = models.CharField(max_length=1,  # type: ignore
                                                     choices=[('P', 'Pending'),
                                                              ('A', 'Accepted'),
                                                              ('R', 'Rejected')],
                                                     default='P')
    creation_time: datetime = models.DateTimeField(  # type: ignore
        auto_now_add=True)


class Message(models.Model):
    class Meta:  # type: ignore
        ordering = ['-pk']

    objects: Manager['Message']

    sender_membership: ChatroomMembership = models.ForeignKey(ChatroomMembership, on_delete=models.CASCADE,  # type: ignore
                                                              related_name='messages_sent')
    chatroom: Chatroom = models.ForeignKey(Chatroom, on_delete=models.CASCADE,  # type: ignore
                                           related_name='messages')
    text: str = models.TextField(max_length=1000)  # type: ignore
    creation_time: datetime = models.DateTimeField(  # type: ignore
        auto_now_add=True)
