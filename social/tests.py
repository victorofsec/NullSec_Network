import base64
import json
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Block, ConversationState, Follow, Post, PostLike, PrivateMessage, Report, SeenPost


VALID_JWK = {
    "key_ops": [], "ext": True, "kty": "EC",
    "x": base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("="),
    "y": base64.urlsafe_b64encode(b"y" * 32).decode().rstrip("="),
    "crv": "P-256",
}


class SocialTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="correct-horse-battery-staple")
        self.bob = User.objects.create_user("bob", password="correct-horse-battery-staple")
        self.client.force_login(self.alice)

    def test_profile_is_created_with_user(self):
        self.assertEqual(self.alice.profile.display_name, "alice")

    def test_authenticated_home_redirects_to_messages(self):
        self.assertRedirects(self.client.get(reverse("home")), reverse("conversations"))

    def test_admin_route_is_available_and_requires_staff_access(self):
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/")

    def test_feed_requires_login_and_post_is_escaped(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("feed")), f"{reverse('login')}?next={reverse('feed')}")
        self.client.force_login(self.alice)
        response = self.client.post(reverse("feed"), {"body": "<script>alert(1)</script>"}, follow=True)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_follow_and_block_rules(self):
        self.client.post(reverse("follow_toggle", args=["bob"]))
        self.assertTrue(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())
        self.client.post(reverse("block_toggle", args=["bob"]))
        self.assertTrue(Block.objects.filter(blocker=self.alice, blocked=self.bob).exists())
        self.assertFalse(Follow.objects.filter(follower=self.alice, followed=self.bob).exists())
        self.assertEqual(self.client.get(reverse("conversation", args=["bob"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("key_api"), {"username": "bob"}).status_code, 403)

    def test_only_author_can_delete_post(self):
        post = Post.objects.create(author=self.bob, body="Bob's post")
        response = self.client.post(reverse("delete_post", args=[post.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(id=post.id).exists())
        own = Post.objects.create(author=self.alice, body="Alice's post")
        self.client.post(reverse("delete_post", args=[own.id]))
        self.assertFalse(Post.objects.filter(id=own.id).exists())

    def test_likes_are_unique_toggleable_and_self_likes_are_blocked(self):
        post = Post.objects.create(author=self.bob, body="Useful report")
        url = reverse("like_toggle", args=[post.id])
        self.client.post(url, {"next": reverse("explore")})
        self.assertTrue(PostLike.objects.filter(user=self.alice, post=post).exists())
        self.client.post(url, {"next": reverse("explore")})
        self.assertFalse(PostLike.objects.filter(user=self.alice, post=post).exists())
        own = Post.objects.create(author=self.alice, body="Own report")
        self.client.post(reverse("like_toggle", args=[own.id]))
        self.assertFalse(PostLike.objects.filter(user=self.alice, post=own).exists())

    def test_feed_is_ranked_by_like_count_then_recency(self):
        charlie = User.objects.create_user("charlie", password="correct-horse-battery-staple")
        popular = Post.objects.create(author=self.bob, body="Popular")
        recent = Post.objects.create(author=charlie, body="Recent")
        Follow.objects.bulk_create([
            Follow(follower=self.alice, followed=self.bob),
            Follow(follower=self.alice, followed=charlie),
        ])
        PostLike.objects.create(user=charlie, post=popular)
        response = self.client.get(reverse("feed"))
        ids = [post.id for post in response.context["page"].object_list]
        self.assertEqual(ids[:2], [popular.id, recent.id])

    def test_seen_moves_post_to_history_and_restore_returns_it(self):
        post = Post.objects.create(author=self.bob, body="Archive me")
        Follow.objects.create(follower=self.alice, followed=self.bob)
        self.client.post(reverse("seen_toggle", args=[post.id]), {"next": reverse("feed")})
        self.assertTrue(SeenPost.objects.filter(user=self.alice, post=post).exists())
        self.assertNotContains(self.client.get(reverse("feed")), "Archive me")
        self.assertContains(self.client.get(reverse("seen_history")), "Archive me")
        self.client.post(reverse("seen_toggle", args=[post.id]), {"undo": "1", "next": reverse("seen_history")})
        self.assertFalse(SeenPost.objects.filter(user=self.alice, post=post).exists())
        self.assertContains(self.client.get(reverse("feed")), "Archive me")

    def test_reporting_is_unique_and_cannot_report_own_post(self):
        post = Post.objects.create(author=self.bob, body="questionable")
        self.client.post(reverse("report_post", args=[post.id]), {"reason": "first"})
        self.client.post(reverse("report_post", args=[post.id]), {"reason": "updated"})
        self.assertEqual(Report.objects.filter(reporter=self.alice, post=post).count(), 1)
        self.assertEqual(Report.objects.get(reporter=self.alice, post=post).reason, "updated")
        own = Post.objects.create(author=self.alice, body="own")
        self.assertRedirects(self.client.get(reverse("report_post", args=[own.id])), reverse("feed"))

    def test_public_key_api_accepts_only_p256_public_jwk(self):
        response = self.client.post(reverse("key_api"), json.dumps({"public_key": VALID_JWK}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        stored = json.loads(self.alice.profile.__class__.objects.get(user=self.alice).public_key_jwk)
        self.assertEqual(stored, VALID_JWK)
        invalid = dict(VALID_JWK, crv="P-384")
        self.assertEqual(self.client.post(reverse("key_api"), json.dumps({"public_key": invalid}), content_type="application/json").status_code, 400)

    def test_message_model_has_no_plaintext_field(self):
        fields = {field.name for field in PrivateMessage._meta.fields}
        self.assertEqual(fields, {"id", "sender", "recipient", "ciphertext", "iv", "protocol_version", "created_at"})
        self.assertNotIn("body", fields)
        self.assertNotIn("plaintext", fields)

    def test_encrypted_message_round_trip_and_pair_authorization(self):
        payload = {
            "ciphertext": base64.b64encode(b"c" * 32).decode(),
            "iv": base64.b64encode(b"i" * 12).decode(),
            "protocol_version": 1,
        }
        response = self.client.post(reverse("message_api", args=["bob"]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        row = PrivateMessage.objects.get()
        self.assertEqual(row.sender, self.alice)
        self.assertEqual(row.recipient, self.bob)
        data = self.client.get(reverse("message_api", args=["bob"])).json()["messages"][0]
        self.assertNotIn("plaintext", data)
        charlie = User.objects.create_user("charlie", password="correct-horse-battery-staple")
        self.client.force_login(charlie)
        self.assertEqual(self.client.get(reverse("message_api", args=["bob"])).json()["messages"], [])

    def test_unread_notification_and_validated_read_cursor(self):
        payload = {
            "ciphertext": base64.b64encode(b"c" * 32).decode(),
            "iv": base64.b64encode(b"i" * 12).decode(),
            "protocol_version": 1,
        }
        self.client.force_login(self.bob)
        sent = self.client.post(
            reverse("message_api", args=["alice"]), json.dumps(payload), content_type="application/json"
        ).json()
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("notifications_api")).json()["unread_messages"], 1)
        state = ConversationState.objects.get(user=self.alice, contact=self.bob)
        self.assertEqual(state.unread_count, 1)
        invalid = self.client.post(
            reverse("mark_conversation_read", args=["bob"]),
            json.dumps({"last_message_id": sent["id"] + 100}), content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        response = self.client.post(
            reverse("mark_conversation_read", args=["bob"]),
            json.dumps({"last_message_id": sent["id"]}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("notifications_api")).json()["unread_messages"], 0)
        self.client.force_login(self.bob)
        receipt = self.client.get(reverse("message_api", args=["alice"])).json()
        self.assertEqual(receipt["contact_last_read_message_id"], sent["id"])

    def test_conversations_are_ordered_by_latest_activity(self):
        charlie = User.objects.create_user("charlie", password="correct-horse-battery-staple")
        older = timezone.now() - timedelta(minutes=2)
        newer = timezone.now()
        ConversationState.objects.create(user=self.alice, contact=self.bob, last_activity_at=older)
        ConversationState.objects.create(user=self.alice, contact=charlie, last_activity_at=newer)
        response = self.client.get(reverse("conversations"))
        contacts = [state.contact.username for state in response.context["page"].object_list]
        self.assertEqual(contacts, ["charlie", "bob"])

    def test_message_api_rejects_plaintext_or_unknown_fields(self):
        payload = {
            "ciphertext": base64.b64encode(b"c" * 32).decode(),
            "iv": base64.b64encode(b"i" * 12).decode(),
            "protocol_version": 1,
            "plaintext": "this must never be accepted",
        }
        response = self.client.post(reverse("message_api", args=["bob"]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PrivateMessage.objects.exists())

    def test_invalid_encrypted_payload_is_rejected(self):
        payload = {"ciphertext": "not base64!", "iv": "wrong", "protocol_version": 1}
        response = self.client.post(reverse("message_api", args=["bob"]), json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PrivateMessage.objects.exists())

    def test_message_rate_limit(self):
        valid = {"ciphertext": base64.b64encode(b"c" * 20).decode(), "iv": base64.b64encode(b"i" * 12).decode(), "protocol_version": 1}
        for _ in range(30):
            self.assertEqual(self.client.post(reverse("message_api", args=["bob"]), json.dumps(valid), content_type="application/json").status_code, 201)
        self.assertEqual(self.client.post(reverse("message_api", args=["bob"]), json.dumps(valid), content_type="application/json").status_code, 429)

    def test_security_headers(self):
        response = self.client.get(reverse("feed"))
        self.assertIn("default-src 'self'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("camera=()", response["Permissions-Policy"])
        self.assertIn("img-src 'self'", response["Content-Security-Policy"])

    def test_static_javascript_never_uses_inner_html(self):
        static_dir = Path(__file__).resolve().parent.parent / "static" / "js"
        source = "\n".join(path.read_text(encoding="utf-8") for path in static_dir.glob("*.js"))
        self.assertNotIn("innerHTML", source)

    def test_local_logo_exists(self):
        logo = Path(__file__).resolve().parent.parent / "static" / "img" / "logo.png"
        self.assertTrue(logo.is_file())

    def test_authenticated_pages_bootstrap_nonextractable_identity(self):
        response = self.client.get(reverse("feed"))
        self.assertContains(response, "js/identity.js")
        identity_source = (Path(__file__).resolve().parent.parent / "static" / "js" / "identity.js").read_text(encoding="utf-8")
        self.assertIn('namedCurve: "P-256" }, false, ["deriveBits"]', identity_source)
        self.assertNotIn('exportKey("jwk", pair.privateKey)', identity_source)
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("home")), "js/identity.js")


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
class ProductionPageTests(TestCase):
    def test_public_pages_render_without_external_assets(self):
        for name in ("home", "about", "privacy", "security"):
            response = self.client.get(reverse(name), secure=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "https://cdn")
