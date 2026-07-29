from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_conversation_states(apps, schema_editor):
    PrivateMessage = apps.get_model("social", "PrivateMessage")
    ConversationState = apps.get_model("social", "ConversationState")
    states = {}
    for message in PrivateMessage.objects.order_by("id").iterator():
        sender_key = (message.sender_id, message.recipient_id)
        recipient_key = (message.recipient_id, message.sender_id)
        sender_state = states.setdefault(sender_key, {
            "last_activity_at": message.created_at, "last_read_message_id": 0, "unread_count": 0,
        })
        recipient_state = states.setdefault(recipient_key, {
            "last_activity_at": message.created_at, "last_read_message_id": 0, "unread_count": 0,
        })
        sender_state["last_activity_at"] = message.created_at
        recipient_state["last_activity_at"] = message.created_at
        recipient_state["unread_count"] += 1
    ConversationState.objects.bulk_create([
        ConversationState(user_id=user_id, contact_id=contact_id, **values)
        for (user_id, contact_id), values in states.items()
    ])


class Migration(migrations.Migration):
    dependencies = [("social", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ConversationState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_activity_at", models.DateTimeField(db_index=True)),
                ("last_read_message_id", models.PositiveBigIntegerField(default=0)),
                ("unread_count", models.PositiveIntegerField(default=0)),
                ("contact", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversation_state_contacts", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversation_states", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PostLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="social.post")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="post_likes", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SeenPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seen_at", models.DateTimeField(auto_now=True)),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seen_by", to="social.post")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seen_posts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(populate_conversation_states, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="conversationstate", constraint=models.UniqueConstraint(fields=("user", "contact"), name="unique_conversation_state")),
        migrations.AddConstraint(model_name="conversationstate", constraint=models.CheckConstraint(condition=~models.Q(user=models.F("contact")), name="conversation_participants_differ")),
        migrations.AddConstraint(model_name="postlike", constraint=models.UniqueConstraint(fields=("user", "post"), name="unique_post_like")),
        migrations.AddConstraint(model_name="seenpost", constraint=models.UniqueConstraint(fields=("user", "post"), name="unique_seen_post")),
        migrations.AddIndex(model_name="conversationstate", index=models.Index(fields=["user", "-last_activity_at"], name="social_conv_user_activity_idx")),
        migrations.AddIndex(model_name="postlike", index=models.Index(fields=["post", "-created_at"], name="social_like_post_created_idx")),
        migrations.AddIndex(model_name="seenpost", index=models.Index(fields=["user", "-seen_at"], name="social_seen_user_seen_idx")),
    ]
