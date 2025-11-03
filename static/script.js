document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("predictionForm");
  const alertSection = document.querySelector(".alert-section");
  const riskText = document.getElementById("riskText");
  const downloadBtn = document.querySelector(".download-btn");
  const pdfInput = document.getElementById("pdfInput");
  const uploadArea = document.getElementById("uploadArea");
  const uploadStatus = document.getElementById("uploadStatus");

  // handle pdf upload area
  uploadArea.addEventListener("click", () => pdfInput.click());
  pdfInput.addEventListener("change", handleFileUpload);

  // handle prediction form submit
  form.addEventListener("submit", handlePredictionSubmit);

  // fetch risk history on page load
  fetchRiskHistory();

  // handle pdf data extraction
  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    uploadStatus.textContent = "extracting data...";
    uploadStatus.className = "upload-status loading";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/extract_data", { method: "POST", body: formData });
      if (!res.ok) throw new Error("server returned " + res.status);

      const data = await res.json();
      for (const [key, value] of Object.entries(data)) {
        const input = document.querySelector(`[name="${key}"]`);
        if (!input || value === "") continue;
        if (input.type === "radio") {
          const radio = document.querySelector(`[name="${key}"][value="${value}"]`);
          if (radio) radio.checked = true;
        } else input.value = value;
      }

      uploadStatus.textContent = "data extracted successfully";
      uploadStatus.className = "upload-status success";
    } catch (err) {
      uploadStatus.textContent = "failed to extract data. try again.";
      uploadStatus.className = "upload-status error";
    }
  }

  // handle prediction form submit
  async function handlePredictionSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    let allValid = true;

    const requiredFields = form.querySelectorAll("[required]");
    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        field.classList.add("warning-border");
        allValid = false;
      } else {
        field.classList.remove("warning-border");
      }
    });

    if (!allValid) {
      alert("please fill all required fields before predicting.");
      return;
    }

    try {
      const response = await fetch("/prediction_model", {
        method: "POST",
        body: formData
      });
      if (!response.ok) throw new Error("network error while predicting");

      const data = await response.json();
      const { risk, percentage } = data;

      // show result alert
      alertSection.classList.remove("hidden", "high-risk", "low-risk", "moderate-risk", "show");
      void alertSection.offsetWidth;

      if (risk === "High Risk") alertSection.classList.add("high-risk");
      else if (risk === "Moderate Risk") alertSection.classList.add("moderate-risk");
      else alertSection.classList.add("low-risk");

      riskText.textContent = `${risk} | ${percentage}%`;
      alertSection.classList.add("show");
      window.scrollTo({ top: 0, behavior: "smooth" });
      downloadBtn.style.display = "flex";

      renderCharts(formData);

      // update risk trend after prediction
      fetchRiskHistory();
    } catch (err) {
      console.error(err);
      alertSection.classList.remove("hidden", "high-risk", "low-risk");
      alertSection.classList.add("show");
      riskText.textContent = "error: unable to fetch prediction.";
    }
  }

  // get risk history data
  async function fetchRiskHistory() {
    try {
      const response = await fetch("/risk_history");
      const data = await response.json();
      if (!data.error) renderRiskCharts(data.labels, data.data);
    } catch (err) {
      console.error("error fetching risk history:", err);
    }
  }

  // show small stats and charts after prediction
  function renderCharts(formData) {
    document.getElementById("placeholderChartContainer").classList.add("hidden-chart");
    document.getElementById("insightContainer").classList.remove("hidden-chart");

    const weight = parseFloat(formData.get("weight"));
    const height = parseFloat(formData.get("height")) / 100;
    const ap_hi = parseFloat(formData.get("ap_hi"));
    const ap_lo = parseFloat(formData.get("ap_lo"));
    const chol = parseFloat(formData.get("cholesterol"));
    const gluc = parseFloat(formData.get("glucose"));
    const smoke = parseInt(formData.get("smoke"));
    const alco = parseInt(formData.get("alco"));
    const active = parseInt(formData.get("active"));

    const bmi = (weight / (height * height)).toFixed(1);
    const pulsePressure = ap_hi - ap_lo;
    const map = ((2 * ap_lo + ap_hi) / 3).toFixed(1);

    const bmiCategory =
      bmi < 18.5 ? "Underweight" :
      bmi < 25 ? "Normal" :
      bmi < 30 ? "Overweight" : "Obese";

    document.querySelector("#bmiCard span").innerHTML = `${bmi} <br><small>(${bmiCategory})</small>`;
    document.querySelector("#pulseCard span").textContent = `${pulsePressure} mmHg`;
    document.querySelector("#mapCard span").textContent = `${map} mmHg`;

    // clear old charts
    Object.values(Chart.instances).forEach(chart => chart.destroy());

    const commonColors = ["#b3e5fc", "#fff9c4", "#c8e6c9"];

    new Chart(document.getElementById("riskFactorChart"), {
      type: "bar",
      data: {
        labels: ["Smoking", "Alcohol", "Cholesterol", "Glucose", "Activity"],
        datasets: [{
          label: "Risk Contribution",
          data: [smoke * 10, alco * 10, chol * 15, gluc * 15, (1 - active) * 10],
          backgroundColor: commonColors
        }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });

    new Chart(document.getElementById("healthRadarChart"), {
      type: "radar",
      data: {
        labels: ["BMI", "Pulse", "Chol", "Gluc", "MAP"],
        datasets: [{
          label: "Health Radar",
          data: [
            (bmi / 30) * 100,
            (pulsePressure / 100) * 100,
            (chol / 3) * 100,
            (gluc / 3) * 100,
            ((map - 60) / 70) * 100
          ],
          backgroundColor: "rgba(234, 40, 49, 0.1)",
          borderColor: "#EA2831",
          pointBackgroundColor: "#EA2831"
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true } } }
    });
  }

  // show risk change chart
  function renderRiskCharts(labels, dataPoints) {
    const placeholderCtx = document.getElementById("placeholderLineChart").getContext("2d");
    new Chart(placeholderCtx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Risk Level Over Time",
          data: dataPoints,
          borderColor: "#4fa3f7",
          fill: false,
          tension: 0.3
        }]
      },
      options: { responsive: true }
    });

    const riskCtx = document.getElementById("riskOverTimeChart").getContext("2d");
    new Chart(riskCtx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Risk Score",
          data: dataPoints,
          borderColor: "#EA2831",
          backgroundColor: "rgba(234, 40, 49, 0.1)",
          fill: true,
          tension: 0.4
        }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });
  }
});
