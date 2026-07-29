from django.db.models import Sum
from .models import Block, ConversationState


def unread_messages(request):
    if not request.user.is_authenticated:
        return {"unread_message_count": 0}
    blocked = set(Block.objects.filter(blocker=request.user).values_list("blocked_id", flat=True))
    blocked.update(Block.objects.filter(blocked=request.user).values_list("blocker_id", flat=True))
    total = ConversationState.objects.filter(user=request.user).exclude(contact_id__in=blocked).aggregate(
        total=Sum("unread_count")
    )["total"] or 0
    return {"unread_message_count": total}
