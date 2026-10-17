/**
 * Git Auto/Manual Updater, Session Auth Controls & iOS Bottom Tab Bar for Shorts Studio UI
 */
(function () {
    "use strict";

    function notifyUser(message, type) {
        if (typeof window.showToast === "function") {
            window.showToast(message, type || "info");
            return;
        }
        const container = document.getElementById("toast-container");
        if (!container) return;
        const toast = document.createElement("div");
        toast.className = "toast-item " + (type || "info");
        toast.style.cssText =
            "background:#171f22;border:1px solid #c8ff3d;color:#f3f7f4;padding:10px 14px;border-radius:10px;margin-top:8px;font-size:13px;box-shadow:0 12px 32px rgba(0,0,0,0.45);";
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, 4000);
    }

    async function refreshGitStatus(doFetch) {
        const btn = document.getElementById("header-btn-git-update");
        const badge = document.getElementById("header-git-badge");
        const textEl = document.getElementById("header-git-text");
        if (!btn) return;

        try {
            const url = "/api/system/git-status" + (doFetch ? "?fetch=true" : "");
            const res = await fetch(url, { cache: "no-store" });
            if (res.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!res.ok) return;
            const data = await res.json();
            if (data.commit && textEl) {
                textEl.textContent = "Güncelle (" + data.commit + ")";
            }
            if (data.subject) {
                btn.title =
                    "Dal: " +
                    (data.branch || "main") +
                    " · Son Commit: " +
                    data.commit +
                    " — " +
                    data.subject +
                    "\nGit'ten en güncel dosyaları çekmek için tıklayın.";
            }
            if (badge) {
                const behind = Number(data.behind_count || 0);
                if (behind > 0) {
                    badge.textContent = "+" + behind + " Yeni";
                    badge.style.display = "inline-block";
                } else {
                    badge.style.display = "none";
                }
            }
        } catch (_) {}
    }

    async function triggerGitUpdate() {
        const btn = document.getElementById("header-btn-git-update");
        const icon = document.getElementById("git-update-icon");
        if (!btn || btn.disabled) return;

        btn.disabled = true;
        if (icon) icon.classList.add("fa-spin");
        notifyUser("Git deposundan en güncel dosyalar kontrol ediliyor...", "info");

        try {
            const res = await fetch("/api/system/git-update", { method: "POST" });
            if (res.status === 401) {
                window.location.href = "/login";
                return;
            }
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || "Git güncellemesi başarısız oldu.");
            }
            if (data.updated) {
                notifyUser(
                    "Güncellendi (" +
                        data.old_commit +
                        " → " +
                        data.new_commit +
                        "). Sayfa yenileniyor...",
                    "success"
                );
                setTimeout(function () {
                    window.location.reload();
                }, 1200);
            } else {
                notifyUser(
                    "Sistem zaten en güncel sürümde (" + (data.new_commit || "HEAD") + ").",
                    "success"
                );
                await refreshGitStatus(false);
            }
        } catch (err) {
            notifyUser(err.message || "Git güncelleme hatası", "error");
        } finally {
            btn.disabled = false;
            if (icon) icon.classList.remove("fa-spin");
        }
    }

    async function handleLogout() {
        try {
            await fetch("/api/auth/logout", { method: "POST" });
        } finally {
            window.location.href = "/login";
        }
    }

    function initIosBottomNav() {
        const bottomNav = document.getElementById("ios-bottom-nav");
        if (!bottomNav) return;

        const iosButtons = Array.from(bottomNav.querySelectorAll(".ios-bottom-nav__btn"));

        function syncActiveIosTab(tabId) {
            iosButtons.forEach(function (btn) {
                const t = btn.getAttribute("data-ios-tab");
                if (t) {
                    btn.classList.toggle("active", t === tabId);
                }
            });
        }

        iosButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                const action = btn.getAttribute("data-ios-action");
                if (action === "drawer") {
                    document.body.classList.toggle("mobile-nav-open");
                    return;
                }
                const tabId = btn.getAttribute("data-ios-tab");
                if (!tabId) return;
                document.body.classList.remove("mobile-nav-open");
                const sideBtn = document.querySelector('.nav-btn[data-tab="' + tabId + '"]');
                if (sideBtn) {
                    sideBtn.click();
                } else if (typeof window.switchTab === "function") {
                    window.switchTab(tabId);
                }
                syncActiveIosTab(tabId);
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        });

        document.querySelectorAll(".sidebar .nav-btn[data-tab]").forEach(function (sideBtn) {
            sideBtn.addEventListener("click", function () {
                const tabId = sideBtn.getAttribute("data-tab");
                if (tabId) syncActiveIosTab(tabId);
                document.body.classList.remove("mobile-nav-open");
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        const gitBtn = document.getElementById("header-btn-git-update");
        if (gitBtn) {
            gitBtn.addEventListener("click", triggerGitUpdate);
        }
        const logoutBtn = document.getElementById("header-btn-logout");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", handleLogout);
        }
        initIosBottomNav();
        refreshGitStatus(false);
        setInterval(function () {
            refreshGitStatus(true);
        }, 120000);
    });
})();
