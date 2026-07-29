from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True, validators=[MaxLengthValidator(300)])
    public_key_jwk = models.TextField(blank=True)
    key_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile({self.user.username})"


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_links")
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["follower", "followed"], name="unique_follow")]
        indexes = [models.Index(fields=["follower", "-created_at"], name="social_follow_follower_idx")]


class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block")]


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField(validators=[MaxLengthValidator(1000)])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["author", "-created_at"], name="social_post_author_created_idx")]


class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_post_like")]
        indexes = [models.Index(fields=["post", "-created_at"], name="social_like_post_created_idx")]


class SeenPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seen_posts")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="seen_by")
    seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "post"], name="unique_seen_post")]
        indexes = [models.Index(fields=["user", "-seen_at"], name="social_seen_user_seen_idx")]


class Report(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["reporter", "post"], name="unique_report")]


class PrivateMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_private_messages")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_private_messages")
    ciphertext = models.TextField()
    iv = models.CharField(max_length=32)
    protocol_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["sender", "recipient", "created_at"], name="social_pm_send_rec_idx"),
            models.Index(fields=["recipient", "sender", "created_at"], name="social_pm_rec_send_idx"),
        ]


class ConversationState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_states")
    contact = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_state_contacts")
    last_activity_at = models.DateTimeField(db_index=True)
    last_read_message_id = models.PositiveBigIntegerField(default=0)
    unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "contact"], name="unique_conversation_state"),
            models.CheckConstraint(condition=~models.Q(user=models.F("contact")), name="conversation_participants_differ"),
        ]
        indexes = [models.Index(fields=["user", "-last_activity_at"], name="social_conv_user_activity_idx")]
