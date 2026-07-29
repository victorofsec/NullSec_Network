from django.contrib import admin
from .models import Block, ConversationState, Follow, Post, PostLike, Profile, Report, SeenPost

admin.site.register(Profile)
admin.site.register(Follow)
admin.site.register(Block)
admin.site.register(Post)
admin.site.register(Report)
admin.site.register(PostLike)
admin.site.register(SeenPost)
admin.site.register(ConversationState)
