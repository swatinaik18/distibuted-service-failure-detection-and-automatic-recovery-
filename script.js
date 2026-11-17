const API_URL = "http://127.0.0.1:5000/api/status";
const HISTORY_URL = "http://127.0.0.1:5000/api/history";

let responseChart;
const maxPoints = 10;


// =====================================
// SAFE TEXT DISPLAY
// =====================================

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}


// =====================================
// LIVE RESPONSE TIME GRAPH
// =====================================

function initializeResponseChart() {

    const canvas = document.getElementById("responseTimeChart");

    if (!canvas || typeof Chart === "undefined") {
        console.error("Chart.js or graph canvas not found");
        return;
    }

    responseChart = new Chart(canvas, {

        type: "line",

        data: {
            labels: [],

            datasets: [
                {
                    label: "Service-1",
                    data: [],
                    tension: 0.3
                },
                {
                    label: "Service-2",
                    data: [],
                    tension: 0.3
                },
                {
                    label: "Service-3",
                    data: [],
                    tension: 0.3
                }
            ]
        },

        options: {

            responsive: true,
            maintainAspectRatio: false,
            animation: false,

            plugins: {
                legend: {
                    display: true,
                    position: "top"
                }
            },

            scales: {

                y: {
                    beginAtZero: true,

                    title: {
                        display: true,
                        text: "Response Time (ms)"
                    }
                },

                x: {
                    title: {
                        display: true,
                        text: "Time"
                    },

                    ticks: {
                        maxTicksLimit: 5,
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            }
        }
    });
}


function updateResponseChart(services) {

    if (!responseChart) {
        initializeResponseChart();
    }

    if (!responseChart) return;

    responseChart.data.labels.push(
        new Date().toLocaleTimeString()
    );

    responseChart.data.datasets.forEach(dataset => {

        const service = services.find(
            item => item.name === dataset.label
        );

        dataset.data.push(
            service && service.response_time != null
                ? service.response_time
                : null
        );

        if (dataset.data.length > maxPoints) {
            dataset.data.shift();
        }
    });

    if (responseChart.data.labels.length > maxPoints) {
        responseChart.data.labels.shift();
    }

    responseChart.update();
}


// =====================================
// DASHBOARD UPDATE
// =====================================

async function updateDashboard() {

    try {

        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error("Backend connection failed");
        }

        const data = await response.json();
        const services = data.services || [];

        updateResponseChart(services);

        const healthy = services.filter(
            service => service.status === "healthy"
        ).length;

        const failed = services.filter(
            service => service.status === "failed"
        ).length;

        const recoveries = services.reduce(
            (total, service) =>
                total + (service.recoveries || 0),
            0
        );

        document.getElementById("totalServices").textContent =
            data.total_services;

        document.getElementById("healthyServices").textContent =
            healthy;

        document.getElementById("failedServices").textContent =
            failed;

        document.getElementById("totalRecoveries").textContent =
            recoveries;

        const serviceList = document.getElementById("serviceList");

        serviceList.innerHTML = services.map(service => {

            const status = service.status.toLowerCase();

            return `
                <div class="service-card">

                    <h3>${escapeHTML(service.name)}</h3>

                    <span class="status ${escapeHTML(status)}">
                        ${escapeHTML(service.status.toUpperCase())}
                    </span>

                    <p>Port: ${escapeHTML(service.port)}</p>

                    <p>Recoveries: ${service.recoveries || 0}</p>

                    <p>
                        Response Time:
                        ${service.response_time != null
                    ? escapeHTML(service.response_time) + " ms"
                    : "Unavailable"}
                    </p>

                </div>
            `;

        }).join("");

    } catch (error) {

        console.error("Dashboard error:", error);

        document.getElementById("serviceList").innerHTML =
            "<p>Unable to connect to the monitoring backend.</p>";
    }
}


// =====================================
// ACTIVITY LOGS
// =====================================

async function loadRecoveryHistory() {

    const logs = document.getElementById("activityLogs");

    if (!logs) return;

    try {

        const response = await fetch(HISTORY_URL);

        if (!response.ok) {
            throw new Error("History API failed");
        }

        const history = await response.json();

        if (history.length === 0) {

            logs.innerHTML =
                "<p>No recovery history available.</p>";

            return;
        }

        logs.innerHTML = history.slice().reverse().map(event => {

            const id = escapeHTML(event.id);

            return `
                <div class="log-entry">

                    <div class="log-details">
                        <span>${escapeHTML(event.Timestamp)}</span>
                        <strong>${escapeHTML(event.Service)}</strong>
                        <span class="recovered-label">
                            ${escapeHTML(event.Result)}
                        </span>
                    </div>

                    <button
                        class="delete-log-btn"
                        type="button"
                        onclick="deleteRecoveryRecord('${id}')">
                         Delete
                    </button>

                </div>
            `;

        }).join("");

    } catch (error) {

        console.error("History error:", error);

        logs.textContent = "Unable to load activity logs.";
    }
}


// =====================================
// DELETE INDIVIDUAL RECOVERY RECORD
// =====================================

async function deleteRecoveryRecord(id) {

    if (!confirm("Are you sure you want to delete this recovery record?")) {
        return;
    }

    try {

        const response = await fetch(HISTORY_URL, {

            method: "DELETE",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                id: id
            })
        });


        const text = await response.text();

        let result;

        try {
            result = JSON.parse(text);
        } catch {
            throw new Error("Backend returned an HTML error. Check that the updated backend is running on port 5000.");
        }

    

        if (!response.ok) {
            throw new Error(
                `Error ${response.status}: ${result.error || "Delete failed"}`
            );
        }


        // Refresh logs after successful deletion
        await loadRecoveryHistory();

    } catch (error) {

        console.error("Delete error:", error);
        alert(error.message);

        
    }
}

// =====================================
// DELETE BUTTON CLICK HANDLER
// =====================================

document.addEventListener("click", function (event) {

    const button = event.target.closest(".delete-log-btn");

    if (!button) return;

    const recordId = button.dataset.id;

    if (recordId) {
        deleteRecoveryRecord(recordId);
    }
});


// =====================================
// START MONITORING
// =====================================

initializeResponseChart();

updateDashboard();

setInterval(updateDashboard, 2000);

loadRecoveryHistory();

setInterval(loadRecoveryHistory, 5000);
window.deleteRecoveryRecord = deleteRecoveryRecord;