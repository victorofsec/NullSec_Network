from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("feed/", views.feed, name="feed"),
    path("explore/", views.explore, name="explore"),
    path("seen/", views.seen_history, name="seen_history"),
    path("search/", views.user_search, name="user_search"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/follow/", views.follow_toggle, name="follow_toggle"),
    path("u/<str:username>/block/", views.block_toggle, name="block_toggle"),
    path("posts/<int:post_id>/delete/", views.delete_post, name="delete_post"),
    path("posts/<int:post_id>/report/", views.report_post, name="report_post"),
    path("posts/<int:post_id>/like/", views.like_toggle, name="like_toggle"),
    path("posts/<int:post_id>/seen/", views.seen_toggle, name="seen_toggle"),
    path("messages/", views.conversations, name="conversations"),
    path("messages/<str:username>/", views.conversation, name="conversation"),
    path("api/keys/", views.key_api, name="key_api"),
    path("api/messages/<str:username>/", views.message_api, name="message_api"),
    path("api/messages/<str:username>/read/", views.mark_conversation_read, name="mark_conversation_read"),
    path("api/notifications/", views.notifications_api, name="notifications_api"),
    path("about/", views.static_page, {"page": "about"}, name="about"),
    path("privacy/", views.static_page, {"page": "privacy"}, name="privacy"),
    path("security/", views.static_page, {"page": "security"}, name="security"),
]
