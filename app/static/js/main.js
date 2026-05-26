document.addEventListener("DOMContentLoaded", () => {
    console.log("Flask site is ready");
});

(function () {
    const tbody = document.getElementById("logs-tbody");
    const lastAccessEl = document.getElementById("last-access");
    const countEl = document.getElementById("count");
    const updatedAtEl = document.getElementById("updated-at");
    const errorBox = document.getElementById("error-box");

    if (!tbody) return;

    const POLL_MS = 10000;

    function escapeHtml(str) {
        return String(str ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function formatDateTime(value) {
        if (!value) return "—";
        const dt = new Date(value);
        if (Number.isNaN(dt.getTime())) return String(value);
        return dt.toLocaleString("ru-RU", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }

    function statusClass(status) {
        const code = Number(status);
        if (code >= 500) return "status status-5xx";
        if (code >= 400) return "status status-4xx";
        if (code >= 300) return "status status-3xx";
        if (code >= 200) return "status status-2xx";
        return "status";
    }

    function renderRows(entries) {
        if (!Array.isArray(entries) || entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-row">Пока нет данных</td></tr>';
            return;
        }

        const rows = [...entries].reverse().map((row, idx) => {
            const status = row.status ?? "";
            const geo = row.geo || {};
            const geoText = (geo.country || "") + (geo.city ? (", " + geo.city) : "");
            return `
                <tr>
                    <td>${idx + 1}</td>
                    <td>${escapeHtml(formatDateTime(row.time_local ?? row.time ?? "-"))}</td>
                    <td>${escapeHtml(row.remote_addr ?? "-")}</td>
                    <td>${escapeHtml(geoText)}</td>
                    <td class="req-cell">${escapeHtml(row.request ?? row.raw ?? "-")}</td>
                    <td><span class="${statusClass(status)}">${escapeHtml(status || "-")}</span></td>
                    <td>${escapeHtml(row.request_time ?? "-")}</td>
                </tr>
            `;
        });

        tbody.innerHTML = rows.join("");
    }

    function setError(msg) {
        if (!msg) {
            errorBox.classList.add("hidden");
            errorBox.textContent = "";
            return;
        }

        errorBox.classList.remove("hidden");
        errorBox.textContent = msg;
    }

    async function loadLogs() {
        try {
            const res = await fetch("/logs", { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            lastAccessEl.textContent = formatDateTime(data.last_access_utc);
            countEl.textContent = String(data.count ?? 0);
            updatedAtEl.textContent = new Date().toLocaleTimeString("ru-RU");
            renderRows(data.last_N_log_entries || []);
            setError("");
        } catch (err) {
            setError(`Не удалось обновить данные: ${err.message}`);
        }
    }

    loadLogs();
    setInterval(loadLogs, POLL_MS);
})();
