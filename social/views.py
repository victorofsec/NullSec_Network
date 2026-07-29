import base64
import binascii
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import PostForm, ProfileForm, ReportForm, SignUpForm
from .models import Block, ConversationState, Follow, Post, PostLike, PrivateMessage, Report, SeenPost


def home(request):
    if request.user.is_authenticated:
        return redirect("conversations")
    return render(request, "social/home.html")


def static_page(request, page):
    if page not in {"about", "privacy", "security"}:
        raise Http404
    return render(request, f"social/{page}.html")


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("feed")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("profile_edit")
    return render(request, "registration/signup.html", {"form": form})


def _blocked_user_ids(user):
    outgoing = Block.objects.filter(blocker=user).values_list("blocked_id", flat=True)
    incoming = Block.objects.filter(blocked=user).values_list("blocker_id", flat=True)
    return set(outgoing).union(incoming)


def _session_rate_limited(request, name, limit, seconds=60):
    now = timezone.now().timestamp()
    key = f"rate:{name}"
    entries = [value for value in request.session.get(key, []) if value > now - seconds]
    limited = len(entries) >= limit
    if not limited:
        entries.append(now)
    request.session[key] = entries
    request.session.modified = True
    return limited


def _decorate_posts(queryset, user, ranked=False):
    queryset = queryset.select_related("author", "author__profile").annotate(
        like_count=Count("likes", distinct=True),
        is_liked=Exists(PostLike.objects.filter(user=user, post_id=OuterRef("pk"))),
    )
    if ranked:
        return queryset.order_by("-like_count", "-created_at", "-id")
    return queryset.order_by("-created_at", "-id")


def _get_accessible_post(user, post_id):
    post = get_object_or_404(Post.objects.select_related("author"), id=post_id)
    if Block.objects.filter(
        Q(blocker=user, blocked=post.author) | Q(blocker=post.author, blocked=user)
    ).exists():
        raise Http404
    return post


def _return_url(request, fallback="feed"):
    candidate = request.POST.get("next", "")
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return candidate
    return reverse(fallback)


@login_required
@require_http_methods(["GET", "POST"])
def feed(request):
    if request.method == "POST":
        if Post.objects.filter(author=request.user, created_at__gte=timezone.now() - timedelta(minutes=1)).count() >= 5:
            messages.error(request, "Posting limit reached. Please wait one minute.")
            return redirect("feed")
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("feed")
    else:
        form = PostForm()
    blocked = _blocked_user_ids(request.user)
    followed = Follow.objects.filter(follower=request.user).values_list("followed_id", flat=True)
    posts = Post.objects.select_related("author", "author__profile").filter(
        Q(author=request.user) | Q(author_id__in=followed)
    ).exclude(author_id__in=blocked).exclude(seen_by__user=request.user)
    posts = _decorate_posts(posts, request.user, ranked=True)
    page = Paginator(posts, 20).get_page(request.GET.get("page"))
    return render(request, "social/feed.html", {"form": form, "page": page})


@login_required
@require_GET
def explore(request):
    blocked = _blocked_user_ids(request.user)
    posts = Post.objects.exclude(author_id__in=blocked).exclude(seen_by__user=request.user)
    posts = _decorate_posts(posts, request.user, ranked=True)
    page = Paginator(posts, 20).get_page(request.GET.get("page"))
    return render(request, "social/explore.html", {"page": page})


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile", username=request.user.username)
    return render(request, "social/profile_edit.html", {"form": form})


@login_required
@require_GET
def profile(request, username):
    person = get_object_or_404(User.objects.select_related("profile"), username=username)
    blocked_by_person = Block.objects.filter(blocker=person, blocked=request.user).exists()
    if blocked_by_person:
        raise Http404
    posts = Paginator(_decorate_posts(person.posts.all(), request.user), 20).get_page(request.GET.get("page"))
    context = {
        "person": person,
        "page": posts,
        "is_following": Follow.objects.filter(follower=request.user, followed=person).exists(),
        "is_blocked": Block.objects.filter(blocker=request.user, blocked=person).exists(),
    }
    return render(request, "social/profile.html", context)


@login_required
@require_GET
def user_search(request):
    query = request.GET.get("q", "").strip()[:50]
    users = User.objects.none()
    limited = False
    if query:
        limited = _session_rate_limited(request, "search", 20)
        if not limited:
            blocked = _blocked_user_ids(request.user)
            users = User.objects.select_related("profile").filter(
                Q(username__icontains=query) | Q(profile__display_name__icontains=query)
            ).exclude(id__in=blocked).order_by("username")[:50]
    return render(request, "social/search.html", {"query": query, "users": users, "limited": limited})


@login_required
@require_POST
def follow_toggle(request, username):
    person = get_object_or_404(User, username=username)
    if _session_rate_limited(request, "follows", 60):
        messages.error(request, "Follow limit reached. Please wait one minute.")
        return redirect("profile", username=username)
    if person == request.user or Block.objects.filter(
        Q(blocker=request.user, blocked=person) | Q(blocker=person, blocked=request.user)
    ).exists():
        return redirect("profile", username=username)
    link, created = Follow.objects.get_or_create(follower=request.user, followed=person)
    if not created:
        link.delete()
    return redirect("profile", username=username)


@login_required
@require_POST
def block_toggle(request, username):
    person = get_object_or_404(User, username=username)
    if _session_rate_limited(request, "blocks", 30):
        messages.error(request, "Block-action limit reached. Please wait one minute.")
        return redirect("profile", username=username)
    if person == request.user:
        return redirect("profile", username=username)
    block, created = Block.objects.get_or_create(blocker=request.user, blocked=person)
    if created:
        Follow.objects.filter(Q(follower=request.user, followed=person) | Q(follower=person, followed=request.user)).delete()
        ConversationState.objects.filter(
            Q(user=request.user, contact=person) | Q(user=person, contact=request.user)
        ).update(unread_count=0)
    else:
        block.delete()
    return redirect("profile", username=username)


@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author_id != request.user.id:
        return JsonResponse({"error": "Forbidden"}, status=403)
    post.delete()
    messages.success(request, "Post deleted.")
    return redirect("feed")


@login_required
@require_POST
def like_toggle(request, post_id):
    post = _get_accessible_post(request.user, post_id)
    if post.author_id == request.user.id:
        messages.error(request, "You cannot like your own post.")
        return redirect(_return_url(request))
    if _session_rate_limited(request, "likes", 60):
        messages.error(request, "Like limit reached. Please wait one minute.")
        return redirect(_return_url(request))
    like, created = PostLike.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return redirect(_return_url(request))


@login_required
@require_POST
def seen_toggle(request, post_id):
    post = _get_accessible_post(request.user, post_id)
    if _session_rate_limited(request, "seen", 120):
        messages.error(request, "Seen-history limit reached. Please wait one minute.")
        return redirect(_return_url(request, "seen_history"))
    if request.POST.get("undo") == "1":
        SeenPost.objects.filter(user=request.user, post=post).delete()
    else:
        SeenPost.objects.update_or_create(user=request.user, post=post)
    return redirect(_return_url(request, "seen_history" if request.POST.get("undo") == "1" else "feed"))


@login_required
@require_GET
def seen_history(request):
    blocked = _blocked_user_ids(request.user)
    seen_at = SeenPost.objects.filter(user=request.user, post_id=OuterRef("pk")).values("seen_at")[:1]
    posts = Post.objects.filter(seen_by__user=request.user).exclude(author_id__in=blocked).annotate(
        seen_at=Subquery(seen_at)
    )
    posts = _decorate_posts(posts, request.user).order_by("-seen_at", "-id")
    page = Paginator(posts, 20).get_page(request.GET.get("page"))
    return render(request, "social/seen_history.html", {"page": page, "in_seen_history": True})


@login_required
@require_http_methods(["GET", "POST"])
def report_post(request, post_id):
    post = _get_accessible_post(request.user, post_id)
    if post.author_id == request.user.id:
        return redirect("feed")
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if _session_rate_limited(request, "reports", 10, seconds=3600):
            messages.error(request, "Report limit reached. Please wait before reporting again.")
            return redirect("explore")
        Report.objects.update_or_create(
            reporter=request.user, post=post, defaults={"reason": form.cleaned_data["reason"]}
        )
        messages.success(request, "Report recorded for review by the instance administrator.")
        return redirect("explore")
    return render(request, "social/report.html", {"form": form, "post": post})


@login_required
@require_GET
def conversations(request):
    blocked = _blocked_user_ids(request.user)
    states = ConversationState.objects.filter(user=request.user).select_related("contact", "contact__profile").exclude(
        contact_id__in=blocked
    ).order_by("-last_activity_at", "-id")
    page = Paginator(states, 30).get_page(request.GET.get("page"))
    return render(request, "social/conversations.html", {"page": page})


@login_required
@require_GET
def notifications_api(request):
    blocked = _blocked_user_ids(request.user)
    total = ConversationState.objects.filter(user=request.user).exclude(contact_id__in=blocked).aggregate(
        total=Sum("unread_count")
    )["total"] or 0
    return JsonResponse({"unread_messages": total})


@login_required
@ensure_csrf_cookie
@require_GET
def conversation(request, username):
    contact = get_object_or_404(User.objects.select_related("profile"), username=username)
    if contact == request.user or Block.objects.filter(
        Q(blocker=request.user, blocked=contact) | Q(blocker=contact, blocked=request.user)
    ).exists():
        raise Http404
    return render(request, "social/conversation.html", {"contact": contact})


def _valid_public_jwk(value):
    if not isinstance(value, dict) or set(value) != {"key_ops", "ext", "kty", "x", "y", "crv"}:
        return False
    structurally_valid = (
        value.get("kty") == "EC" and value.get("crv") == "P-256" and value.get("ext") is True
        and value.get("key_ops") == [] and all(isinstance(value.get(k), str) and 40 <= len(value[k]) <= 50 for k in ("x", "y"))
    )
    if not structurally_valid:
        return False
    try:
        return all(len(base64.urlsafe_b64decode(value[k] + "=" * (-len(value[k]) % 4))) == 32 for k in ("x", "y"))
    except (ValueError, binascii.Error):
        return False


@login_required
@require_http_methods(["GET", "POST"])
def key_api(request):
    if request.method == "GET":
        username = request.GET.get("username", request.user.username)
        person = get_object_or_404(User.objects.select_related("profile"), username=username)
        if person != request.user and Block.objects.filter(
            Q(blocker=request.user, blocked=person) | Q(blocker=person, blocked=request.user)
        ).exists():
            return JsonResponse({"error": "Forbidden"}, status=403)
        if not person.profile.public_key_jwk:
            return JsonResponse({"error": "No public key"}, status=404)
        return JsonResponse({"username": person.username, "public_key": json.loads(person.profile.public_key_jwk)})
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if not isinstance(data, dict) or set(data) != {"public_key"}:
        return JsonResponse({"error": "Unexpected fields"}, status=400)
    key = data.get("public_key")
    if not _valid_public_jwk(key):
        return JsonResponse({"error": "Invalid P-256 public JWK"}, status=400)
    encoded = json.dumps(key, sort_keys=True, separators=(",", ":"))
    profile = request.user.profile
    changed = profile.public_key_jwk != encoded
    if changed:
        profile.public_key_jwk = encoded
        profile.key_updated_at = timezone.now()
        profile.save(update_fields=["public_key_jwk", "key_updated_at"])
    return JsonResponse({"ok": True, "changed": changed})


@login_required
@require_http_methods(["GET", "POST"])
def message_api(request, username):
    contact = get_object_or_404(User, username=username)
    if contact == request.user or Block.objects.filter(
        Q(blocker=request.user, blocked=contact) | Q(blocker=contact, blocked=request.user)
    ).exists():
        return JsonResponse({"error": "Forbidden"}, status=403)
    pair = Q(sender=request.user, recipient=contact) | Q(sender=contact, recipient=request.user)
    if request.method == "GET":
        try:
            after = max(0, int(request.GET.get("after", "0")))
        except ValueError:
            return JsonResponse({"error": "Invalid cursor"}, status=400)
        rows = PrivateMessage.objects.filter(pair, id__gt=after).select_related("sender").order_by("id")[:100]
        contact_read_cursor = ConversationState.objects.filter(
            user=contact, contact=request.user
        ).values_list("last_read_message_id", flat=True).first() or 0
        return JsonResponse({"messages": [{
            "id": row.id, "sender": row.sender.username, "recipient": row.recipient.username,
            "ciphertext": row.ciphertext, "iv": row.iv, "protocol_version": row.protocol_version,
            "created_at": row.created_at.isoformat(),
        } for row in rows], "contact_last_read_message_id": contact_read_cursor})
    if PrivateMessage.objects.filter(sender=request.user, created_at__gte=timezone.now() - timedelta(minutes=1)).count() >= 30:
        return JsonResponse({"error": "Message rate limit reached"}, status=429)
    if len(request.body) > 20000:
        return JsonResponse({"error": "Payload too large"}, status=413)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if not isinstance(data, dict) or set(data) != {"ciphertext", "iv", "protocol_version"}:
        return JsonResponse({"error": "Unexpected fields"}, status=400)
    ciphertext, iv, version = data.get("ciphertext"), data.get("iv"), data.get("protocol_version")
    if not isinstance(ciphertext, str) or not 24 <= len(ciphertext) <= 16000:
        return JsonResponse({"error": "Invalid ciphertext"}, status=400)
    if not isinstance(iv, str) or version != 1:
        return JsonResponse({"error": "Invalid protocol fields"}, status=400)
    try:
        decoded_ciphertext = base64.b64decode(ciphertext, validate=True)
        decoded_iv = base64.b64decode(iv, validate=True)
    except (ValueError, binascii.Error):
        return JsonResponse({"error": "Invalid Base64"}, status=400)
    if len(decoded_ciphertext) < 16 or len(decoded_ciphertext) > 12000 or len(decoded_iv) != 12:
        return JsonResponse({"error": "Invalid encrypted payload size"}, status=400)
    with transaction.atomic():
        row = PrivateMessage.objects.create(
            sender=request.user, recipient=contact, ciphertext=ciphertext, iv=iv, protocol_version=1
        )
        sender_state, _ = ConversationState.objects.get_or_create(
            user=request.user, contact=contact,
            defaults={"last_activity_at": row.created_at},
        )
        recipient_state, _ = ConversationState.objects.get_or_create(
            user=contact, contact=request.user,
            defaults={"last_activity_at": row.created_at},
        )
        ConversationState.objects.filter(id=sender_state.id).update(last_activity_at=row.created_at)
        ConversationState.objects.filter(id=recipient_state.id).update(
            last_activity_at=row.created_at, unread_count=F("unread_count") + 1
        )
    return JsonResponse({"ok": True, "id": row.id, "created_at": row.created_at.isoformat()}, status=201)


@login_required
@require_POST
def mark_conversation_read(request, username):
    contact = get_object_or_404(User, username=username)
    if contact == request.user or Block.objects.filter(
        Q(blocker=request.user, blocked=contact) | Q(blocker=contact, blocked=request.user)
    ).exists():
        return JsonResponse({"error": "Forbidden"}, status=403)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    if not isinstance(data, dict) or set(data) != {"last_message_id"} or not isinstance(data["last_message_id"], int):
        return JsonResponse({"error": "Invalid read cursor"}, status=400)
    cursor = data["last_message_id"]
    if cursor <= 0 or not PrivateMessage.objects.filter(
        id=cursor, sender=contact, recipient=request.user
    ).exists():
        return JsonResponse({"error": "Read cursor does not identify a received message"}, status=400)
    with transaction.atomic():
        state, _ = ConversationState.objects.get_or_create(
            user=request.user, contact=contact, defaults={"last_activity_at": timezone.now()}
        )
        new_cursor = max(state.last_read_message_id, cursor)
        remaining = PrivateMessage.objects.filter(
            sender=contact, recipient=request.user, id__gt=new_cursor
        ).count()
        ConversationState.objects.filter(id=state.id).update(
            last_read_message_id=new_cursor, unread_count=remaining
        )
    return JsonResponse({"ok": True, "unread_messages": remaining})
