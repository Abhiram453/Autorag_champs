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

// --- 3. Live RAG Diagnostic Hub Logic ---

/**
 * Sends POST /query request to backend RAG API.
 * @param {string} question - Technician query
 * @returns {Promise<Object>} - RAG response
 */
async function askQuestion(question) {
  const endpoint = `${RAG_API_URL}/query`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: question,
      history: conversationHistory
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `RAG query failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Component: Answer({ result })
 * Displays the answer first, then renders retrieved sources with verified chunk_id.
 * @param {Object} props - { result: QueryResponse }
 * @returns {HTMLElement}
 */
function Answer({ result }) {
  const isRefusal = result.status === "refused_weak_context";
  const confidencePercent = Math.round((result.confidence || result.top_score || 0) * 100);

  const row = document.createElement("div");
  row.className = "chat-bubble-row bot";

  let sourcesHtml = "";
  if (result.sources && result.sources.length > 0) {
    const sourceItems = result.sources.map((s, idx) => {
      const scoreTag = s.score ? `(${Math.round(s.score * 100)}% match)` : "";
      return `
        <li style="margin-bottom: 6px; padding: 6px 10px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;">
          <div style="font-weight: 600; color: #0f172a; display: flex; justify-content: space-between;">
            <span>[${idx + 1}] ${escapeHtml(s.source)} ${s.chunk_id ? `<code>(${escapeHtml(s.chunk_id)})</code>` : ""}</span>
            <span style="font-size: 11px; color: #0284c7;">${scoreTag}</span>
          </div>
          <div style="font-size: 11.5px; color: #64748b; margin-top: 2px;">
            ${escapeHtml(s.section || "General")} &bull; ${escapeHtml(s.text ? s.text.substring(0, 110) + "..." : "")}
          </div>
        </li>
      `;
    }).join("");

    sourcesHtml = `
      <div style="margin-top: 12px; padding-top: 10px; border-top: 1px dashed #cbd5e1;">
        <div style="font-weight: 700; font-size: 12px; color: #475569; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em;">
          📚 Retrieved Sources (${result.sources.length} Documents)
        </div>
        <ul style="list-style: none; padding: 0;">
          ${sourceItems}
        </ul>
      </div>
    `;
  } else if (isRefusal) {
    sourcesHtml = `
      <div style="margin-top: 10px; padding: 8px 12px; background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 4px; font-size: 12px; color: #b45309;">
        ⚠️ <strong>Zero Hallucination Guardrail:</strong> Context similarity below minimum threshold (${confidencePercent}%). System refused answer.
      </div>
    `;
  }

  row.innerHTML = `
    <div class="chat-avatar">AI</div>
    <div class="chat-bubble-content">
      <div style="font-size: 11px; font-weight: 700; color: ${isRefusal ? '#b45309' : '#0284c7'}; margin-bottom: 4px; text-transform: uppercase;">
        ${isRefusal ? '🛡️ Guardrail Refusal' : `🛡️ Grounded Diagnostic Response (${confidencePercent}% Confidence)`}
      </div>
      <div>${escapeHtml(result.answer)}</div>
      ${sourcesHtml}
    </div>
  `;

  return row;
}

/**
 * Handles RAG form submission with clear loading and error feedback.
 * @param {string} question
 */
async function handleSubmit(question) {
  const trimmed = question.trim();
  if (!trimmed || isQueryLoading) return;

  isQueryLoading = true;
  hubQueryInput.value = "";
  hubQuerySubmit.disabled = true;

  // 1. Render User Message
  const userRow = document.createElement("div");
  userRow.className = "chat-bubble-row user";
  userRow.innerHTML = `
    <div class="chat-avatar user-avatar">Tech</div>
    <div class="chat-bubble-content">${escapeHtml(trimmed)}</div>
  `;
  hubChatStream.appendChild(userRow);
  userRow.scrollIntoView({ behavior: "smooth", block: "nearest" });

  // 2. Render Thinking Indicator
  const thinkingRow = document.createElement("div");
  thinkingRow.className = "chat-bubble-row bot";
  thinkingRow.id = "thinking-indicator";
  thinkingRow.innerHTML = `
    <div class="chat-avatar">AI</div>
    <div class="chat-bubble-content" style="display: flex; align-items: center; gap: 8px; color: var(--text-muted);">
      <div style="width: 14px; height: 14px; border: 2px solid #0066ff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <span>Querying model-specific manuals & verifying citations...</span>
    </div>
  `;
  hubChatStream.appendChild(thinkingRow);
  thinkingRow.scrollIntoView({ behavior: "smooth", block: "nearest" });

  try {
    const result = await askQuestion(trimmed);
    thinkingRow.remove();

    const answerElement = Answer({ result });
    hubChatStream.appendChild(answerElement);
    answerElement.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Update history
    conversationHistory.push({ role: "user", content: trimmed });
    conversationHistory.push({ role: "assistant", content: result.answer });
  } catch (err) {
    thinkingRow.remove();
    const errorRow = document.createElement("div");
    errorRow.className = "chat-bubble-row bot";
    errorRow.innerHTML = `
      <div class="chat-avatar" style="background:#ef4444;">✕</div>
      <div class="chat-bubble-content" style="background:#fef2f2; border: 1px solid #fecaca; color:#b91c1c;">
        <strong>API Error:</strong> ${escapeHtml(err.message || "Failed to reach RAG backend service.")}
      </div>
    `;
    hubChatStream.appendChild(errorRow);
    errorRow.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } finally {
    isQueryLoading = false;
    hubQuerySubmit.disabled = false;
    hubQueryInput.focus();
  }
}

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
