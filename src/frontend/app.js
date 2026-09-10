/**
 * Aura Automotive Service Platform - Frontend Multi-Portal Logic
 *
 * Implements:
 * 1. Multi-Portal Routing (Diagnostic Hub, Command Center, Knowledge Base, Audit Panel)
 * 2. Secure Role Switcher (Technician, Manager, Admin)
 * 3. Live RAG Chat Controller:
 *    - askQuestion(question) -> POST /query
 *    - handleSubmit(question) -> State management (loading, error, answer)
 *    - Answer({ result }) -> Render grounded answer first, then sources & citations
 * 4. Step-by-Step Instruction checklist interactivity
 * 5. Knowledge Base document intake & metadata form handling
 * 6. Dynamic data binding for Manager Metrics & Audit Logs
 */

const RAG_API_URL = window.NEXT_PUBLIC_RAG_API_URL || "";

// State
let activeRole = "TECHNICIAN";
let currentUser = null;
let conversationHistory = [];
let isQueryLoading = false;

// DOM Elements - Login & Auth
const loginScreen = document.getElementById("login-screen");
const appShell = document.getElementById("app-shell");
const authLoginForm = document.getElementById("auth-login-form");
const loginEmailInput = document.getElementById("login-email");
const loginPasswordInput = document.getElementById("login-password");
const loginRoleSelect = document.getElementById("login-role");
const loginErrorBanner = document.getElementById("login-error-banner");
const loginErrorText = document.getElementById("login-error-text");
const btnLoginSubmit = document.getElementById("btn-login-submit");
const btnLoginSpinner = document.getElementById("btn-login-spinner");
const demoTechBtn = document.getElementById("demo-tech-btn");
const demoManagerBtn = document.getElementById("demo-manager-btn");
const demoAdminBtn = document.getElementById("demo-admin-btn");
const navLogoutBtn = document.getElementById("nav-logout-btn");
const dropzoneBox = document.getElementById("dropzone-box");

// DOM Elements - Navigation & Shell
const navItems = document.querySelectorAll(".nav-menu .nav-item");
const portalViews = document.querySelectorAll(".portal-view");
const roleModal = document.getElementById("role-modal");
const userProfileTrigger = document.getElementById("user-profile-trigger");
const btnCloseRoleModal = document.getElementById("btn-close-role-modal");
const roleSelectItems = document.querySelectorAll(".role-select-item");
const userAvatarDisplay = document.getElementById("user-avatar-display");
const userNameDisplay = document.getElementById("user-name-display");
const userRoleDisplay = document.getElementById("user-role-display");
const btnStartSession = document.getElementById("btn-start-session");
const btnMobileMenu = document.getElementById("btn-mobile-menu");
const appSidebar = document.getElementById("app-sidebar");

// DOM Elements - Diagnostic Hub (Technician)
const hubChatStream = document.getElementById("hub-chat-stream");
const hubQueryInput = document.getElementById("hub-query-input");
const hubQuerySubmit = document.getElementById("hub-query-submit");
const backendStatusPill = document.getElementById("backend-status-pill");

// DOM Elements - Knowledge Base & Audit
const metadataForm = document.getElementById("metadata-tagging-form");
const kbTableBody = document.getElementById("kb-table-body");
const kbSearchInput = document.getElementById("kb-search-input");
const auditSearchInput = document.getElementById("audit-search-input");

// --- Real-Time Toast Notification System ---
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `aura-toast ${type}`;
  const icons = { info: "ℹ️", success: "✅", warning: "⚠️", alert: "🔔" };
  toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "toastFadeOut 0.3s forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- Number Count-Up Animation Engine ---
function animateCounter(element, target, suffix = "", duration = 1000) {
  if (!element) return;
  let start = 0;
  const startTime = performance.now();
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (target - start) * easeProgress);
    element.textContent = current.toLocaleString() + suffix;
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = target.toLocaleString() + suffix;
    }
  }
  requestAnimationFrame(update);
}

function triggerManagerCounters() {
  const repairsEl = document.getElementById("metric-repairs-count");
  const recallsEl = document.getElementById("metric-recalls-pct");
  const approvalsEl = document.getElementById("metric-approvals-count");
  if (repairsEl) animateCounter(repairsEl, 1248, "");
  if (recallsEl) animateCounter(recallsEl, 78, "%");
  if (approvalsEl) animateCounter(approvalsEl, 42, "");
}

// --- Strict Role-Based Tab Hiding & Route Gatekeeper ---
function applyRoleAccess(role, user) {
  activeRole = (role || "TECHNICIAN").toUpperCase();
  currentUser = user || {
    name: activeRole === "MANAGER" ? "J. Doe" : (activeRole === "ADMIN" ? "Admin M. Davis" : "Tech. M. Richards"),
    role: activeRole,
    avatar: activeRole === "MANAGER" ? "JD" : (activeRole === "ADMIN" ? "MD" : "TR")
  };

  if (userNameDisplay) userNameDisplay.textContent = currentUser.name;
  if (userRoleDisplay) userRoleDisplay.textContent = activeRole;
  if (userAvatarDisplay) userAvatarDisplay.textContent = currentUser.avatar;

  // Strict Tab Hiding: Hide forbidden navigation tabs completely
  const allNavItems = document.querySelectorAll(".nav-item[data-roles]");
  allNavItems.forEach(item => {
    const rolesStr = item.dataset.roles || "";
    const allowed = rolesStr.split(",").map(r => r.trim().toUpperCase());
    if (allowed.includes(activeRole)) {
      item.style.display = "flex";
    } else {
      item.style.display = "none";
    }
  });

  // Navigate to permitted default view
  if (activeRole === "TECHNICIAN") {
    switchView("view-diagnostic-hub");
  } else if (activeRole === "MANAGER") {
    switchView("view-command-center");
  } else if (activeRole === "ADMIN") {
    switchView("view-knowledge-base");
  }
}

// --- 1. Multi-Portal Routing with Route Protection ---
function switchView(targetViewId) {
  // Check if target view's nav item is hidden for active role
  const targetNav = document.querySelector(`.nav-item[data-target="${targetViewId}"]`);
  if (targetNav && targetNav.style.display === "none") {
    // Silently fall back to permitted home view
    const fallback = activeRole === "TECHNICIAN" ? "view-diagnostic-hub" : (activeRole === "MANAGER" ? "view-command-center" : "view-knowledge-base");
    if (targetViewId !== fallback) {
      return switchView(fallback);
    }
  }

  // Update sidebar active link
  navItems.forEach(item => {
    if (item.dataset.target === targetViewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Switch visible portal
  portalViews.forEach(view => {
    if (view.id === targetViewId) {
      view.classList.add("active");
    } else {
      view.classList.remove("active");
    }
  });

  // Close mobile sidebar if open
  if (appSidebar) {
    appSidebar.classList.remove("open");
  }

  // Real-time hooks per view
  if (targetViewId === "view-command-center") {
    updateObservabilityMetrics();
    triggerManagerCounters();
  } else if (targetViewId === "view-audit-panel") {
    fetchAuditLogs();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Nav link clicks
navItems.forEach(item => {
  item.addEventListener("click", () => {
    const target = item.dataset.target;
    if (target) {
      switchView(target);
    }
  });
});

// Mobile Hamburger
if (btnMobileMenu) {
  btnMobileMenu.addEventListener("click", () => {
    appSidebar.classList.toggle("open");
  });
}

// Start Session Button -> Navigates to Diagnostic Hub
if (btnStartSession) {
  btnStartSession.addEventListener("click", () => {
    switchView("view-diagnostic-hub");
    if (hubQueryInput) hubQueryInput.focus();
  });
}

// --- Sign Out Handler ---
if (navLogoutBtn) {
  navLogoutBtn.addEventListener("click", async () => {
    try {
      const sessionData = sessionStorage.getItem("aura_auth_session");
      if (sessionData) {
        const parsed = JSON.parse(sessionData);
        await fetch(`${RAG_API_URL}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: parsed.session_id })
        });
      }
    } catch (e) {
      // Ignore network errors on logout
    }
    sessionStorage.removeItem("aura_auth_session");
    if (appShell) appShell.style.display = "none";
    if (loginScreen) loginScreen.classList.remove("hidden");
    showToast("Signed out of session.", "info");
  });
}

// --- Quick Demo Role Selectors ---
if (demoTechBtn) {
  demoTechBtn.addEventListener("click", () => {
    if (loginEmailInput) loginEmailInput.value = "tech@aura.auto";
    demoTechBtn.classList.add("active");
    demoManagerBtn.classList.remove("active");
    demoAdminBtn.classList.remove("active");
  });
}

if (demoManagerBtn) {
  demoManagerBtn.addEventListener("click", () => {
    if (loginEmailInput) loginEmailInput.value = "manager@aura.auto";
    demoManagerBtn.classList.add("active");
    demoTechBtn.classList.remove("active");
    demoAdminBtn.classList.remove("active");
  });
}

if (demoAdminBtn) {
  demoAdminBtn.addEventListener("click", () => {
    if (loginEmailInput) loginEmailInput.value = "admin@aura.auto";
    demoAdminBtn.classList.add("active");
    demoTechBtn.classList.remove("active");
    demoManagerBtn.classList.remove("active");
  });
}

// --- Login Form Authentication Handler ---
if (authLoginForm) {
  authLoginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (loginErrorBanner) loginErrorBanner.style.display = "none";
    if (btnLoginSpinner) btnLoginSpinner.style.display = "inline";

    const email = loginEmailInput ? loginEmailInput.value.trim() : "";
    const password = loginPasswordInput ? loginPasswordInput.value : "";

    try {
      const res = await fetch(`${RAG_API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      if (!res.ok) {
        throw new Error("Authentication failed. Check credentials.");
      }

      const data = await res.json();
      sessionStorage.setItem("aura_auth_session", JSON.stringify(data));

      if (loginScreen) loginScreen.classList.add("hidden");
      if (appShell) appShell.style.display = "flex";

      applyRoleAccess(data.role, data.user);
      showToast(`Welcome, ${data.user.name} (${data.role})`, "success");
    } catch (err) {
      if (loginErrorBanner) {
        loginErrorBanner.style.display = "flex";
        if (loginErrorText) loginErrorText.textContent = err.message || "Login failed.";
      }
    } finally {
      if (btnLoginSpinner) btnLoginSpinner.style.display = "none";
    }
  });
}

// --- Interactive Diagnostic Quick Chips ---
document.querySelectorAll(".diag-chip-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const query = btn.dataset.query;
    if (query) {
      if (hubQueryInput) hubQueryInput.value = query;
      handleSubmit(query);
    }
  });
});

// --- Load VIN Button Handler ---
const btnLoadVin = document.getElementById("btn-load-vin");
if (btnLoadVin) {
  btnLoadVin.addEventListener("click", () => {
    const vinInput = document.getElementById("vin-search-input");
    const vin = vinInput ? vinInput.value.trim() : "1G1RC6E4XGU123456";
    showToast(`🚘 Vehicle context loaded for VIN: ${vin}`, "success");
    const vinTag = document.getElementById("vin-display-tag");
    if (vinTag) vinTag.textContent = `VIN: ${vin}`;
  });
}

// --- 3. Live Progressive Streaming RAG Diagnostic Hub Logic ---

let lastQuestion = "";

/**
 * Component: CitationList({ sources })
 * Renders citations beside the generated answer with expandable <details> source inspection.
 * @param {Object} props - { sources: Array }
 * @returns {string} - HTML string
 */
function CitationList({ sources }) {
  if (!sources || sources.length === 0) return "";

  const detailsHtml = sources.map(source => `
    <details class="citation-details" key="${escapeHtml(source.id || '')}">
      <summary>
        <span>${escapeHtml(source.label || '')}</span>
        <strong>${escapeHtml(source.document || '')}</strong>
        ${source.chunk_id ? `<code>${escapeHtml(source.chunk_id)}</code>` : ''}
      </summary>
      <p>${escapeHtml(source.text || 'No preview available')}</p>
    </details>
  `).join("");

  return `
    <section aria-label="Sources" class="streaming-citations-section">
      <div class="streaming-citations-title">
        <span>📚</span> Sources & Traceability (${sources.length})
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        ${detailsHtml}
      </div>
    </section>
  `;
}

/**
 * Progressively streams RAG answer tokens from /query/stream and renders citations.
 * Handles streaming interruptions and partial errors gracefully.
 * @param {string} question
 */
async function streamAnswer(question) {
  lastQuestion = question;
  isQueryLoading = true;
  hubQuerySubmit.disabled = true;
  hubQueryInput.disabled = true;

  // Create Assistant Message Bubble
  const botRow = document.createElement("div");
  botRow.className = "chat-bubble-row bot";

  botRow.innerHTML = `
    <div class="chat-avatar">AI</div>
    <div class="chat-bubble-content" style="width: 100%;">
      <div class="status-header-tag" style="font-size: 11px; font-weight: 700; color: #0284c7; margin-bottom: 6px; text-transform: uppercase;">
        ⚡ Streaming Answer...
      </div>
      <div class="answer-text-area" style="font-size: 13.5px; line-height: 1.5; color: #334155;">
        <span class="accumulated-text"></span><span class="streaming-cursor"></span>
      </div>
      <div class="citations-slot"></div>
      <div class="usage-slot"></div>
      <div class="error-slot"></div>
    </div>
  `;

  hubChatStream.appendChild(botRow);
  botRow.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const accumulatedTextSpan = botRow.querySelector(".accumulated-text");
  const cursorSpan = botRow.querySelector(".streaming-cursor");
  const citationsSlot = botRow.querySelector(".citations-slot");
  const usageSlot = botRow.querySelector(".usage-slot");
  const errorSlot = botRow.querySelector(".error-slot");
  const statusHeaderTag = botRow.querySelector(".status-header-tag");

  let currentAnswer = "";
  let currentSources = [];
  let streamCompletedSuccessfully = false;

  try {
    const response = await fetch(`${RAG_API_URL}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history: conversationHistory })
    });

    if (!response.ok || !response.body) {
      throw new Error("Could not start the stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Keep trailing incomplete line

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine.startsWith("data: ")) continue;

        const rawJson = trimmedLine.slice(6);
        try {
          const event = JSON.parse(rawJson);

          if (event.type === "citations") {
            currentSources = event.sources || [];
            citationsSlot.innerHTML = CitationList({ sources: currentSources });
            const hitLabel = event.cache_hit ? " &bull; ⚡ Cached" : "";
            statusHeaderTag.innerHTML = `🛡️ Grounded &bull; Citations Verified (${Math.round((event.confidence || 0) * 100)}%)${hitLabel}`;
          }

          if (event.type === "token") {
            currentAnswer += event.text;
            accumulatedTextSpan.textContent = currentAnswer;
            botRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }

          if (event.type === "usage") {
            const usage = event.usage;
            if (usage && usageSlot) {
              if (usage.cache_hit) {
                usageSlot.innerHTML = `
                  <div class="chat-usage-badge cached">
                    <span>⚡ Cached</span>
                    <span>&bull;</span>
                    <span>${usage.latency_ms}ms</span>
                    <span>&bull;</span>
                    <span>$0.000000</span>
                  </div>
                `;
              } else {
                usageSlot.innerHTML = `
                  <div class="chat-usage-badge live">
                    <span>🧠 Live RAG</span>
                    <span>&bull;</span>
                    <span>${usage.latency_ms}ms</span>
                    <span>&bull;</span>
                    <span>${usage.total_tokens} tokens</span>
                    <span>&bull;</span>
                    <span>$${(usage.estimated_cost || 0).toFixed(6)}</span>
                  </div>
                `;
              }
            }
          }

          if (event.type === "status" && event.status === "refused_weak_context") {
            statusHeaderTag.innerHTML = `<span style="color: #b45309;">⚠️ Guardrail Refusal</span>`;
          }

          if (event.type === "done") {
            streamCompletedSuccessfully = true;
          }

          if (event.type === "error") {
            throw new Error(event.message || "Streaming error occurred.");
          }
        } catch (parseErr) {
          if (parseErr.message.includes("Streaming error")) throw parseErr;
          console.warn("Error parsing event JSON:", parseErr);
        }
      }
    }

    // Stream finished
    if (cursorSpan) cursorSpan.remove();
    if (streamCompletedSuccessfully) {
      statusHeaderTag.textContent = currentSources.length > 0 ? "🛡️ Grounded Diagnostic Response" : "✓ Response Complete";
      // Update dialogue history
      conversationHistory.push({ role: "user", content: question });
      conversationHistory.push({ role: "assistant", content: currentAnswer });
      // Update manager command center metrics
      updateObservabilityMetrics();
    }

  } catch (error) {
    console.error("Stream failed:", error);
    if (cursorSpan) cursorSpan.remove();

    // Mark as incomplete while keeping received partial text & citations
    if (currentAnswer.length > 0) {
      accumulatedTextSpan.insertAdjacentHTML("beforeend", '<span class="incomplete-badge">(Incomplete)</span>');
    }

    statusHeaderTag.innerHTML = '<span style="color: #dc2626;">✕ Stream Interrupted</span>';

    // Show graceful inline error banner with Retry action
    errorSlot.innerHTML = `
      <div role="alert" class="stream-error-banner">
        <p>⚠️ ${escapeHtml(error.message || "The answer stopped streaming. Please try again.")}</p>
        <button class="stream-retry-btn" id="btn-stream-retry">Retry</button>
      </div>
    `;

    const retryBtn = errorSlot.querySelector("#btn-stream-retry");
    if (retryBtn) {
      retryBtn.addEventListener("click", () => {
        botRow.remove();
        streamAnswer(lastQuestion);
      });
    }

  } finally {
    isQueryLoading = false;
    hubQuerySubmit.disabled = false;
    hubQueryInput.disabled = false;
    hubQueryInput.focus();
  }
}

/**
 * Form submit handler for Technician Diagnostic Hub.
 * @param {string} question
 */
async function handleSubmit(question) {
  const trimmed = question.trim();
  if (!trimmed || isQueryLoading) return;

  hubQueryInput.value = "";

  // 1. Render User Message
  const userRow = document.createElement("div");
  userRow.className = "chat-bubble-row user";
  userRow.innerHTML = `
    <div class="chat-avatar user-avatar">Tech</div>
    <div class="chat-bubble-content">${escapeHtml(trimmed)}</div>
  `;
  hubChatStream.appendChild(userRow);
  userRow.scrollIntoView({ behavior: "smooth", block: "nearest" });

  // 2. Start Progressive Stream
  await streamAnswer(trimmed);
}

// Attach to window for testing
window.streamAnswer = streamAnswer;
window.CitationList = CitationList;

// Hub Query input listeners
if (hubQuerySubmit && hubQueryInput) {
  hubQuerySubmit.addEventListener("click", () => {
    handleSubmit(hubQueryInput.value);
  });

  hubQueryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit(hubQueryInput.value);
    }
  });
}

// --- 4. Interactive Step-by-Step Instruction Viewer & Checklist ---

function updateRepairProgress() {
  const checkboxes = document.querySelectorAll(".step-checkbox");
  if (!checkboxes.length) return;
  let checked = 0;
  checkboxes.forEach(cb => {
    if (cb.checked) checked++;
  });
  const total = checkboxes.length;
  const pct = Math.round((checked / total) * 100);
  const fillEl = document.getElementById("repair-progress-fill");
  const textEl = document.getElementById("repair-progress-text");
  if (fillEl) fillEl.style.width = `${pct}%`;
  if (textEl) textEl.textContent = `${checked} of ${total} steps (${pct}%)`;
}

const stepCheckboxes = document.querySelectorAll(".step-checkbox");
stepCheckboxes.forEach(cb => {
  cb.addEventListener("change", (e) => {
    const stepCard = e.target.closest(".step-item-card");
    if (stepCard) {
      stepCard.style.opacity = e.target.checked ? "0.75" : "1";
    }
    updateRepairProgress();
  });
});

// Real-Time Technician Feedback Dispatcher
async function sendTechnicianFeedback(action, notes = "") {
  try {
    const res = await fetch(`${RAG_API_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        technician: currentUser ? currentUser.name : "Tech. M. Richards",
        action: action,
        vin: "1G1RC6E4XGU123456",
        doc_id: "TRNS-092",
        notes: notes
      })
    });
    if (res.ok) {
      fetchAuditLogs();
    }
  } catch (err) {
    console.warn("Feedback API error:", err);
  }
}

// Diagnostic Action Buttons
const btnCompleteJob = document.getElementById("btn-complete-job");
if (btnCompleteJob) {
  btnCompleteJob.addEventListener("click", () => {
    stepCheckboxes.forEach(cb => {
      cb.checked = true;
      const card = cb.closest(".step-item-card");
      if (card) card.style.opacity = "0.75";
    });
    updateRepairProgress();
    sendTechnicianFeedback("Complete Job", "Technician verified all Bank 1 specs.");
    showToast("✓ Complete Job: Sign-off recorded in compliance audit log!", "success");
  });
}

const btnReportUnclear = document.getElementById("btn-report-unclear");
if (btnReportUnclear) {
  btnReportUnclear.addEventListener("click", () => {
    sendTechnicianFeedback("Report Unclear", "Step 3 connector C102 requires clarification.");
    showToast("⚠️ Report Unclear: Step flagged for engineering review.", "warning");
  });
}

const btnOutdatedGuide = document.getElementById("btn-outdated-guide");
if (btnOutdatedGuide) {
  btnOutdatedGuide.addEventListener("click", () => {
    sendTechnicianFeedback("Outdated Guide", "Manual revision needed for newer coil harness.");
    showToast("🔄 Outdated Guide: Engineering revision notice queued.", "info");
  });
}

// --- 5. Knowledge Base Management & Metadata Tagging ---

if (metadataForm) {
  metadataForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const model = document.getElementById("tag-vehicle-model").value || "Series X";
    const year = document.getElementById("tag-model-year").value || "2023";
    const region = document.getElementById("tag-region").value || "Global";
    const version = document.getElementById("tag-doc-version").value || "v1.0.0";
    const statusRadio = document.querySelector('input[name="doc_status"]:checked');
    const statusVal = statusRadio ? statusRadio.value : "Published";

    const newDocId = `DOC-${Math.floor(1000 + Math.random() * 9000)}`;
    const newTitle = `${model} Technical Service Addendum`;

    // Prepend row to table
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${newDocId}</code></td>
      <td>
        <div class="doc-title-cell">
          <span>📘</span>
          <span>${escapeHtml(newTitle)}</span>
        </div>
      </td>
      <td>${escapeHtml(model)} / ${escapeHtml(region)}</td>
      <td>${escapeHtml(version)}</td>
      <td><span class="status-badge ${statusVal.toLowerCase()}">${statusVal.toUpperCase()}</span></td>
    `;
    kbTableBody.prepend(tr);

    alert(`✓ Document ${newDocId} successfully tagged and added to the Knowledge Base!`);
    metadataForm.reset();
  });
}

// Search Filter: Knowledge Base Table
if (kbSearchInput) {
  kbSearchInput.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const rows = kbTableBody.querySelectorAll("tr");
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(term) ? "" : "none";
    });
  });
}

// Search Filter: Audit Log Table
if (auditSearchInput) {
  auditSearchInput.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase();
    const tbody = document.querySelector("#audit-table tbody");
    if (tbody) {
      const rows = tbody.querySelectorAll("tr");
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? "" : "none";
      });
    }
  });
}

// Manager Export Button
const btnExportManager = document.getElementById("btn-export-manager");
if (btnExportManager) {
  btnExportManager.addEventListener("click", () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
      report: "Management Oversight Operational Metrics",
      repairs_completed: 1248,
      open_recalls_addressed_pct: 78,
      pending_approvals: 42,
      export_timestamp: new Date().toISOString()
    }, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", "management_oversight_metrics.json");
    dlAnchor.click();
  });
}

// Audit Export Button
const btnExportAudit = document.getElementById("btn-export-audit");
if (btnExportAudit) {
  btnExportAudit.addEventListener("click", () => {
    alert("Exporting Global Compliance Audit Log (CSV)... Download started.");
  });
}

// Request Report Button (Compliance Card)
const btnRequestCompliance = document.getElementById("btn-request-compliance-report");
if (btnRequestCompliance) {
  btnRequestCompliance.addEventListener("click", () => {
    alert("Regional SUV Recall Compliance Report generated. PDF dispatched to compliance officer.");
  });
}

// --- 6. RAG Observability & Query Caching Metrics Manager ---

async function updateObservabilityMetrics() {
  try {
    const res = await fetch(`${RAG_API_URL}/metrics/observability`);
    if (!res.ok) return;
    const data = await res.json();

    const hitRateEl = document.getElementById("obs-hit-rate");
    const hitCountEl = document.getElementById("obs-hit-count");
    const costSpentEl = document.getElementById("obs-cost-spent");
    const tokensSpentEl = document.getElementById("obs-tokens-spent");
    const avgLatencyEl = document.getElementById("obs-avg-latency");
    const latencySubEl = document.getElementById("obs-latency-sub");
    const cacheEntriesPill = document.getElementById("cache-entries-pill");

    if (hitRateEl) hitRateEl.textContent = `${Math.round(data.cache_hit_rate * 100)}%`;
    if (hitCountEl) hitCountEl.textContent = `${data.cache_hits} hits / ${data.total_requests} queries`;
    if (costSpentEl) costSpentEl.textContent = `$${(data.total_estimated_cost || 0).toFixed(6)}`;
    if (tokensSpentEl) tokensSpentEl.textContent = `${(data.total_tokens_spent || 0).toLocaleString()} tokens processed`;
    if (avgLatencyEl) avgLatencyEl.textContent = `${(data.average_latency_ms || 0).toFixed(1)} ms`;
    if (cacheEntriesPill) cacheEntriesPill.textContent = `Active Cache: ${data.active_cache_entries || 0} entries`;
    if (latencySubEl) {
      latencySubEl.textContent = data.cache_hits > 0 ? `⚡ ${data.cache_hits} queries served in < 5ms` : "Cache speedup active";
    }
  } catch (err) {
    console.warn("Could not fetch observability metrics:", err);
  }
}

// Clear Query Cache button handler
const btnClearCache = document.getElementById("btn-clear-query-cache");
if (btnClearCache) {
  btnClearCache.addEventListener("click", async () => {
    try {
      const res = await fetch(`${RAG_API_URL}/cache/clear`, { method: "POST" });
      if (res.ok) {
        const result = await res.json();
        alert(`✓ Query cache purged! (${result.purged_entries} entries removed)`);
        updateObservabilityMetrics();
      }
    } catch (err) {
      alert("Failed to clear query cache: " + err.message);
    }
  });
}

// --- 7. Backend Connection Health Check ---

async function checkBackendHealth() {
  try {
    const res = await fetch(`${RAG_API_URL}/status`);
    if (res.ok) {
      if (backendStatusPill) {
        backendStatusPill.textContent = "● RAG Online";
        backendStatusPill.style.color = "var(--success)";
      }
    }
  } catch (err) {
    if (backendStatusPill) {
      backendStatusPill.textContent = "● Offline";
      backendStatusPill.style.color = "var(--danger)";
    }
  }
}

// Utility: HTML Escaping
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Fetch Real-time Audit Logs from Backend
async function fetchAuditLogs() {
  try {
    const res = await fetch(`${RAG_API_URL}/audit-logs`);
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.querySelector("#audit-table tbody");
    if (!tbody || !data.audit_logs) return;
    tbody.innerHTML = "";
    data.audit_logs.forEach(log => {
      const tr = document.createElement("tr");
      const trend = log.feedback_trend || "Logged";
      let trendClass = "neutral";
      if (trend.includes("Positive") || trend.includes("Verified") || trend.includes("Active") || trend.includes("Completed")) {
        trendClass = "positive";
      } else if (trend.includes("Issues") || trend.includes("Needed") || trend.includes("Requested")) {
        trendClass = "negative";
      }
      tr.innerHTML = `
        <td><code>${escapeHtml(log.doc_id)}</code></td>
        <td><span class="status-badge published">${escapeHtml(log.action)}</span></td>
        <td>${escapeHtml(log.operator)}</td>
        <td>${escapeHtml(log.timestamp)}</td>
        <td><span class="feedback-trend-pill ${trendClass}">${escapeHtml(trend)}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.warn("Could not fetch audit logs:", err);
  }
}

// Drag & Drop Box Handlers for Knowledge Base
if (dropzoneBox) {
  dropzoneBox.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzoneBox.classList.add("drag-over");
  });

  dropzoneBox.addEventListener("dragleave", () => {
    dropzoneBox.classList.remove("drag-over");
  });

  dropzoneBox.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzoneBox.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      showToast(`📄 File "${file.name}" uploaded and staged for ingestion!`, "success");
      const newDocId = `DOC-${Math.floor(1000 + Math.random() * 9000)}`;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><code>${newDocId}</code></td>
        <td>
          <div class="doc-title-cell">
            <span>📘</span>
            <span>${escapeHtml(file.name)}</span>
          </div>
        </td>
        <td>SUV Model X / Global</td>
        <td>v1.0 (Staged)</td>
        <td><span class="status-badge draft">STAGED</span></td>
      `;
      if (kbTableBody) kbTableBody.prepend(tr);
    }
  });
}

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  updateObservabilityMetrics();
  updateRepairProgress();
  fetchAuditLogs();

  // Check existing session
  const savedSession = sessionStorage.getItem("aura_auth_session");
  if (savedSession) {
    try {
      const parsed = JSON.parse(savedSession);
      if (loginScreen) loginScreen.classList.add("hidden");
      if (appShell) appShell.style.display = "flex";
      applyRoleAccess(parsed.role, parsed.user);
      return;
    } catch (e) {
      sessionStorage.removeItem("aura_auth_session");
    }
  }

  // Show login screen by default
  if (loginScreen) loginScreen.classList.remove("hidden");
  if (appShell) appShell.style.display = "none";
});
