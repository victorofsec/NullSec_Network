"use strict";

document.querySelectorAll(".confirm-delete").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("Delete this public post permanently?")) event.preventDefault();
  });
});

document.querySelectorAll(".confirm-block").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const button = form.querySelector("button");
    if (button && button.textContent.trim() === "Block" && !window.confirm("Block this user and remove mutual follows?")) {
      event.preventDefault();
    }
  });
});

const messageBadge = document.getElementById("message-badge");
const notificationsUrl = document.body.dataset.notificationsUrl;
const conversationList = document.querySelector("[data-conversation-list='true']");
let previousUnreadCount = messageBadge ? Number.parseInt(messageBadge.textContent, 10) || 0 : 0;

async function refreshNotificationBadge() {
  if (!messageBadge || !notificationsUrl || document.visibilityState === "hidden") return;
  try {
    const response = await fetch(notificationsUrl, { credentials: "same-origin", headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const data = await response.json();
    const count = Number.isInteger(data.unread_messages) && data.unread_messages >= 0 ? data.unread_messages : 0;
    messageBadge.textContent = String(count);
    messageBadge.setAttribute("aria-label", `${count} unread messages`);
    messageBadge.classList.toggle("hidden", count === 0);
    if (conversationList && count !== previousUnreadCount) window.location.reload();
    previousUnreadCount = count;
  } catch (_error) {
    // A temporary polling failure must not interrupt the rest of the interface.
  }
}

if (messageBadge && notificationsUrl) {
  window.setInterval(refreshNotificationBadge, 5000);
  document.addEventListener("visibilitychange", refreshNotificationBadge);
}
