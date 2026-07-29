"use strict";

(() => {
  function cookie(name) {
    const entry = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${name}=`));
    return entry ? decodeURIComponent(entry.slice(name.length + 1)) : "";
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open("nullsec-identity-v1", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("identities", { keyPath: "username" });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function getOrCreate(username) {
    const database = await openDatabase();
    const existing = await new Promise((resolve, reject) => {
      const request = database.transaction("identities", "readonly").objectStore("identities").get(username);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    if (existing && existing.privateKey && existing.publicJwk) {
      database.close();
      return existing;
    }

    const pair = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, false, ["deriveBits"]);
    const publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
    const identity = { username, privateKey: pair.privateKey, publicJwk };
    await new Promise((resolve, reject) => {
      const transaction = database.transaction("identities", "readwrite");
      transaction.objectStore("identities").put(identity);
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
    });
    database.close();
    return identity;
  }

  async function initialize() {
    const username = document.body.dataset.identityUsername;
    const keyUrl = document.body.dataset.identityKeyUrl;
    if (!username || !keyUrl) throw new Error("Missing identity configuration.");
    if (!window.crypto || !window.crypto.subtle || !window.indexedDB) {
      throw new Error("This browser does not support the required secure Web APIs.");
    }
    const identity = await getOrCreate(username);
    const response = await fetch(keyUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify({ public_key: identity.publicJwk }),
    });
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch (_error) { data = {}; }
      throw new Error(data.error || `Public-key registration failed (${response.status}).`);
    }
    return identity;
  }

  window.NullSecIdentity = Object.freeze({ ready: initialize() });
})();
