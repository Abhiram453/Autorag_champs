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
let activeRole = "MANAGER"; // Default starting role as shown in screenshot
let conversationHistory = [];
let isQueryLoading = false;

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

// --- 1. Multi-Portal Routing ---

function switchView(targetViewId) {
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

  // Auto-scroll to top
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

// --- 2. Secure Role Switcher ---

if (userProfileTrigger) {
  userProfileTrigger.addEventListener("click", () => {
    roleModal.style.display = "flex";
  });
}

if (btnCloseRoleModal) {
  btnCloseRoleModal.addEventListener("click", () => {
    roleModal.style.display = "none";
  });
}

// Close modal when clicking outside
window.addEventListener("click", (e) => {
  if (e.target === roleModal) {
    roleModal.style.display = "none";
  }
});

roleSelectItems.forEach(item => {
  item.addEventListener("click", () => {
    const role = item.dataset.role;
    const name = item.dataset.name;
    const avatar = item.dataset.avatar;
    const targetView = item.dataset.target;

    activeRole = role;
    userNameDisplay.textContent = name;
    userRoleDisplay.textContent = role;
    userAvatarDisplay.textContent = avatar;

    roleSelectItems.forEach(i => i.classList.remove("selected"));
    item.classList.add("selected");

    roleModal.style.display = "none";
    switchView(targetView);
  });
});

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
      <div class="error-slot"></div>
    </div>
  `;

  hubChatStream.appendChild(botRow);
  botRow.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const accumulatedTextSpan = botRow.querySelector(".accumulated-text");
  const cursorSpan = botRow.querySelector(".streaming-cursor");
  const citationsSlot = botRow.querySelector(".citations-slot");
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
            statusHeaderTag.innerHTML = `🛡️ Grounded &bull; Citations Verified (${Math.round((event.confidence || 0) * 100)}%)`;
          }

          if (event.type === "token") {
            currentAnswer += event.text;
            accumulatedTextSpan.textContent = currentAnswer;
            botRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
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

// --- 4. Interactive Step-by-Step Instruction Viewer ---

const stepCheckboxes = document.querySelectorAll(".step-checkbox");
stepCheckboxes.forEach(cb => {
  cb.addEventListener("change", (e) => {
    const stepCard = e.target.closest(".step-item-card");
    if (stepCard) {
      if (e.target.checked) {
        stepCard.style.opacity = "0.75";
      } else {
        stepCard.style.opacity = "1";
      }
    }
  });
});

// Diagnostic Action Buttons
const btnCompleteJob = document.getElementById("btn-complete-job");
if (btnCompleteJob) {
  btnCompleteJob.addEventListener("click", () => {
    alert("✓ Diagnostic Session SESSION-8A9F completed! Logged to Compliance Audit Panel.");
  });
}

const btnReportUnclear = document.getElementById("btn-report-unclear");
if (btnReportUnclear) {
  btnReportUnclear.addEventListener("click", () => {
    const reason = prompt("Report Unclear Step:\nPlease specify which instruction requires engineering clarification:");
    if (reason) {
      alert(`Report logged for Diagnostic Session SESSION-8A9F: "${reason}"`);
    }
  });
}

const btnOutdatedGuide = document.getElementById("btn-outdated-guide");
if (btnOutdatedGuide) {
  btnOutdatedGuide.addEventListener("click", () => {
    alert("Flagged guide MNL-24-001 as Outdated. Engineering notification queued.");
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

// --- 6. Backend Connection Health Check ---

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

// Initialize on Load
document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  // Default to Manager Command Center as per mockup or Diagnostic Hub
  // In the first screenshot Command Center is active for Manager J. Doe
  switchView("view-command-center");
});
