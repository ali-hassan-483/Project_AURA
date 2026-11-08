let authToken = localStorage.getItem("aura_admin_token") || "";
let activeTab = "simulator";
let currentMemories = [];

document.addEventListener("DOMContentLoaded", () => {
  checkAuth();

  // Register PWA Service Worker for Mobile installation
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
      .then(() => console.log("Aylin PWA Service Worker Registered"))
      .catch((err) => console.log("SW registration error:", err));
  }
});

// ---------------- MOBILE DRAWER ----------------
function toggleMobileDrawer() {
  const drawer = document.getElementById("mobileDrawer");
  const backdrop = document.getElementById("mobileDrawerBackdrop");
  if (!drawer || !backdrop) return;
  
  if (drawer.classList.contains("-translate-x-full")) {
    drawer.classList.remove("-translate-x-full");
    backdrop.classList.remove("hidden");
  } else {
    drawer.classList.add("-translate-x-full");
    backdrop.classList.add("hidden");
  }
}

function mobileSwitchTab(tabId) {
  toggleMobileDrawer();
  switchTab(tabId);
}

// ---------------- TAB SWITCHING ----------------
function switchTab(tabId) {
  activeTab = tabId;
  const sections = ["overview", "simulator", "persona", "memory", "voice", "image", "providers", "privacy"];
  sections.forEach(s => {
    const el = document.getElementById(`tab-${s}`);
    if (el) el.classList.add("hidden");
  });

  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.remove("hidden");

  // Update nav button styling
  const buttons = document.querySelectorAll(".nav-btn");
  buttons.forEach(btn => {
    btn.className = "nav-btn w-full flex items-center space-x-3 px-3.5 py-2 rounded-xl text-sm font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800/50";
  });

  event?.currentTarget?.classList?.remove("text-slate-400", "hover:text-slate-200", "hover:bg-slate-800/50");
  event?.currentTarget?.classList?.add("text-rose-400", "bg-rose-500/10", "border", "border-rose-500/20");

  if (tabId === "memory" && authToken) loadUserDropdown();
  if (tabId === "overview" && authToken) refreshMetrics();
  if (tabId === "providers" && authToken) loadProviders();
  if (tabId === "simulator") loadChatHistory();

  lucide.createIcons();
}

// ---------------- AUTHENTICATION ----------------
async function checkAuth() {
  const statusText = document.getElementById("authStatusText");
  const adminNav = document.getElementById("adminNavGroup");
  const mobileAdminNav = document.getElementById("mobileAdminNavGroup");
  const chatSection = document.getElementById("tab-simulator");
  const loginWall = document.getElementById("chatLoginWall");

  if (!authToken) {
    statusText.innerText = "Admin Login";
    statusText.className = "text-slate-300";
    if (adminNav) adminNav.classList.add("hidden");
    if (mobileAdminNav) mobileAdminNav.classList.add("hidden");
    // Show login wall, hide chat
    if (chatSection) chatSection.classList.add("hidden");
    if (loginWall) loginWall.classList.remove("hidden");
    return;
  }

  // Validate token against backend
  try {
    const res = await fetch("/api/admin/metrics", { headers: getAuthHeaders() });
    if (res.ok) {
      statusText.innerText = "Admin (Logout)";
      statusText.className = "text-emerald-400 font-semibold";
      if (adminNav) adminNav.classList.remove("hidden");
      if (mobileAdminNav) mobileAdminNav.classList.remove("hidden");
      // Show chat, hide login wall
      if (loginWall) loginWall.classList.add("hidden");
      if (chatSection) chatSection.classList.remove("hidden");
      refreshMetrics();
      loadCharacterSettings();
      loadProviders();
      loadUserDropdown();
      loadChatHistory();
    } else {
      localStorage.removeItem("aura_admin_token");
      authToken = "";
      statusText.innerText = "Admin Login";
      statusText.className = "text-slate-300";
      if (adminNav) adminNav.classList.add("hidden");
      if (mobileAdminNav) mobileAdminNav.classList.add("hidden");
      if (chatSection) chatSection.classList.add("hidden");
      if (loginWall) loginWall.classList.remove("hidden");
    }
  } catch (e) {
    if (adminNav) adminNav.classList.add("hidden");
    if (mobileAdminNav) mobileAdminNav.classList.add("hidden");
    if (chatSection) chatSection.classList.add("hidden");
    if (loginWall) loginWall.classList.remove("hidden");
  }

  if (window.lucide) lucide.createIcons();
}

function handleAuthAction() {
  if (authToken) {
    if (confirm("Are you sure you want to log out of Admin Dashboard?")) {
      localStorage.removeItem("aura_admin_token");
      authToken = "";
      checkAuth();
    }
  } else {
    toggleAuthModal();
  }
}

function toggleAuthModal() {
  const modal = document.getElementById("authModal");
  modal.classList.toggle("hidden");
}

async function performLogin() {
  const username = document.getElementById("modalUsername").value.trim();
  const password = document.getElementById("modalPassword").value.trim();

  if (!username || !password) {
    alert("Please enter both username and password.");
    return;
  }

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("aura_admin_token", authToken);
      toggleAuthModal();
      await checkAuth();
      switchTab("simulator");
    } else {
      alert("Invalid username or password.");
    }
  } catch (err) {
    alert("Login failed: " + err.message);
  }
}

function getAuthHeaders() {
  return {
    "Authorization": `Bearer ${authToken}`,
    "Content-Type": "application/json"
  };
}

// ---------------- METRICS & DASHBOARD ----------------
async function refreshMetrics() {
  try {
    const res = await fetch("/api/admin/metrics", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("metricTotalMessages").innerText = data.total_messages || 0;
    document.getElementById("metricVoiceMessages").innerText = data.voice_messages || 0;
    document.getElementById("metricImageMessages").innerText = data.image_messages || 0;
    document.getElementById("metricTotalMemories").innerText = data.total_memories || 0;
    document.getElementById("currentAiProvider").innerText = data.primary_provider || "Groq";

    // Activity Logs
    const logContainer = document.getElementById("activityLogsList");
    logContainer.innerHTML = "";
    if (data.recent_logs && data.recent_logs.length > 0) {
      data.recent_logs.forEach(log => {
        const item = document.createElement("div");
        item.className = "p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between";
        item.innerHTML = `
          <div>
            <span class="font-medium text-slate-200 capitalize">${log.event_type.replace('_', ' ')}</span>
            <span class="text-slate-500 text-[11px] ml-2">${log.details || ''}</span>
          </div>
          <span class="text-slate-500 text-[10px]">${new Date(log.timestamp).toLocaleTimeString()}</span>
        `;
        logContainer.appendChild(item);
      });
    } else {
      logContainer.innerHTML = `<p class="text-slate-500 py-2">No activity logged yet.</p>`;
    }

    // Provider statuses
    const provContainer = document.getElementById("providerStatusList");
    provContainer.innerHTML = "";
    if (data.active_providers) {
      for (const [p, active] of Object.entries(data.active_providers)) {
        const item = document.createElement("div");
        item.className = "flex items-center justify-between p-2 rounded bg-slate-900/50 border border-slate-800";
        item.innerHTML = `
          <span class="font-medium text-slate-300 capitalize">${p}</span>
          <span class="px-2 py-0.5 rounded text-[10px] ${active ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}">${active ? 'Available' : 'Offline / Standby'}</span>
        `;
        provContainer.appendChild(item);
      }
    }
  } catch (err) {
    console.error("Failed to load metrics:", err);
  }
}

// ---------------- LIVE SIMULATOR & PERSISTENCE ----------------
const LOCAL_CHAT_KEY = "aylin_chat_history_backup";

function getLocalChat() {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_CHAT_KEY) || "[]");
  } catch (e) {
    return [];
  }
}

function saveLocalMessage(sender, text, imageUrl = null, voiceUrl = null) {
  try {
    const list = getLocalChat();
    list.push({
      sender,
      raw_content: text,
      message_type: imageUrl ? "image" : (voiceUrl ? "voice" : "text"),
      media_url: imageUrl || voiceUrl,
      created_at: new Date().toISOString()
    });
    // Keep last 100 messages in localStorage
    if (list.length > 100) list.shift();
    localStorage.setItem(LOCAL_CHAT_KEY, JSON.stringify(list));
  } catch (e) {
    console.warn("Could not save to localStorage:", e);
  }
}

async function loadChatHistory() {
  const container = document.getElementById("chatMessages");
  let messages = [];

  try {
    const res = await fetch("/api/admin/simulator/history?phone=%2B923001234567");
    if (res.ok) {
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        messages = data.messages;
        localStorage.setItem(LOCAL_CHAT_KEY, JSON.stringify(messages));
      }
    }
  } catch (err) {
    console.error("Failed to load past chat history from server:", err);
  }

  // If server has no messages (e.g. Render redeployed or restarted container),
  // immediately restore from browser localStorage and sync back to server!
  if (messages.length === 0) {
    const localBackup = getLocalChat();
    if (localBackup.length > 0) {
      console.log(`Restoring ${localBackup.length} messages from local browser storage...`);
      messages = localBackup;

      // Sync restored messages back to server database in background
      fetch("/api/admin/simulator/sync-history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: "+923001234567", messages: localBackup })
      }).catch(e => console.warn("Sync failed:", e));
    }
  }

  if (messages.length > 0) {
    container.innerHTML = "";
    messages.forEach(m => {
      let img = null;
      let voice = null;
      if (m.message_type === "image" && m.media_url) img = m.media_url;
      if (m.message_type === "voice" && m.media_url) voice = m.media_url;
      const content = m.raw_content || m.content || "";
      appendChatMessage(m.sender, content, img, voice, false);
    });
  }
}

async function sendSimulatorMessage() {
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendChatMessage("user", msg, null, null, true);

  // Add typing indicator
  const typingId = appendTypingIndicator();

  try {
    const res = await fetch("/api/admin/simulator/chat", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ message: msg, phone: "+923001234567", name: "Jaan" })
    });
    removeTypingIndicator(typingId);

    if (res.ok) {
      const data = await res.json();
      appendChatMessage("assistant", data.reply, data.image_url, data.voice_url, true);
    } else {
      appendChatMessage("assistant", "Sorry jaan, there was a temporary connection hiccup!", null, null, true);
    }
  } catch (e) {
    removeTypingIndicator(typingId);
    appendChatMessage("assistant", "Error communicating with Aylin engine.", null, null, true);
  }
}

function sendQuickPrompt(promptText) {
  document.getElementById("chatInput").value = promptText;
  sendSimulatorMessage();
}

function appendChatMessage(sender, text, imageUrl = null, voiceUrl = null, saveToStorage = false) {
  if (saveToStorage) {
    saveLocalMessage(sender, text, imageUrl, voiceUrl);
  }

  const container = document.getElementById("chatMessages");
  const row = document.createElement("div");

  if (sender === "user") {
    row.className = "flex items-end justify-end space-x-2";
    row.innerHTML = `
      <div class="chat-bubble-user p-3 rounded-2xl shadow-sm text-xs leading-relaxed max-w-[80%]">
        ${escapeHtml(text)}
      </div>
    `;
  } else {
    row.className = "flex items-start space-x-2 max-w-[85%]";
    let mediaHtml = "";

    if (imageUrl) {
      mediaHtml += `
        <div class="mt-2 rounded-xl overflow-hidden border border-slate-700 max-w-xs shadow-md">
          <img src="${imageUrl}" alt="Aylin" class="w-full h-auto object-cover" />
        </div>
      `;
    }

    if (voiceUrl) {
      mediaHtml += `
        <div class="mt-2 p-2 rounded-xl bg-slate-900/90 border border-slate-700/80 flex items-center space-x-2">
          <audio controls src="${voiceUrl}" class="h-8 w-60"></audio>
        </div>
      `;
    }

    row.innerHTML = `
      <div class="w-7 h-7 rounded-full bg-rose-500/20 text-rose-300 flex items-center justify-center text-xs font-bold mt-1">A</div>
      <div class="chat-bubble-aura p-3 rounded-2xl shadow-sm text-xs leading-relaxed">
        <p>${escapeHtml(text)}</p>
        ${mediaHtml}
      </div>
    `;
  }

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
  const container = document.getElementById("chatMessages");
  const id = "typing-" + Date.now();
  const row = document.createElement("div");
  row.id = id;
  row.className = "flex items-center space-x-2";
  row.innerHTML = `
    <div class="w-7 h-7 rounded-full bg-rose-500/20 text-rose-300 flex items-center justify-center text-xs font-bold">A</div>
    <div class="chat-bubble-aura px-3 py-2 rounded-2xl text-xs text-slate-400 italic">
      Aura is typing...
    </div>
  `;
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function clearChatSimulator() {
  const container = document.getElementById("chatMessages");
  container.innerHTML = "";
  localStorage.removeItem(LOCAL_CHAT_KEY);
  appendChatMessage("assistant", "Chat history cleared. I'm ready, what's on your mind?", null, null, false);
}

// ---------------- PERSONA STUDIO ----------------
async function loadCharacterSettings() {
  try {
    const res = await fetch("/api/admin/character", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("personaName").value = data.name || "Aura";
    document.getElementById("personaAge").value = data.age || 21;
    document.getElementById("personaSeed").value = data.seed || 789234;
    document.getElementById("personaSystemPrompt").value = data.system_prompt || "";
    document.getElementById("personaIdentityPrompt").value = data.identity_prompt || "";
    document.getElementById("personaNegativePrompt").value = data.negative_prompt || "";
  } catch (err) {
    console.error("Error loading persona:", err);
  }
}

async function savePersona(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById("personaName").value,
    age: parseInt(document.getElementById("personaAge").value),
    seed: parseInt(document.getElementById("personaSeed").value),
    system_prompt: document.getElementById("personaSystemPrompt").value,
    identity_prompt: document.getElementById("personaIdentityPrompt").value,
    negative_prompt: document.getElementById("personaNegativePrompt").value
  };

  try {
    const res = await fetch("/api/admin/character", {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert("Aura's persona and identity settings updated successfully!");
    } else {
      alert("Failed to save settings.");
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// ---------------- MEMORY LEDGER ----------------
async function loadUserDropdown() {
  try {
    const res = await fetch("/api/admin/users", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const users = await res.json();
    const select = document.getElementById("userMemorySelect");
    select.innerHTML = "";

    if (users.length === 0) {
      select.innerHTML = `<option value="1">Default User (ID: 1)</option>`;
      loadUserMemories(1);
      return;
    }

    users.forEach(u => {
      const opt = document.createElement("option");
      opt.value = u.id;
      opt.innerText = `${u.name || 'User'} (${u.phone_number})`;
      select.appendChild(opt);
    });

    loadUserMemories(users[0].id);
  } catch (err) {
    console.error("Error loading users:", err);
  }
}

async function loadUserMemories(userId) {
  try {
    const res = await fetch(`/api/admin/memories/${userId}`, { headers: getAuthHeaders() });
    if (!res.ok) return;
    currentMemories = await res.json();
    renderMemoriesTable(currentMemories);
  } catch (err) {
    console.error("Error loading memories:", err);
  }
}

function renderMemoriesTable(memories) {
  const tbody = document.getElementById("memoriesTableBody");
  tbody.innerHTML = "";

  if (memories.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">No memories recorded yet for this user.</td></tr>`;
    return;
  }

  memories.forEach(m => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-900/40";
    tr.innerHTML = `
      <td class="p-3"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] uppercase font-mono">${m.category}</span></td>
      <td class="p-3 font-medium text-slate-200">${m.memory_key}</td>
      <td class="p-3 text-slate-300">${escapeHtml(m.memory_value)}</td>
      <td class="p-3"><span class="text-rose-400 font-bold">${'★'.repeat(m.importance)}</span></td>
      <td class="p-3 text-right">
        <button onclick="deleteMemoryItem(${m.id})" class="text-rose-400 hover:text-rose-300 px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-xs">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterMemoriesTable() {
  const term = document.getElementById("memorySearchInput").value.toLowerCase();
  const filtered = currentMemories.filter(m => 
    m.memory_key.toLowerCase().includes(term) || m.memory_value.toLowerCase().includes(term)
  );
  renderMemoriesTable(filtered);
}

function openAddMemoryModal() {
  document.getElementById("addMemoryModal").classList.remove("hidden");
}

function closeAddMemoryModal() {
  document.getElementById("addMemoryModal").classList.add("hidden");
}

async function saveNewMemory() {
  const userId = parseInt(document.getElementById("newMemUserId").value);
  const category = document.getElementById("newMemCategory").value;
  const key = document.getElementById("newMemKey").value;
  const value = document.getElementById("newMemValue").value;
  const importance = parseInt(document.getElementById("newMemImportance").value);

  if (!key || !value) {
    alert("Key and value are required");
    return;
  }

  try {
    const res = await fetch("/api/admin/memories", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ user_id: userId, category, key, value, importance })
    });
    if (res.ok) {
      closeAddMemoryModal();
      loadUserMemories(userId);
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function deleteMemoryItem(id) {
  if (!confirm("Are you sure you want to delete this memory item?")) return;
  try {
    const res = await fetch(`/api/admin/memories/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    if (res.ok) {
      const userId = document.getElementById("userMemorySelect").value;
      loadUserMemories(userId);
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// ---------------- VOICE STUDIO ----------------
async function generateVoicePreview() {
  const text = document.getElementById("voicePreviewText").value;
  const voice = document.getElementById("voiceSelect").value;
  const rate = document.getElementById("voiceRate").value;
  const pitch = document.getElementById("voicePitch").value;

  try {
    const res = await fetch("/api/admin/voice/preview", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ text, voice, rate, pitch })
    });
    if (res.ok) {
      const data = await res.json();
      const player = document.getElementById("audioPreviewPlayer");
      player.src = data.audio_url;
      player.play();
    }
  } catch (err) {
    alert("Voice synthesis failed: " + err.message);
  }
}

// ---------------- IMAGE LAB ----------------
function setPromptAndGenerate(prompt) {
  document.getElementById("imageCustomPrompt").value = prompt;
  generateCustomImage();
}

async function generateCustomImage() {
  const prompt = document.getElementById("imageCustomPrompt").value || "candid smiling selfie";
  const seedOffset = parseInt(document.getElementById("imageSeedOffset").value || 0);

  const spinner = document.getElementById("imageSpinner");
  const imgTag = document.getElementById("generatedImgTag");
  const status = document.getElementById("imageStatusText");

  spinner.classList.remove("hidden");
  status.innerText = "Conditioning face anchor & rendering...";

  try {
    const res = await fetch("/api/admin/image/generate", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ prompt, seed_offset: seedOffset })
    });

    if (res.ok) {
      const data = await res.json();
      imgTag.src = data.image_url + "?t=" + Date.now();
      status.innerText = `Rendered: ${prompt}`;
    } else {
      const errData = await res.json().catch(() => ({}));
      status.innerText = "Error: " + (errData.detail || "Generation failed, please try again in a few seconds.");
    }
  } catch (e) {
    status.innerText = "Error: " + e.message;
  } finally {
    spinner.classList.add("hidden");
  }
}

// ---------------- REFERENCE PHOTO UPLOAD ----------------
async function uploadReferencePhoto(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const statusEl = document.getElementById("refUploadStatus");
  const previewDiv = document.getElementById("refPhotoPreview");
  const previewImg = document.getElementById("refPhotoImg");

  // Show local preview immediately
  previewImg.src = URL.createObjectURL(file);
  previewDiv.classList.remove("hidden");
  statusEl.innerText = "Uploading...";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/admin/character/upload-reference", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      statusEl.innerText = "✅ " + (data.message || "Reference photo saved!");
      statusEl.className = "text-xs text-emerald-400";
    } else {
      statusEl.innerText = "❌ " + (data.detail || "Upload failed");
      statusEl.className = "text-xs text-red-400";
    }
  } catch (e) {
    statusEl.innerText = "❌ Error: " + e.message;
    statusEl.className = "text-xs text-red-400";
  }
}

// ---------------- AI PROVIDERS ----------------
async function loadProviders() {
  try {
    const res = await fetch("/api/admin/providers", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    const pills = {
      groq: "groqStatusPill",
      gemini: "geminiStatusPill",
      ollama: "ollamaStatusPill",
      openrouter: "openrouterStatusPill"
    };

    for (const [k, id] of Object.entries(pills)) {
      const el = document.getElementById(id);
      if (el && data.statuses) {
        const isUp = data.statuses[k];
        el.innerText = isUp ? "Active & Verified" : "Not Configured / Idle";
        el.className = isUp ? "text-emerald-400 font-bold" : "text-slate-500 font-mono";
      }
    }
  } catch (err) {
    console.error("Error loading providers:", err);
  }
}

async function setPrimaryProvider(provider) {
  try {
    const res = await fetch("/api/admin/providers/set-primary", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ provider })
    });
    if (res.ok) {
      alert(`Primary AI provider switched to: ${provider}`);
      refreshMetrics();
    }
  } catch (e) {
    alert("Failed: " + e.message);
  }
}

// ---------------- PRIVACY PURGE ----------------
async function purgeUserData() {
  const userId = document.getElementById("purgeUserIdInput").value;
  if (!userId) {
    alert("Please enter a valid user ID.");
    return;
  }
  if (!confirm(`CAUTION: Are you sure you want to PERMANENTLY ERASE all data for User ID ${userId}?`)) return;

  try {
    const res = await fetch(`/api/admin/users/${userId}/purge`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    if (res.ok) {
      alert(`User ${userId} and all related messages and memories have been permanently deleted.`);
      refreshMetrics();
      loadUserDropdown();
    }
  } catch (e) {
    alert("Error: " + e.message);
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}
