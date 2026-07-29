# Generated for Django 5.2
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(name="Post", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("body", models.TextField(validators=[django.core.validators.MaxLengthValidator(1000)])),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posts", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="Profile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("display_name", models.CharField(blank=True, max_length=50)),
            ("bio", models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(300)])),
            ("public_key_jwk", models.TextField(blank=True)),
            ("key_updated_at", models.DateTimeField(blank=True, null=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="PrivateMessage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("ciphertext", models.TextField()),
            ("iv", models.CharField(max_length=32)),
            ("protocol_version", models.PositiveSmallIntegerField(default=1)),
            ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_private_messages", to=settings.AUTH_USER_MODEL)),
            ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_private_messages", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["created_at"]}),
        migrations.CreateModel(name="Follow", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("followed", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="follower_links", to=settings.AUTH_USER_MODEL)),
            ("follower", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="following_links", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Block", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("blocked", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_received", to=settings.AUTH_USER_MODEL)),
            ("blocker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_made", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Report", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("reason", models.CharField(max_length=200)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="social.post")),
            ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="follow", constraint=models.UniqueConstraint(fields=("follower", "followed"), name="unique_follow")),
        migrations.AddConstraint(model_name="block", constraint=models.UniqueConstraint(fields=("blocker", "blocked"), name="unique_block")),
        migrations.AddConstraint(model_name="report", constraint=models.UniqueConstraint(fields=("reporter", "post"), name="unique_report")),
        migrations.AddIndex(model_name="post", index=models.Index(fields=["author", "-created_at"], name="social_post_author_created_idx")),
        migrations.AddIndex(model_name="follow", index=models.Index(fields=["follower", "-created_at"], name="social_follow_follower_idx")),
        migrations.AddIndex(model_name="privatemessage", index=models.Index(fields=["sender", "recipient", "created_at"], name="social_pm_send_rec_idx")),
        migrations.AddIndex(model_name="privatemessage", index=models.Index(fields=["recipient", "sender", "created_at"], name="social_pm_rec_send_idx")),
    ]
