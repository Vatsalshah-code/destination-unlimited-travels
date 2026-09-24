// Client Status Tracking Script
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("trackForm");
  const trackBtn = document.getElementById("trackBtn");
  const trackSpinner = document.getElementById("trackSpinner");
  const resultCard = document.getElementById("resultCard");
  const errorAlert = document.getElementById("errorAlert");
  const errorText = document.getElementById("errorText");

  // Output fields
  const outClientId = document.getElementById("outClientId");
  const outClientName = document.getElementById("outClientName");
  const outService = document.getElementById("outService");
  const outCountry = document.getElementById("outCountry");
  const outStatus = document.getElementById("outStatus");
  const outSubmitted = document.getElementById("outSubmitted");
  const outUpdated = document.getElementById("outUpdated");
  const outDocCount = document.getElementById("outDocCount");
  const docsList = document.getElementById("docsList");

  // Timeline steps
  const stepSubmitted = document.getElementById("stepSubmitted");
  const stepReview = document.getElementById("stepReview");
  const stepProcessing = document.getElementById("stepProcessing");
  const stepCompleted = document.getElementById("stepCompleted");

  function formatDate(isoStr) {
    if (!isoStr) return "-";
    const d = new Date(isoStr);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  function updateTimeline(status) {
    // Reset steps
    [stepSubmitted, stepReview, stepProcessing, stepCompleted].forEach(s => {
      if (s) {
        s.classList.remove("active", "current");
      }
    });

    stepSubmitted.classList.add("active");

    if (status === "Under Review" || status === "Documents Pending" || status === "Additional Documents Required") {
      stepReview.classList.add("active", "current");
    } else if (status === "Submitted") {
      stepReview.classList.add("active");
      stepProcessing.classList.add("active", "current");
    } else if (status === "Completed") {
      stepReview.classList.add("active");
      stepProcessing.classList.add("active");
      stepCompleted.classList.add("active", "current");
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorAlert.style.display = "none";
    resultCard.style.display = "none";

    const clientId = document.getElementById("trackClientId").value.trim();
    const contact = document.getElementById("trackContact").value.trim();

    if (!clientId || !contact) {
      errorText.textContent = "Please enter both Client ID and Registered Mobile / Email.";
      errorAlert.style.display = "block";
      return;
    }

    trackBtn.disabled = true;
    trackSpinner.style.display = "inline-block";

    try {
      const res = await fetch("/api/track-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, contact_identifier: contact })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Unable to find application. Please check your details.");
      }

      outClientId.textContent = data.client_id;
      outClientName.textContent = data.full_name;
      outService.textContent = data.service;
      outCountry.textContent = data.country;
      outStatus.textContent = data.status;
      outStatus.className = `badge badge-${data.status.toLowerCase().replace(/\s+/g, "-")}`;
      outSubmitted.textContent = formatDate(data.submitted_at);
      outUpdated.textContent = formatDate(data.updated_at);
      outDocCount.textContent = data.documents_count;

      updateTimeline(data.status);

      // Render documents summary
      docsList.innerHTML = "";
      if (data.documents_summary && data.documents_summary.length > 0) {
        data.documents_summary.forEach(d => {
          const row = document.createElement("div");
          row.style.padding = "0.5rem 0";
          row.style.borderBottom = "1px solid #f1f5f9";
          row.style.display = "flex";
          row.style.justifyContent = "space-between";
          row.style.alignItems = "center";
          row.style.fontSize = "0.85rem";
          row.innerHTML = `
            <div>
              <strong>${d.category_label}</strong>
              <div style="font-size:0.75rem; color:#64748b;">${d.original_filename}</div>
            </div>
            <span class="badge badge-completed" style="font-size:0.7rem;">Verified on Server</span>
          `;
          docsList.appendChild(row);
        });
      }

      resultCard.style.display = "block";
      resultCard.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
      errorText.textContent = err.message;
      errorAlert.style.display = "block";
    } finally {
      trackBtn.disabled = false;
      trackSpinner.style.display = "none";
    }
  });
});
