/* PharmaGest — interactions & animations */
(function () {
    "use strict";

    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

    /* Sidebar mobile */
    const sidebar = $("#pgSidebar");
    const overlay = $("#pgOverlay");
    const toggle = $("#pgMenuToggle");
    const closeSidebar = () => {
        if (sidebar) sidebar.classList.remove("open");
        if (overlay) overlay.classList.remove("show");
    };
    if (toggle && sidebar) {
        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            if (overlay) overlay.classList.toggle("show");
        });
    }
    if (overlay) overlay.addEventListener("click", closeSidebar);
    $$(".pg-sidebar .pg-nav a").forEach((a) => a.addEventListener("click", closeSidebar));

    /* Reveal on scroll */
    const revealEls = $$(".reveal");
    if ("IntersectionObserver" in window) {
        const io = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        io.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0, rootMargin: "0px 0px -30px 0px" }
        );
        revealEls.forEach((el) => {
            if (el.getBoundingClientRect().height > window.innerHeight) {
                el.classList.add("is-visible");
            } else {
                io.observe(el);
            }
        });
    } else {
        revealEls.forEach((el) => el.classList.add("is-visible"));
    }
    setTimeout(() => revealEls.forEach((el) => el.classList.add("is-visible")), 2500);

    /* Compteurs animés */
    function animateValue(el) {
        const raw = String(el.dataset.count !== undefined ? el.dataset.count : el.textContent)
            .replace(/\s/g, "")
            .replace(/,/g, ".")
            .replace(/[^\d.-]/g, "");
        const target = parseFloat(raw) || 0;
        const decimals = parseInt(el.dataset.decimals || "0", 10);
        const suffix = el.dataset.suffix || "";
        const prefix = el.dataset.prefix || "";
        const duration = parseInt(el.dataset.duration || "1400", 10);
        const start = performance.now();
        const from = 0;
        function frame(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = from + (target - from) * eased;
            el.textContent =
                prefix +
                value.toLocaleString("fr-FR", {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals,
                }) +
                suffix;
            if (progress < 1) requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    }
    const counters = $$("[data-count]");
    if (counters.length) {
        if ("IntersectionObserver" in window) {
            const co = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            animateValue(entry.target);
                            co.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.4 }
            );
            counters.forEach((el) => co.observe(el));
        } else {
            counters.forEach(animateValue);
        }
    }

    /* Barres de progression */
    requestAnimationFrame(() => {
        $$(".pg-progress > span").forEach((span) => {
            const w = span.dataset.width || span.style.width || "0%";
            span.style.width = "0%";
            setTimeout(() => (span.style.width = w), 220);
        });
    });

    /* Toasts */
    $$(".pg-toast").forEach((toast) => {
        const closeBtn = $(".close", toast);
        if (closeBtn) closeBtn.addEventListener("click", () => dismissToast(toast));
        setTimeout(() => dismissToast(toast), 5200);
    });
    function dismissToast(toast) {
        toast.classList.add("hide");
        setTimeout(() => toast.remove(), 320);
    }

    /* Chiffres qui "flashent" quand le panier change */
    const cartBadge = $("#cartBadge");
    if (cartBadge) {
        cartBadge.classList.add("animate-fade-in");
    }

    /* Recherche instantanée simple (filtre de cartes produits) */
    const liveSearch = $("#liveSearch");
    if (liveSearch) {
        liveSearch.addEventListener("input", function () {
            const q = this.value.toLowerCase().trim();
            $$("[data-search]").forEach((card) => {
                const hay = card.getAttribute("data-search").toLowerCase();
                card.style.display = !q || hay.includes(q) ? "" : "none";
            });
            const empty = $("#liveEmpty");
            if (empty) {
                const visible = $$("[data-search]").filter((c) => c.style.display !== "none").length;
                empty.style.display = visible ? "none" : "";
            }
        });
    }

    /* Confirmation générique */
    $$("[data-confirm]").forEach((el) => {
        el.addEventListener("click", (e) => {
            if (!window.confirm(el.getAttribute("data-confirm"))) e.preventDefault();
        });
    });

    /* Chart.js thème global + helpers */
    window.pgCharts = {};
    window.pgMakeChart = function (id, config) {
        const canvas = document.getElementById(id);
        if (!canvas || typeof Chart === "undefined") return null;
        if (window.pgCharts[id]) window.pgCharts[id].destroy();
        const chart = new Chart(canvas, config);
        window.pgCharts[id] = chart;
        return chart;
    };

    if (typeof Chart !== "undefined") {
        Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
        Chart.defaults.font.size = 11;
        Chart.defaults.color = "#64748b";
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.legend.labels.padding = 16;
        Chart.defaults.plugins.tooltip.backgroundColor = "#0f172a";
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 10;
        Chart.defaults.plugins.tooltip.titleFont = { weight: "700" };
        Chart.defaults.elements.line.tension = 0.42;
        Chart.defaults.elements.line.borderWidth = 2.5;
        Chart.defaults.elements.point.radius = 0;
        Chart.defaults.elements.point.hoverRadius = 5;
    }
})();
