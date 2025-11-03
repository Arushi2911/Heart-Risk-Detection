document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("predictionForm");
  const alertSection = document.querySelector(".alert-section");
  const riskText = document.getElementById("riskText");
  const downloadBtn = document.querySelector(".download-btn");
  const pdfInput = document.getElementById('pdfInput');
  const uploadArea = document.getElementById('uploadArea');
  const uploadStatus = document.getElementById('uploadStatus');

  uploadArea.addEventListener('click', () => pdfInput.click());
  pdfInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    uploadStatus.textContent = "Extracting data...";
    uploadStatus.className = "upload-status loading";

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/extract_data', {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Server returned ' + res.status);
      const data = await res.json();
      

      for (const [key, value] of Object.entries(data)) {
        const input = document.querySelector(`[name="${key}"]`);
        if (!input || value === '') continue;

        if (input.type === 'radio') {
          const radio = document.querySelector(`[name="${key}"][value="${value}"]`);
          if (radio) radio.checked = true;
        } else {
          input.value = value;
        }
      }


      uploadStatus.textContent = "Data extracted successfully";
      uploadStatus.className = "upload-status success";
    } catch (err) {
      uploadStatus.textContent = "Failed to extract data. Try again.";
      uploadStatus.className = "upload-status error";
    }
  });


  downloadBtn.style.display = "none";
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const formData = new FormData(form);
  
    try {
      const response = await fetch("/prediction_model", { 
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      const { risk, percentage, labels, percentages } = data;

  
      alertSection.classList.remove("hidden", "high-risk", "low-risk", "moderate-risk", "show");
      void alertSection.offsetWidth; // reflow
      if (risk === "High Risk") {
        alertSection.classList.add("high-risk");
      } else if (risk === "Moderate Risk") {
        alertSection.classList.add("moderate-risk");
      } else {
        alertSection.classList.add("low-risk");
      }

      riskText.textContent = `${risk} | ${percentage}%`;
      alertSection.classList.add("show");
      window.scrollTo({ top: 0, behavior: "smooth" });
      downloadBtn.style.display = "flex";
  
      renderCharts(formData);
  
    } catch (err) {
      console.error(err);
      riskText.textContent = "Error: Unable to fetch prediction.";
      alertSection.classList.remove("hidden","high-risk","low-risk");
      alertSection.classList.add("show");
    }
  });  

function renderCharts(formData) {
  document.getElementById('placeholderChartContainer').classList.add('hidden-chart');
  document.getElementById('insightContainer').classList.remove('hidden-chart');

  const weight = parseFloat(formData.get('weight'));
  const height = parseFloat(formData.get('height')) / 100;
  const ap_hi = parseFloat(formData.get('ap_hi'));
  const ap_lo = parseFloat(formData.get('ap_lo'));
  const chol = parseFloat(formData.get('cholesterol'));
  const gluc = parseFloat(formData.get('glucose'));
  const smoke = parseInt(formData.get('smoke'));
  const alco = parseInt(formData.get('alco'));
  const active = parseInt(formData.get('active'));

  const bmi = (weight / (height * height)).toFixed(1);
  const pulsePressure = ap_hi - ap_lo;
  const map = ((2 * ap_lo + ap_hi) / 3).toFixed(1);

  // get BMI category
  function getBmiCategory(bmi) {
    if (bmi < 18.5) return "Underweight";
    if (bmi < 25) return "Normal";
    if (bmi < 30) return "Overweight";
    return "Obese";
  }

  const bmiCategory = getBmiCategory(bmi);

  document.querySelector('#bmiCard span').innerHTML = `${bmi} <br><small>(${bmiCategory})</small>`;
  document.querySelector('#pulseCard span').textContent = `${pulsePressure} mmHg`;
  document.querySelector('#mapCard span').textContent = `${map} mmHg`;

  Chart.helpers.each(Chart.instances, function (instance) {
    instance.destroy();
  });

  const commonColors = ['#b3e5fc', '#fff9c4', '#c8e6c9']; 

  // Risk factor over time line chart after prediction
  new Chart(document.getElementById('riskOverTimeChart'), {
    type: 'line',
    data: {
      labels: ['2019', '2020', '2021', '2022', '2023', '2024'],
      datasets: [{
        label: 'Risk Score',
        data: [60, 62, 59, 65, 63, 61],
        borderColor: '#EA2831',
        backgroundColor: 'rgba(234, 40, 49, 0.1)',
        fill: true,
        tension: 0.4
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });

  // Risk contribution bar chart - shows how much each factor contributed to risk
  new Chart(document.getElementById('riskFactorChart'), {
    type: 'bar',
    data: {
      labels: ['Smoking', 'Alcohol', 'Cholesterol', 'Glucose', 'Activity'],
      datasets: [{
        label: 'Risk Contribution',
        data: [smoke * 10, alco * 10, chol * 15, gluc * 15, (1 - active) * 10],
        backgroundColor: commonColors
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });

  // Health Radar chart - shows how much deviation from normal is there for diffrent aspects
  new Chart(document.getElementById('healthRadarChart'), {
    type: 'radar',
    data: {
      labels: ['BMI', 'Pulse', 'Chol', 'Gluc', 'MAP'],
      datasets: [{
        label: 'Health Radar',
        data: [(bmi / 30) * 100, (pulsePressure / 100) * 100, (chol / 3) * 100, (gluc / 3) * 100, ((map - 60) / (130 - 60)) * 100 ],
  
        backgroundColor: 'rgba(234, 40, 49, 0.1)',
        borderColor: '#EA2831',
        pointBackgroundColor: '#EA2831'
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true } } }
  });

}

//risk over time line chart
const placeholderCtx = document.getElementById('placeholderLineChart').getContext('2d');
placeholderChart = new Chart(placeholderCtx, {
  type: 'line',
  data: {
    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
    datasets: [{
      label: 'Risk Level Over Time',
      data: [70, 72, 69, 65, 68],
      borderColor: '#4fa3f7',
      fill: false,
      tension: 0.3
    }]
  },
  options: { responsive: true }
});

  
});
