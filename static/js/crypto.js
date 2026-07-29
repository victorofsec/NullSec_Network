"use strict";

(() => {
  const root = document.getElementById("conversation");
  if (!root) return;

  const ownUsername = root.dataset.username;
  const contactUsername = root.dataset.contact;
  const keyUrl = root.dataset.keyUrl;
  const messageUrl = root.dataset.messageUrl;
  const readUrl = root.dataset.readUrl;
  const status = document.getElementById("crypto-status");
  const warning = document.getElementById("key-warning");
  const ownFingerprint = document.getElementById("own-fingerprint");
  const contactFingerprint = document.getElementById("contact-fingerprint");
  const list = document.getElementById("message-list");
  const form = document.getElementById("message-form");
  const input = document.getElementById("message-input");
  const sendButton = document.getElementById("send-button");
  const acceptKey = document.getElementById("accept-key");
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let localIdentity;
  let peerPublicKey;
  let peerFingerprint = "";
  let conversationKey;
  let cursor = 0;
  let polling = false;

  function cookie(name) {
    const entry = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${name}=`));
    return entry ? decodeURIComponent(entry.slice(name.length + 1)) : "";
  }

  function toBase64(bytes) {
    let binary = "";
    new Uint8Array(bytes).forEach((byte) => { binary += String.fromCharCode(byte); });
    return btoa(binary);
  }

  function fromBase64(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    let data;
    try { data = await response.json(); } catch (_error) { data = {}; }
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  async function fingerprint(publicKey) {
    const raw = await crypto.subtle.exportKey("raw", publicKey);
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", raw));
    return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("").match(/.{1,4}/g).join(" ");
  }

  async function importPublic(jwk) {
    return crypto.subtle.importKey("jwk", jwk, { name: "ECDH", namedCurve: "P-256" }, true, []);
  }

  async function deriveConversationKey(publicKey) {
    const shared = await crypto.subtle.deriveBits({ name: "ECDH", public: publicKey }, localIdentity.privateKey, 256);
    const hkdfKey = await crypto.subtle.importKey("raw", shared, "HKDF", false, ["deriveKey"]);
    const participants = [ownUsername, contactUsername].sort().join("|");
    const salt = await crypto.subtle.digest("SHA-256", encoder.encode(`NullSecNetwork-v1|${participants}`));
    return crypto.subtle.deriveKey(
      { name: "HKDF", hash: "SHA-256", salt, info: encoder.encode("private-message") },
      hkdfKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  function aad(sender, recipient) {
    return encoder.encode(`NullSecNetwork-v1|${sender}|${recipient}`);
  }

  async function showOwnFingerprint() {
    const ownPublic = await importPublic(localIdentity.publicJwk);
    ownFingerprint.textContent = await fingerprint(ownPublic);
  }

  async function refreshPeerKey(initial = false) {
    const data = await requestJson(`${keyUrl}?username=${encodeURIComponent(contactUsername)}`);
    const imported = await importPublic(data.public_key);
    const current = await fingerprint(imported);
    const storageKey = `nullsec-fingerprint:${ownUsername}:${contactUsername}`;
    const saved = localStorage.getItem(storageKey);
    if (saved && saved !== current) {
      warning.classList.remove("hidden");
      input.disabled = true;
      sendButton.disabled = true;
    }
    if (!saved || (initial && saved === current)) localStorage.setItem(storageKey, current);
    if (peerFingerprint !== current) {
      peerPublicKey = imported;
      peerFingerprint = current;
      contactFingerprint.textContent = current;
      conversationKey = await deriveConversationKey(peerPublicKey);
    }
  }

  function appendMessage(row, plaintext, failed = false) {
    const article = document.createElement("article");
    article.className = `message ${row.sender === ownUsername ? "sent" : "received"}${failed ? " failed" : ""}`;
    article.dataset.messageId = String(row.id);
    article.dataset.sender = row.sender;
    const body = document.createElement("p");
    body.textContent = plaintext;
    const meta = document.createElement("small");
    const date = new Date(row.created_at);
    meta.textContent = `${row.sender} · ${Number.isNaN(date.valueOf()) ? "unknown date" : date.toLocaleString()}`;
    article.append(body, meta);
    if (row.sender === ownUsername && !failed) {
      const seen = document.createElement("small");
      seen.className = "seen-status hidden";
      seen.textContent = "Seen";
      article.appendChild(seen);
    }
    list.appendChild(article);
    list.scrollTop = list.scrollHeight;
  }

  function updateSeenMarkers(readCursor) {
    if (!Number.isInteger(readCursor) || readCursor <= 0) return;
    list.querySelectorAll(".message.sent[data-message-id]").forEach((message) => {
      const messageId = Number.parseInt(message.dataset.messageId, 10);
      const marker = message.querySelector(".seen-status");
      if (marker) marker.classList.toggle("hidden", messageId > readCursor);
    });
  }

  async function poll() {
    if (polling) return;
    polling = true;
    try {
      await refreshPeerKey();
      const data = await requestJson(`${messageUrl}?after=${cursor}`);
      let highestDecryptedIncoming = 0;
      for (const row of data.messages) {
        cursor = Math.max(cursor, row.id);
        try {
          const plaintext = await crypto.subtle.decrypt(
            { name: "AES-GCM", iv: fromBase64(row.iv), additionalData: aad(row.sender, row.recipient), tagLength: 128 },
            conversationKey,
            fromBase64(row.ciphertext)
          );
          appendMessage(row, decoder.decode(plaintext));
          if (row.sender === contactUsername) highestDecryptedIncoming = Math.max(highestDecryptedIncoming, row.id);
        } catch (_error) {
          appendMessage(row, "Unable to decrypt: the message may use a previous key or be damaged.", true);
        }
      }
      updateSeenMarkers(data.contact_last_read_message_id);
      if (highestDecryptedIncoming > 0) {
        try {
          await requestJson(readUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
            body: JSON.stringify({ last_message_id: highestDecryptedIncoming }),
          });
        } catch (_error) {
          status.textContent = "Messages decrypted, but the unread counter could not be synchronized.";
        }
      }
    } catch (error) {
      status.textContent = `Encryption unavailable: ${error.message}`;
    } finally {
      polling = false;
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const plaintext = input.value.trim();
    if (!plaintext || !conversationKey || !warning.classList.contains("hidden")) return;
    sendButton.disabled = true;
    try {
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const ciphertext = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv, additionalData: aad(ownUsername, contactUsername), tagLength: 128 },
        conversationKey,
        encoder.encode(plaintext)
      );
      await requestJson(messageUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
        body: JSON.stringify({ ciphertext: toBase64(ciphertext), iv: toBase64(iv), protocol_version: 1 }),
      });
      input.value = "";
      await poll();
    } catch (error) {
      status.textContent = `Message not sent: ${error.message}`;
    } finally {
      if (warning.classList.contains("hidden")) sendButton.disabled = false;
    }
  });

  acceptKey.addEventListener("click", () => {
    localStorage.setItem(`nullsec-fingerprint:${ownUsername}:${contactUsername}`, peerFingerprint);
    warning.classList.add("hidden");
    input.disabled = false;
    sendButton.disabled = false;
  });

  async function initialize() {
    if (!window.NullSecIdentity) throw new Error("The local identity module is unavailable.");
    localIdentity = await window.NullSecIdentity.ready;
    await showOwnFingerprint();
    try {
      await refreshPeerKey(true);
      if (warning.classList.contains("hidden")) {
        input.disabled = false;
        sendButton.disabled = false;
      }
      status.textContent = "Ready. Plaintext is encrypted locally before it leaves this browser.";
      await poll();
    } catch (error) {
      status.textContent = `Waiting for @${contactUsername} to create a browser key: ${error.message}`;
    }
    window.setInterval(async () => {
      if (conversationKey) {
        await poll();
        return;
      }
      try {
        await refreshPeerKey(true);
        if (warning.classList.contains("hidden")) {
          input.disabled = false;
          sendButton.disabled = false;
        }
        status.textContent = "Ready. Plaintext is encrypted locally before it leaves this browser.";
        await poll();
      } catch (error) {
        status.textContent = `Waiting for @${contactUsername} to create a browser key: ${error.message}`;
      }
    }, 5000);
  }

  initialize().catch((error) => { status.textContent = `Encryption setup failed: ${error.message}`; });
})();
