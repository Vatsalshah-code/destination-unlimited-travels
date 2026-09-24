// Staff Admin Dashboard Interactivity & Real-Time Management
document.addEventListener("DOMContentLoaded", () => {
  let currentPage = 1;
  let currentSearch = "";
  let currentService = "";
  let currentStatus = "";
  let activeClientId = null;

  // Elements
  const clientTableBody = document.getElementById("clientTableBody");
  const tableLoading = document.getElementById("tableLoading");
  const emptyState = document.getElementById("emptyState");
  const searchInput = document.getElementById("searchInput");
  const serviceFilter = document.getElementById("serviceFilter");
  const statusFilter = document.getElementById("statusFilter");
  const refreshBtn = document.getElementById("refreshBtn");
  const prevPageBtn = document.getElementById("prevPageBtn");
  const nextPageBtn = document.getElementById("nextPageBtn");
  const paginationInfo = document.getElementById("paginationInfo");

  // Metric elements
  const metricTotal = document.getElementById("metricTotal");
  const metricNew = document.getElementById("metricNew");
  const metricUnderReview = document.getElementById("metricUnderReview");
  const metricPendingDocs = document.getElementById("metricPendingDocs");
  const metricCompleted = document.getElementById("metricCompleted");

  // Client Details Modal Elements
  const clientModal = document.getElementById("clientDetailModal");
  const closeClientModal = document.getElementById("closeClientModal");
  const modalClientId = document.getElementById("modalClientId");
  const modalStatusBadge = document.getElementById("modalStatusBadge");
  const modalClientName = document.getElementById("modalClientName");
  const modalClientEmail = document.getElementById("modalClientEmail");
  const modalClientMobile = document.getElementById("modalClientMobile");
  const modalClientDob = document.getElementById("modalClientDob");
  const modalClientCountry = document.getElementById("modalClientCountry");
  const modalClientService = document.getElementById("modalClientService");
  const modalClientAddress = document.getElementById("modalClientAddress");
  const modalClientRefNo = document.getElementById("modalClientRefNo");
  const modalClientSubmitted = document.getElementById("modalClientSubmitted");
  const modalDocList = document.getElementById("modalDocList");
  const modalNotesList = document.getElementById("modalNotesList");
  const modalAuditList = document.getElementById("modalAuditList");
  const modalStatusSelect = document.getElementById("modalStatusSelect");
  const updateStatusBtn = document.getElementById("updateStatusBtn");
  const statusNoteInput = document.getElementById("statusNoteInput");
  const notifyClientCheckbox = document.getElementById("notifyClientCheckbox");
  const addNoteBtn = document.getElementById("addNoteBtn");
  const newNoteText = document.getElementById("newNoteText");
  const downloadAllZipBtn = document.getElementById("downloadAllZipBtn");
  const deleteClientBtn = document.getElementById("deleteClientBtn");
  const whatsappLink = document.getElementById("whatsappLink");
  const telLink = document.getElementById("telLink");
  const openContactModalBtn = document.getElementById("openContactModalBtn");

  // Document Preview Modal Elements
  const previewModal = document.getElementById("previewModal");
  const previewModalTitle = document.getElementById("previewModalTitle");
  const previewContainer = document.getElementById("previewContainer");
  const closePreviewModal = document.getElementById("closePreviewModal");

  // Contact Client Modal
  const contactModal = document.getElementById("contactModal");
  const closeContactModal = document.getElementById("closeContactModal");
  const contactSubject = document.getElementById("contactSubject");
  const contactMessage = document.getElementById("contactMessage");
  const sendContactBtn = document.getElementById("sendContactBtn");

  // Notifications
  const notifBell = document.getElementById("notifBell");
  const notifDropdown = document.getElementById("notifDropdown");
  const notifList = document.getElementById("notifList");
  const markReadBtn = document.getElementById("markReadBtn");
  const notifBadge = document.getElementById("notifBadge");

  // Logout
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await fetch("/api/admin/logout", { method: "POST" });
      window.location.href = "/admin/login";
    });
  }

  // Helper formatting
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  function formatDate(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  function getStatusBadgeClass(status) {
    const slug = status.toLowerCase().replace(/\s+/g, "-");
    return `badge-${slug}`;
  }

  // Load clients table
  async function loadClients() {
    tableLoading.style.display = "block";
    clientTableBody.innerHTML = "";
    emptyState.style.display = "none";

    const params = new URLSearchParams({
      page: currentPage,
      limit: 20
    });
    if (currentSearch) params.append("search", currentSearch);
    if (currentService) params.append("service", currentService);
    if (currentStatus) params.append("status", currentStatus);

    try {
      const res = await fetch(`/api/admin/clients?${params.toString()}`);
      if (res.status === 401) {
        window.location.href = "/admin/login";
        return;
      }
      const data = await res.json();
      tableLoading.style.display = "none";

      if (!data.success || !data.clients || data.clients.length === 0) {
        emptyState.style.display = "block";
        paginationInfo.textContent = "Showing 0 of 0 records";
        prevPageBtn.disabled = true;
        nextPageBtn.disabled = true;
        updateMetrics(data.metrics);
        return;
      }

      updateMetrics(data.metrics);
      renderTableRows(data.clients);

      // Pagination
      paginationInfo.textContent = `Showing ${(data.page - 1) * data.limit + 1} - ${Math.min(data.page * data.limit, data.total)} of ${data.total} records (Page ${data.page}/${data.pages})`;
      prevPageBtn.disabled = data.page <= 1;
      nextPageBtn.disabled = data.page >= data.pages;

    } catch (err) {
      console.error(err);
      tableLoading.style.display = "none";
      emptyState.style.display = "block";
    }
  }

  function updateMetrics(m) {
    if (!m) return;
    if (metricTotal) metricTotal.textContent = m.total_clients || 0;
    if (metricNew) metricNew.textContent = m.new_count || 0;
    if (metricUnderReview) metricUnderReview.textContent = m.under_review || 0;
    if (metricPendingDocs) metricPendingDocs.textContent = m.additional_docs_required || m.documents_pending || 0;
    if (metricCompleted) metricCompleted.textContent = m.completed_count || 0;
  }

  function renderTableRows(clients) {
    clientTableBody.innerHTML = "";
    clients.forEach(c => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><a href="javascript:void(0)" class="client-id-link" data-id="${c.client_id}">${c.client_id}</a></td>
        <td>
          <div style="font-weight:600; color:#0f172a;">${escapeHtml(c.full_name)}</div>
          <div style="font-size:0.75rem; color:#64748b;">${escapeHtml(c.email)}</div>
        </td>
        <td>${escapeHtml(c.mobile)}</td>
        <td><span style="font-weight:500;">${escapeHtml(c.service)}</span></td>
        <td>${escapeHtml(c.country)}</td>
        <td>${formatDate(c.created_at)}</td>
        <td><span class="badge ${getStatusBadgeClass(c.status)}">${c.status}</span></td>
        <td><span style="background:#f1f5f9; padding:0.2rem 0.6rem; border-radius:12px; font-weight:600; font-size:0.75rem;">📁 ${c.doc_count || 0}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm view-client-btn" data-id="${c.client_id}" title="View Details">
            Open Record
          </button>
        </td>
      `;
      clientTableBody.appendChild(tr);
    });

    // Attach listeners
    document.querySelectorAll(".client-id-link, .view-client-btn").forEach(el => {
      el.addEventListener("click", () => {
        const cid = el.getAttribute("data-id");
        openClientDetails(cid);
      });
    });
  }

  // Open Full Client Detail Modal
  async function openClientDetails(clientId) {
    activeClientId = clientId;
    try {
      const res = await fetch(`/api/admin/clients/${clientId}`);
      const data = await res.json();
      if (!data.success) {
        alert("Failed to load client details.");
        return;
      }

      const c = data.client;
      modalClientId.textContent = c.client_id;
      modalStatusBadge.textContent = c.status;
      modalStatusBadge.className = `badge ${getStatusBadgeClass(c.status)}`;
      modalClientName.textContent = c.full_name;
      modalClientEmail.textContent = c.email;
      modalClientMobile.textContent = c.mobile;
      modalClientDob.textContent = c.dob;
      modalClientCountry.textContent = c.country;
      modalClientService.textContent = c.service;
      modalClientAddress.textContent = c.address;
      modalClientRefNo.textContent = c.reference_no || "N/A";
      modalClientSubmitted.textContent = formatDate(c.created_at);
      modalStatusSelect.value = c.status;

      // Contact Links
      const cleanPhone = c.mobile.replace(/[^0-9]/g, "");
      whatsappLink.href = `https://wa.me/${cleanPhone}?text=Hello%20${encodeURIComponent(c.full_name)},%20regarding%20your%20visa%20application%20(${c.client_id}):`;
      telLink.href = `tel:${c.mobile}`;

      // Render Documents
      renderClientDocuments(c.client_id, c.documents || []);

      // Render Notes
      renderClientNotes(c.notes || []);

      // Render Audit Trail
      renderClientAuditLogs(c.audit_logs || []);

      clientModal.classList.add("active");
    } catch (err) {
      console.error(err);
      alert("Error opening client record.");
    }
  }

  function renderClientDocuments(clientId, docs) {
    modalDocList.innerHTML = "";
    if (docs.length === 0) {
      modalDocList.innerHTML = `<div style="color:#64748b; font-size:0.875rem;">No documents uploaded.</div>`;
      return;
    }

    docs.forEach(doc => {
      const card = document.createElement("div");
      card.className = "doc-item-card";
      card.innerHTML = `
        <div>
          <div class="doc-item-header">
            <span class="doc-item-name">${escapeHtml(doc.category_label)}</span>
            <span class="badge badge-submitted" style="font-size:0.7rem;">Verified</span>
          </div>
          <div class="doc-item-file" title="${escapeHtml(doc.original_filename)}">
            📄 ${escapeHtml(doc.original_filename)}
          </div>
          <div style="font-size:0.75rem; color:#64748b;">
            Size: ${formatBytes(doc.file_size)} • ${formatDate(doc.uploaded_at)}
          </div>
        </div>
        <div class="doc-item-actions">
          <button class="btn btn-secondary btn-sm preview-doc-btn" data-client="${clientId}" data-doc="${doc.id}" data-type="${doc.mime_type}" data-name="${escapeHtml(doc.original_filename)}">
            👁 View
          </button>
          <a href="/api/admin/clients/${clientId}/documents/${doc.id}/download" class="btn btn-primary btn-sm" download>
            ⬇ Download
          </a>
        </div>
      `;
      modalDocList.appendChild(card);
    });

    // Bind preview buttons
    modalDocList.querySelectorAll(".preview-doc-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const cId = btn.getAttribute("data-client");
        const docId = btn.getAttribute("data-doc");
        const mime = btn.getAttribute("data-type");
        const name = btn.getAttribute("data-name");
        openDocumentPreview(cId, docId, mime, name);
      });
    });
  }

  function openDocumentPreview(clientId, docId, mime, filename) {
    previewModalTitle.textContent = `Viewing: ${filename}`;
    previewContainer.innerHTML = "";

    const viewUrl = `/api/admin/clients/${clientId}/documents/${docId}/view`;

    if (mime.includes("pdf")) {
      previewContainer.innerHTML = `
        <iframe src="${viewUrl}" style="width:100%; height:550px; border:none; border-radius:8px;"></iframe>
      `;
    } else if (mime.startsWith("image/")) {
      previewContainer.innerHTML = `
        <div style="text-align:center; padding:1rem; max-height:550px; overflow:auto;">
          <img src="${viewUrl}" alt="${filename}" style="max-width:100%; max-height:500px; border-radius:8px; box-shadow:var(--shadow-md);">
        </div>
      `;
    } else {
      previewContainer.innerHTML = `
        <div style="text-align:center; padding:2rem;">
          <p>This file type cannot be previewed directly in the browser.</p>
          <a href="/api/admin/clients/${clientId}/documents/${docId}/download" class="btn btn-primary" style="margin-top:1rem;">
            Download File
          </a>
        </div>
      `;
    }

    previewModal.classList.add("active");
  }

  function renderClientNotes(notes) {
    modalNotesList.innerHTML = "";
    if (notes.length === 0) {
      modalNotesList.innerHTML = `<div style="color:#94a3b8; font-size:0.8rem; font-style:italic;">No internal notes yet.</div>`;
      return;
    }
    notes.forEach(n => {
      const b = document.createElement("div");
      b.className = "note-bubble";
      b.innerHTML = `
        <div class="note-header">
          <strong style="color:#0f172a;">${escapeHtml(n.author_name)}</strong>
          <span>${formatDate(n.created_at)}</span>
        </div>
        <div style="color:#334155;">${escapeHtml(n.note_text)}</div>
      `;
      modalNotesList.appendChild(b);
    });
  }

  function renderClientAuditLogs(logs) {
    modalAuditList.innerHTML = "";
    if (logs.length === 0) {
      modalAuditList.innerHTML = `<div style="color:#94a3b8; font-size:0.8rem;">No activity logged.</div>`;
      return;
    }
    logs.forEach(l => {
      const row = document.createElement("div");
      row.style.fontSize = "0.75rem";
      row.style.padding = "0.4rem 0";
      row.style.borderBottom = "1px solid #f1f5f9";
      row.style.display = "flex";
      row.style.justifyContent = "space-between";
      row.innerHTML = `
        <div>
          <span style="font-weight:600; color:#1e40af;">[${l.action}]</span>
          <span>${escapeHtml(l.details || "")}</span>
          <span style="color:#94a3b8;">(${l.actor_identifier})</span>
        </div>
        <span style="color:#64748b; white-space:nowrap; margin-left:0.5rem;">${formatDate(l.created_at)}</span>
      `;
      modalAuditList.appendChild(row);
    });
  }

  // Update Status
  if (updateStatusBtn) {
    updateStatusBtn.addEventListener("click", async () => {
      if (!activeClientId) return;
      const newStatus = modalStatusSelect.value;
      const customNote = statusNoteInput.value.trim();
      const notify = notifyClientCheckbox.checked;

      updateStatusBtn.disabled = true;
      updateStatusBtn.textContent = "Updating...";

      try {
        const res = await fetch(`/api/admin/clients/${activeClientId}/status`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status: newStatus,
            custom_note: customNote,
            notify_client: notify
          })
        });

        const data = await res.json();
        if (data.success) {
          statusNoteInput.value = "";
          alert(`Status successfully updated to '${newStatus}'.`);
          openClientDetails(activeClientId);
          loadClients();
        } else {
          alert(data.detail || "Failed to update status.");
        }
      } catch (err) {
        alert("Network error updating status.");
      } finally {
        updateStatusBtn.disabled = false;
        updateStatusBtn.textContent = "Update Status";
      }
    });
  }

  // Add Internal Note
  if (addNoteBtn) {
    addNoteBtn.addEventListener("click", async () => {
      if (!activeClientId) return;
      const noteText = newNoteText.value.trim();
      if (!noteText) {
        alert("Please enter note text.");
        return;
      }

      addNoteBtn.disabled = true;
      try {
        const res = await fetch(`/api/admin/clients/${activeClientId}/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ note_text: noteText })
        });
        const data = await res.json();
        if (data.success) {
          newNoteText.value = "";
          openClientDetails(activeClientId);
        } else {
          alert(data.detail || "Failed to add note.");
        }
      } catch (err) {
        alert("Error saving note.");
      } finally {
        addNoteBtn.disabled = false;
      }
    });
  }

  // Download All as ZIP
  if (downloadAllZipBtn) {
    downloadAllZipBtn.addEventListener("click", () => {
      if (!activeClientId) return;
      window.location.href = `/api/admin/clients/${activeClientId}/download-all-zip`;
    });
  }

  // Delete Client Record
  if (deleteClientBtn) {
    deleteClientBtn.addEventListener("click", async () => {
      if (!activeClientId) return;
      const confirmDelete = confirm(`Are you sure you want to permanently delete client ${activeClientId}?\nThis will purge all personal data and securely wipe all uploaded files from storage.`);
      if (!confirmDelete) return;

      try {
        const res = await fetch(`/api/admin/clients/${activeClientId}`, { method: "DELETE" });
        const data = await res.json();
        if (data.success) {
          alert("Client record and all files deleted permanently.");
          clientModal.classList.remove("active");
          loadClients();
        } else {
          alert(data.detail || "Error deleting record.");
        }
      } catch (err) {
        alert("Network error.");
      }
    });
  }

  // Contact Modal
  if (openContactModalBtn) {
    openContactModalBtn.addEventListener("click", () => {
      contactSubject.value = `Update on your Visa Application (${activeClientId})`;
      contactMessage.value = "";
      contactModal.classList.add("active");
    });
  }

  if (sendContactBtn) {
    sendContactBtn.addEventListener("click", async () => {
      if (!activeClientId) return;
      const subj = contactSubject.value.trim();
      const msg = contactMessage.value.trim();
      if (!subj || !msg) {
        alert("Please enter subject and message.");
        return;
      }

      sendContactBtn.disabled = true;
      try {
        const res = await fetch(`/api/admin/contact-client/${activeClientId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subject: subj, message: msg, channel: "EMAIL" })
        });
        const data = await res.json();
        if (data.success) {
          alert("Message dispatched to client.");
          contactModal.classList.remove("active");
          openClientDetails(activeClientId);
        } else {
          alert(data.detail || "Failed to send message.");
        }
      } catch (err) {
        alert("Error sending message.");
      } finally {
        sendContactBtn.disabled = false;
      }
    });
  }

  // Close modals
  if (closeClientModal) closeClientModal.addEventListener("click", () => clientModal.classList.remove("active"));
  if (closePreviewModal) closePreviewModal.addEventListener("click", () => previewModal.classList.remove("active"));
  if (closeContactModal) closeContactModal.addEventListener("click", () => contactModal.classList.remove("active"));

  // Notifications Bell
  if (notifBell) {
    notifBell.addEventListener("click", (e) => {
      e.stopPropagation();
      notifDropdown.style.display = notifDropdown.style.display === "block" ? "none" : "block";
    });

    document.addEventListener("click", () => {
      if (notifDropdown) notifDropdown.style.display = "none";
    });

    if (notifDropdown) {
      notifDropdown.addEventListener("click", (e) => e.stopPropagation());
    }
  }

  if (markReadBtn) {
    markReadBtn.addEventListener("click", async () => {
      await fetch("/api/admin/notifications/mark-read", { method: "POST" });
      if (notifBadge) notifBadge.style.display = "none";
      if (notifList) notifList.innerHTML = `<div style="padding:1rem; text-align:center; color:#94a3b8; font-size:0.8rem;">No unread notifications</div>`;
    });
  }

  // Search & Filters
  let searchDebounce;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      currentSearch = e.target.value.trim();
      currentPage = 1;
      loadClients();
    }, 300);
  });

  serviceFilter.addEventListener("change", (e) => {
    currentService = e.target.value;
    currentPage = 1;
    loadClients();
  });

  statusFilter.addEventListener("change", (e) => {
    currentStatus = e.target.value;
    currentPage = 1;
    loadClients();
  });

  refreshBtn.addEventListener("click", () => {
    loadClients();
  });

  prevPageBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      loadClients();
    }
  });

  nextPageBtn.addEventListener("click", () => {
    currentPage++;
    loadClients();
  });

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Initial table load
  loadClients();
});
