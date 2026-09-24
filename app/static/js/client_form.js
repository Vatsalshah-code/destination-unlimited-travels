// Client Intake & Document Upload Interactive Script
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("clientIntakeForm");
  const submitBtn = document.getElementById("submitBtn");
  const submitSpinner = document.getElementById("submitSpinner");
  const btnText = document.getElementById("btnText");
  const errorAlert = document.getElementById("errorAlert");
  const errorText = document.getElementById("errorText");

  // Single file input slots configuration
  const singleSlots = [
    { inputId: "passportInput", slotId: "passportSlot", boxId: "passportPreview", nameId: "passportName", metaId: "passportMeta", removeId: "passportRemove" },
    { inputId: "aadhaarInput", slotId: "aadhaarSlot", boxId: "aadhaarPreview", nameId: "aadhaarName", metaId: "aadhaarMeta", removeId: "aadhaarRemove" },
    { inputId: "panInput", slotId: "panSlot", boxId: "panPreview", nameId: "panName", metaId: "panMeta", removeId: "panRemove" },
    { inputId: "photoInput", slotId: "photoSlot", boxId: "photoPreview", nameId: "photoName", metaId: "photoMeta", removeId: "photoRemove" },
    { inputId: "bankDocsInput", slotId: "bankDocsSlot", boxId: "bankDocsPreview", nameId: "bankDocsName", metaId: "bankDocsMeta", removeId: "bankDocsRemove" },
    { inputId: "prevVisaInput", slotId: "prevVisaSlot", boxId: "prevVisaPreview", nameId: "prevVisaName", metaId: "prevVisaMeta", removeId: "prevVisaRemove" }
  ];

  function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  }

  function validateFile(file) {
    const validExtensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      return `Invalid format '${ext}'. Allowed formats: PDF, JPG, PNG, WEBP.`;
    }
    const maxBytes = 10 * 1024 * 1024; // 10MB
    if (file.size > maxBytes) {
      return `File exceeds 10MB limit (${formatBytes(file.size)}).`;
    }
    return null;
  }

  // Setup single file handlers
  singleSlots.forEach(slot => {
    const input = document.getElementById(slot.inputId);
    const container = document.getElementById(slot.slotId);
    const box = document.getElementById(slot.boxId);
    const nameEl = document.getElementById(slot.nameId);
    const metaEl = document.getElementById(slot.metaId);
    const removeBtn = document.getElementById(slot.removeId);

    if (!input) return;

    input.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const error = validateFile(file);
      if (error) {
        alert(error);
        input.value = "";
        return;
      }

      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      nameEl.textContent = file.name;
      metaEl.textContent = `${formatBytes(file.size)} • Uploaded today at ${now} • Ready`;
      container.classList.add("has-file");
      box.style.display = "flex";
    });

    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        input.value = "";
        container.classList.remove("has-file");
        box.style.display = "none";
      });
    }
  });

  // Multiple Supporting Documents handler
  const supInput = document.getElementById("supDocsInput");
  const supListContainer = document.getElementById("supDocsList");
  let supportingFilesStore = [];

  if (supInput && supListContainer) {
    supInput.addEventListener("change", (e) => {
      const files = Array.from(e.target.files);
      files.forEach(file => {
        const error = validateFile(file);
        if (error) {
          alert(`${file.name}: ${error}`);
          return;
        }
        supportingFilesStore.push(file);
      });
      renderSupportingFiles();
      supInput.value = ""; // reset so same file can be picked if needed
    });

    function renderSupportingFiles() {
      supListContainer.innerHTML = "";
      if (supportingFilesStore.length === 0) {
        document.getElementById("supSlot").classList.remove("has-file");
        return;
      }

      document.getElementById("supSlot").classList.add("has-file");
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      supportingFilesStore.forEach((file, idx) => {
        const item = document.createElement("div");
        item.className = "file-preview-box";
        item.style.display = "flex";
        item.style.marginTop = "0.5rem";
        item.innerHTML = `
          <div class="file-info-text">
            <span class="file-name-text">${escapeHtml(file.name)}</span>
            <span class="file-meta-text">${formatBytes(file.size)} • Uploaded at ${now} • Ready</span>
          </div>
          <button type="button" class="file-remove-btn" title="Remove file" data-index="${idx}">
            ✕
          </button>
        `;
        supListContainer.appendChild(item);
      });

      // Bind remove buttons
      supListContainer.querySelectorAll(".file-remove-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
          const idx = parseInt(e.currentTarget.getAttribute("data-index"));
          supportingFilesStore.splice(idx, 1);
          renderSupportingFiles();
        });
      });
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function showError(msg) {
    errorText.textContent = msg;
    errorAlert.style.display = "flex";
    errorAlert.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function hideError() {
    errorAlert.style.display = "none";
  }

  // Form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideError();

    // Check privacy consent
    const consent = document.getElementById("consentCheckbox");
    if (!consent || !consent.checked) {
      showError("Please check the consent declaration to proceed with secure document submission.");
      return;
    }

    // Verify required inputs
    const fullName = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const mobile = document.getElementById("mobile").value.trim();
    const dob = document.getElementById("dob").value.trim();
    const address = document.getElementById("address").value.trim();
    const service = document.getElementById("service").value.trim();
    const country = document.getElementById("country").value.trim();
    const refNo = document.getElementById("referenceNo").value.trim();

    if (!fullName || !email || !mobile || !dob || !address || !service || !country) {
      showError("Please fill in all required fields marked with *.");
      return;
    }

    // Check if at least one document is selected
    const passportFile = document.getElementById("passportInput").files[0];
    const aadhaarFile = document.getElementById("aadhaarInput").files[0];
    const panFile = document.getElementById("panInput").files[0];
    const photoFile = document.getElementById("photoInput").files[0];
    const bankFile = document.getElementById("bankDocsInput").files[0];
    const prevVisaFile = document.getElementById("prevVisaInput").files[0];

    const hasAnyDoc = passportFile || aadhaarFile || panFile || photoFile || bankFile || prevVisaFile || supportingFilesStore.length > 0;
    if (!hasAnyDoc) {
      showError("Please upload at least one mandatory document (such as Passport or Aadhaar Card) to proceed.");
      return;
    }

    // Prepare FormData
    const formData = new FormData();
    formData.append("full_name", fullName);
    formData.append("email", email);
    formData.append("mobile", mobile);
    formData.append("dob", dob);
    formData.append("address", address);
    formData.append("service", service);
    formData.append("country", country);
    formData.append("reference_no", refNo);
    formData.append("consent_given", "true");

    if (passportFile) formData.append("passport", passportFile);
    if (aadhaarFile) formData.append("aadhaar", aadhaarFile);
    if (panFile) formData.append("pan", panFile);
    if (photoFile) formData.append("photo", photoFile);
    if (bankFile) formData.append("bank_docs", bankFile);
    if (prevVisaFile) formData.append("previous_visa", prevVisaFile);

    supportingFilesStore.forEach(file => {
      formData.append("supporting_docs", file);
    });

    // Loading State
    submitBtn.disabled = true;
    submitSpinner.style.display = "inline-block";
    btnText.textContent = "Encrypting & Uploading Documents...";

    try {
      const response = await fetch("/api/submit-documents", {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || "Failed to submit documents.");
      }

      // Success: redirect to confirmation
      window.location.href = data.redirect_url;
    } catch (err) {
      showError(err.message || "An unexpected network error occurred. Please try again.");
      submitBtn.disabled = false;
      submitSpinner.style.display = "none";
      btnText.textContent = "Submit All Documents Securely";
    }
  });
});
