document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    if (page === "home") initAuthTabs();
    if (page === "dashboard") {
        initSymptomSearch();
        autoScrollToReport();
    }
});

function initAuthTabs() {
    const authShell = document.querySelector("[data-auth-shell]");
    if (!authShell) return;
    const buttons = [...document.querySelectorAll("[data-auth-tab]")];
    const panes = [...document.querySelectorAll("[data-auth-pane]")];
    const triggers = [...document.querySelectorAll("[data-auth-tab-trigger]")];

    function setTab(name) {
        buttons.forEach((button) => button.classList.toggle("is-active", button.dataset.authTab === name));
        panes.forEach((pane) => pane.classList.toggle("is-active", pane.dataset.authPane === name));
    }

    buttons.forEach((button) => button.addEventListener("click", () => setTab(button.dataset.authTab)));
    triggers.forEach((button) => button.addEventListener("click", () => setTab(button.dataset.authTabTrigger)));
    setTab(authShell.dataset.activeTab || "login");
}

function initSymptomSearch() {
    const search = document.getElementById("symptom-search");
    const chips = [...document.querySelectorAll(".symptom-chip")];
    const checks = [...document.querySelectorAll(".symptom-chip input[type='checkbox']")];
    const count = document.getElementById("selected-count");

    function updateCount() {
        if (count) count.textContent = String(checks.filter((item) => item.checked).length);
    }

    if (search) {
        search.addEventListener("input", (event) => {
            const query = event.target.value.trim().toLowerCase();
            chips.forEach((chip) => {
                chip.hidden = query.length > 0 && !(chip.dataset.label || "").includes(query);
            });
        });
    }

    checks.forEach((item) => item.addEventListener("change", updateCount));
    updateCount();
}

function autoScrollToReport() {
    if (document.body.dataset.autoScroll !== "true") return;
    const report = document.getElementById("report-view");
    if (report) requestAnimationFrame(() => report.scrollIntoView({ behavior: "smooth", block: "start" }));
}
