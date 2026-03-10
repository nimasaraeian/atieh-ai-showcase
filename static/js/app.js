const App = (() => {
    const state = {
        route: "/",
        trendsLimit: 12
    };

    const el = {
        title: document.getElementById("page-title"),
        subtitle: document.getElementById("page-subtitle"),
        content: document.getElementById("page-content"),
        toast: document.getElementById("toast"),
        refreshBtn: document.getElementById("refreshBtn"),
        modal: document.getElementById("patientModal"),
        modalBody: document.getElementById("patientModalBody"),
        modalRecordNo: document.getElementById("modalRecordNo"),
        closeModalBtn: document.getElementById("closeModalBtn")
    };

    function formatNumber(value) {
        if (value === null || value === undefined || value === "") return "-";
        return new Intl.NumberFormat("en-US").format(Number(value));
    }

    function formatMoney(value) {
        if (value === null || value === undefined) return "-";
        return `${formatNumber(Math.round(Number(value)))} ریال`;
    }

    function escapeHtml(str) {
        return String(str ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatMobileDisplay(mobile) {
        const m = String(mobile ?? "").trim();
        if (!m) return "-";
        if (m.toUpperCase().startsWith("UNKNOWN_")) return "موبایل نامشخص";
        return m;
    }

    function badgeClass(value) {
        const v = String(value || "").toLowerCase();

        if (["ready", "active", "fully_populated", "present", "success"].includes(v)) return "badge badge--success";
        if (["critical", "high", "present_but_small"].includes(v)) return "badge badge--danger";
        if (["elevated", "moderate", "warning", "partial"].includes(v)) return "badge badge--warning";
        return "badge badge--info";
    }

    function showToast(message) {
        el.toast.textContent = message;
        el.toast.classList.add("show");
        clearTimeout(showToast._timer);
        showToast._timer = setTimeout(() => {
            el.toast.classList.remove("show");
        }, 3000);
    }

    function setLoading(message = "در حال بارگذاری...") {
        el.content.innerHTML = `<div class="loading-state">${message}</div>`;
    }

    function setError(message) {
        el.content.innerHTML = `<div class="error-state">خطا: ${escapeHtml(message)}</div>`;
    }

    function updateNav() {
        document.querySelectorAll(".nav-link").forEach(link => {
            const route = link.dataset.route;
            link.classList.toggle("active", route === state.route);
        });
    }

    function setPageMeta(title, subtitle) {
        el.title.textContent = title;
        el.subtitle.textContent = subtitle;
        updateNav();
    }

    function normalizeHashRoute() {
        const hash = window.location.hash || "#/";
        const route = hash.replace(/^#/, "") || "/";
        state.route = route;
    }

    async function render() {
        normalizeHashRoute();

        if (state.route === "/") return renderStaffDashboard();
        if (state.route === "/manager") return renderManagerDashboard();
        if (state.route === "/followup") return renderFollowup();
        if (state.route === "/top300") return renderTop300();
        if (state.route === "/priority") return renderPriority();
        if (state.route === "/patients") return renderPatients();
        if (state.route === "/appointment") return renderAppointment();

        setPageMeta("صفحه یافت نشد", "مسیر انتخاب شده معتبر نیست");
        el.content.innerHTML = `<div class="empty-state">این بخش هنوز پیاده‌سازی نشده است.</div>`;
    }

    async function renderStaffDashboard() {
        setPageMeta("داشبورد عملیاتی", "صفحه کاری روزانه برای پذیرش و پرسنل کلینیک");

        el.content.innerHTML = `
            <section class="grid grid--main">
                <div class="card">
                    <div class="card__header">
                        <div>
                            <h3 class="card__title">جستجوی سریع بیمار</h3>
                            <div class="card__subtitle">نام بیمار، موبایل یا شماره پرونده را جستجو کنید</div>
                        </div>
                    </div>
                    <div class="card__body">
                        <div class="search-bar">
                            <input id="patient-search" placeholder="مثلاً احمدی رضا، رضا احمدی یا شماره پرونده" />
                            <button id="patient-search-btn" class="btn btn--primary">جستجو</button>
                        </div>
                        <div class="table-wrap" style="margin-top:16px;">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>نام بیمار</th>
                                        <th>موبایل</th>
                                        <th>شماره پرونده</th>
                                        <th>آخرین پرداخت</th>
                                        <th>در Top300</th>
                                        <th>در صف پیگیری</th>
                                        <th>جزئیات</th>
                                    </tr>
                                </thead>
                                <tbody id="patient-results">
                                    <tr>
                                        <td colspan="7" class="empty-state">برای شروع، نام، موبایل یا شماره پرونده را وارد کنید.</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card__header">
                        <div>
                            <h3 class="card__title">میانبرهای کاری</h3>
                            <div class="card__subtitle">دسترسی سریع به بخش‌های اصلی سیستم</div>
                        </div>
                    </div>
                    <div class="card__body">
                        <div class="quick-actions" style="display:flex; flex-wrap:wrap; gap:8px;">
                            <button class="btn btn--secondary" data-nav="#/patients">جستجوی پیشرفته بیمار</button>
                            <button class="btn btn--secondary" data-nav="#/followup">صف پیگیری</button>
                            <button class="btn btn--secondary" data-nav="#/top300">اولویت ۳۰۰</button>
                            <button class="btn btn--secondary" data-nav="#/priority">اولویت AI</button>
                            <button class="btn btn--secondary" data-nav="#/appointment">درخواست نوبت هوشمند</button>
                            <a href="/manager" class="btn btn--secondary">داشبورد مدیریتی (مدیر)</a>
                        </div>
                        <p class="section-note" style="margin-top:16px;">
                            این صفحه برای استفاده روزانه پرسنل طراحی شده است و فقط اطلاعات عملیاتی را نمایش می‌دهد.
                        </p>
                    </div>
                </div>
            </section>
        `;

        document
            .getElementById("patient-search-btn")
            .addEventListener("click", searchPatient);

        document
            .getElementById("patient-search")
            .addEventListener("keypress", function (e) {
                if (e.key === "Enter") {
                    searchPatient();
                }
            });

        document.querySelectorAll(".quick-actions [data-nav]").forEach(btn => {
            btn.addEventListener("click", () => {
                const target = btn.getAttribute("data-nav");
                if (target) {
                    window.location.hash = target;
                }
            });
        });
    }

    async function renderManagerDashboard() {
        setPageMeta("داشبورد مدیریتی", "نمای کلی وضعیت مالی و اجرایی (نمای مدیر / دسترسی محدود)");
        setLoading("در حال بارگذاری داشبورد مدیریتی...");

        try {
            const [kpis, summary, insights, trends, vipData] = await Promise.all([
                API.getDashboardKpis(),
                API.getDashboardSummary(),
                API.getDashboardInsights(),
                API.getDashboardTrends(state.trendsLimit),
                API.getTopVIPs(10, 0)
            ]);

            const trendMaxRevenue = Math.max(...trends.data.map(x => Number(x.total_revenue || 0)), 1);

            el.content.innerHTML = `
                <div class="manager-banner" style="background:linear-gradient(135deg,#1e3a5f 0%,#0f172a 100%);border:1px solid rgba(59,130,246,0.4);border-radius:12px;padding:12px 16px;margin-bottom:20px;display:flex;align-items:center;gap:12px;">
                    <span style="font-weight:600;color:#93c5fd;">پنل مدیریتی</span>
                    <span style="color:rgba(255,255,255,0.7);font-size:0.9em;">این بخش ویژه مدیریت است — گزارش‌های مالی و اجرایی</span>
                </div>
                <section class="grid grid--kpis">
                    ${renderKpiCard("کل درآمد ردیابی‌شده", formatMoney(kpis.total_revenue), "مجموع ارزش مالی ثبت‌شده در موتور مالی")}
                    ${renderKpiCard("هویت‌های مالی", formatNumber(kpis.total_financial_identities), "کل record_no های تحلیل‌شده")}
                    ${renderKpiCard("میانگین درآمد هر هویت", formatMoney(kpis.avg_revenue_per_identity), "میانگین ارزش مالی هر identity")}
                    ${renderKpiCard("VIP + HIGH", formatNumber(kpis.vip_plus_high_count), `${formatNumber(kpis.vip_count)} مورد VIP`)}
                    ${renderKpiCard("صف پیگیری قابل تماس", formatNumber(kpis.total_followup_contactable), `Backlog تقریبی: ${formatNumber(kpis.followup_backlog_days)} روز`)}
                    ${renderKpiCard("صف اولویت 300", formatNumber(kpis.total_scheduling_top300), `${formatNumber(kpis.critical_priority_count)} مورد بحرانی`)}
                    ${renderKpiCard("VIP Count", formatNumber(summary.vip_count), "بیماران با بالاترین ارزش مالی")}
                    ${renderKpiCard("سطح آمادگی سیستم", insights.system_status === "ready" ? "READY" : "PARTIAL", "وضعیت فعلی لایه تصمیم‌سازی")}
                </section>

                <section class="grid grid--main">
                    <div class="card">
                        <div class="card__header">
                            <div>
                                <h3 class="card__title">روند 12 دوره اخیر</h3>
                                <div class="card__subtitle">بر اساس last_payment_date_raw</div>
                            </div>
                        </div>
                        <div class="card__body">
                            <div class="spark-bars">
                                ${trends.data.map(item => `
                                    <div class="spark-row">
                                        <div class="spark-row__label">${escapeHtml(item.period)}</div>
                                        <div class="spark-bar">
                                            <div class="spark-bar__fill" style="width:${Math.max(3, (Number(item.total_revenue || 0) / trendMaxRevenue) * 100)}%"></div>
                                        </div>
                                        <div class="spark-row__value">${formatNumber(Math.round(item.total_revenue || 0))}</div>
                                    </div>
                                `).join("")}
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card__header">
                            <div>
                                <h3 class="card__title">Insight مدیریتی</h3>
                                <div class="card__subtitle">تفسیر مستقیم موتور هوشمند</div>
                            </div>
                        </div>
                        <div class="card__body">
                            <div class="status-list">
                                ${renderStatusItem("وضعیت سیستم", insights.system_status)}
                                ${renderStatusItem("موتور مالی", insights.financial_engine_status)}
                                ${renderStatusItem("وضعیت VIP", insights.vip_segment_status)}
                                ${renderStatusItem("وضعیت backlog", insights.followup_backlog_status)}
                                ${renderStatusItem("فشار scheduling", insights.scheduling_pressure_status)}
                                ${renderStatusItem("صف اولویت", insights.priority_queue_status)}
                            </div>

                            <ul class="insight-list" style="margin-top:16px; padding:0;">
                                ${(insights.insights || []).map(item => `<li>${escapeHtml(item)}</li>`).join("")}
                            </ul>
                        </div>
                    </div>
                </section>

                <section class="grid grid--bottom">
                    <div class="card">
                        <div class="card__header">
                            <div>
                                <h3 class="card__title">Top VIP Patients</h3>
                                <div class="card__subtitle">بالاترین بیماران VIP بر اساس score و revenue</div>
                            </div>
                        </div>
                        <div class="card__body">
                            <div class="table-wrap">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>Record No</th>
                                            <th>Tier</th>
                                            <th>Score</th>
                                            <th>Txn Count</th>
                                            <th>Revenue</th>
                                            <th>Last Payment</th>
                                            <th>جزئیات</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${(vipData.data || []).map(row => `
                                            <tr>
                                                <td>${escapeHtml(row.record_no)}</td>
                                                <td>${escapeHtml(row.financial_tier)}</td>
                                                <td>${Number(row.financial_value_score || 0).toFixed(4)}</td>
                                                <td>${formatNumber(row.lifetime_txn_count)}</td>
                                                <td>${formatNumber(Math.round(row.lifetime_net_received || 0))}</td>
                                                <td>${escapeHtml(row.last_payment_date_raw)}</td>
                                                <td>
                                                    <button class="table__action-btn" data-record-no="${escapeHtml(row.record_no)}">
                                                        مشاهده
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join("")}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card__header">
                            <div>
                                <h3 class="card__title">شاخص‌های تکمیلی</h3>
                                <div class="card__subtitle">ترکیب داده‌های summary و insights</div>
                            </div>
                        </div>
                        <div class="card__body">
                            <div class="metric-list">
                                ${renderMetricItem("VIP Count", summary.vip_count)}
                                ${renderMetricItem("HIGH Count", summary.high_count)}
                                ${renderMetricItem("MEDIUM Count", summary.medium_count)}
                                ${renderMetricItem("LOW Count", summary.low_count)}
                                ${renderMetricItem("Critical Priority", summary.critical_priority_count)}
                                ${renderMetricItem("High Priority", summary.high_priority_count)}
                                ${renderMetricItem("Follow-up Daily", summary.total_daily_balanced)}
                                ${renderMetricItem("Average Revenue / Identity", formatMoney(insights.metrics?.avg_revenue_per_identity))}
                                ${renderMetricItem("VIP Share %", insights.metrics?.vip_share_pct)}
                                ${renderMetricItem("VIP + HIGH Share %", insights.metrics?.high_plus_vip_share_pct)}
                            </div>
                            <p class="section-note" style="margin-top:16px;">
                                این داشبورد اکنون مستقیم به لایه‌های summary، KPI، insight، VIP ranking و patient drill-down متصل است.
                            </p>
                        </div>
                    </div>
                </section>
                
                <section class="card ai-suggestions-card">
                    <div class="card__header">
                        <div>
                            <h3 class="card__title">AI Suggestions Review</h3>
                            <div class="card__subtitle">بررسی و تایید/رد پیشنهادهای نوبت‌دهی AI</div>
                        </div>
                        <button id="aiSuggestionsRefreshBtn" class="btn btn--secondary">Refresh Suggestions</button>
                    </div>
                    <div class="card__body">
                        <div class="table-wrap">
                            <table class="table" id="aiSuggestionsTable">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Record No</th>
                                        <th>Patient Name</th>
                                        <th>Service Name</th>
                                        <th>Insurance Name</th>
                                        <th>Suggested Slot</th>
                                        <th>Priority Band</th>
                                        <th>Priority Score</th>
                                        <th>Status</th>
                                        <th>Notes</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="aiSuggestionsTbody">
                                    <tr>
                                        <td colspan="11">در حال بارگذاری پیشنهادها...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            `;

            bindVipButtons();
            bindAiSuggestionsSection();
        } catch (error) {
            setError(error.message || "خطا در بارگذاری داشبورد");
        }
    }

    async function renderFollowup() {
        setPageMeta("صف پیگیری", "نمایش بیماران قابل تماس برای follow-up");
        setLoading();

        try {
            const data = await API.getFollowupQueue(100, 0);
            const rows = data.data || [];
            el.content.innerHTML = renderSimpleTableCard(
                "صف پیگیری قابل تماس",
                "این لیست از v_financial_followup_queue_contactable خوانده می‌شود",
                [
                    "record_no",
                    "patient_name_canonical",
                    "mobile_canonical",
                    "financial_tier",
                    "action_type",
                    "lifetime_net_received",
                    "last_payment_date_raw"
                ],
                rows
            );
        } catch (error) {
            setError(error.message);
        }
    }

    async function renderTop300() {
        setPageMeta("صف اولویت ۳۰۰", "بیماران منتخب برای scheduling priority");
        setLoading();

        try {
            const data = await API.getTop300(100, 0);
            const rows = data.data || [];
            el.content.innerHTML = renderSimpleTableCard(
                "Top 300 Scheduling Queue",
                "خروجی v_financial_scheduling_queue_top300",
                [
                    "record_no",
                    "patient_name_canonical",
                    "financial_tier",
                    "action_type",
                    "scheduling_band",
                    "scheduling_priority_score",
                    "lifetime_net_received",
                    "last_payment_date_raw"
                ],
                rows
            );
        } catch (error) {
            setError(error.message);
        }
    }

    async function renderPriority() {
        setPageMeta("اولویت AI", "خروجی لایه scheduling priority");
        setLoading();

        try {
            const data = await API.getPriority(100, 0);
            const rows = data.data || [];
            el.content.innerHTML = renderSimpleTableCard(
                "Scheduling Priority",
                "نمایش اولویت‌بندی تصمیم‌یار برای زمان‌بندی",
                [
                    "record_no",
                    "patient_name_canonical",
                    "financial_tier",
                    "action_type",
                    "scheduling_band",
                    "scheduling_priority_score",
                    "lifetime_net_received",
                    "last_payment_date_raw"
                ],
                rows
            );
        } catch (error) {
            setError(error.message);
        }
    }

    async function renderPatients() {
        setPageMeta("جستجوی بیمار", "نام بیمار، موبایل یا شماره پرونده را جستجو کنید");
        el.content.innerHTML = `
            <div class="card">
                <div class="search-bar">
                    <input id="patient-search" placeholder="نام بیمار، موبایل یا شماره پرونده">
                    <button id="patient-search-btn" class="btn btn--primary">جستجو</button>
                </div>

                <div class="table-wrap">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>نام بیمار</th>
                                <th>موبایل</th>
                                <th>شماره پرونده</th>
                                <th>آخرین پرداخت</th>
                                <th>در Top300</th>
                                <th>در صف پیگیری</th>
                                <th>جزئیات</th>
                            </tr>
                        </thead>
                        <tbody id="patient-results"></tbody>
                    </table>
                </div>
            </div>
        `;

        document
            .getElementById("patient-search-btn")
            .addEventListener("click", searchPatient);

        document
            .getElementById("patient-search")
            .addEventListener("keypress", function (e) {
                if (e.key === "Enter") {
                    searchPatient();
                }
            });
    }

    async function searchPatient() {
        const inputEl = document.getElementById("patient-search");
        const q = (inputEl && inputEl.value || "").trim();
        if (!q) return;

        const tbody = document.getElementById("patient-results");
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="7" class="loading-state">در حال جستجو...</td></tr>`;

        try {
            const result = await API.getPatientsSearch(q, 50, 0);
            const rows = Array.isArray(result?.data) ? result.data : [];
            const count = result?.count ?? rows.length;

            tbody.innerHTML = "";

            if (rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="empty-state">بیمار پیدا نشد. با نام خانوادگی، شماره موبایل یا شماره پرونده جستجو کنید.</td></tr>`;
                return;
            }

            rows.forEach(p => {
                const tr = document.createElement("tr");
                const recordNo = p.record_no ?? p.recordNo ?? "-";
                const hasDetail = recordNo && String(recordNo) !== "-";
                const patientName = p.patient_name ?? p.patient_name_canonical ?? "-";
                const mobileDisplay = formatMobileDisplay(p.mobile ?? p.mobile_canonical);
                const lastPayment = p.last_payment_date_raw ?? "-";
                const inTop300 = p.in_top300 ? "بله" : "-";
                const inFollowup = p.in_followup_queue ? "بله" : "-";
                tr.innerHTML = `
                    <td>${escapeHtml(patientName)}</td>
                    <td>${escapeHtml(mobileDisplay)}</td>
                    <td>${escapeHtml(recordNo)}</td>
                    <td>${escapeHtml(lastPayment)}</td>
                    <td>${escapeHtml(inTop300)}</td>
                    <td>${escapeHtml(inFollowup)}</td>
                    <td>${hasDetail ? `<button class="table__action-btn" data-record-no="${escapeHtml(String(recordNo))}">مشاهده</button>` : "-"}</td>
                `;
                tbody.appendChild(tr);
            });

            bindVipButtons();
        } catch (err) {
            console.error("patient search error:", err);
            const msg = err && err.message ? String(err.message) : "خطا در اتصال به سرور";
            tbody.innerHTML = `<tr><td colspan="7" class="error-state">${escapeHtml(msg)}</td></tr>`;
        }
    }

    async function renderAppointment() {
        setPageMeta("نوبت جدید", "AI Scheduling Engine");
        el.content.innerHTML = `
            <div class="ai-scheduling">
                <div class="ai-scheduling__left">
                    <form id="appointmentAiForm" class="ai-form">
                        <div class="ai-form__field">
                            <label class="ai-form__label">Record No</label>
                            <input id="apptRecordNo" type="text" class="ai-form__input" placeholder="e.g. 139990" />
                        </div>
                        <div class="ai-form__field">
                            <label class="ai-form__label">Service</label>
                            <select id="apptService" class="ai-form__input ai-form__select">
                                <option value="">در حال بارگذاری...</option>
                            </select>
                        </div>
                        <div class="ai-form__field">
                            <label class="ai-form__label">Insurance</label>
                            <select id="apptInsurance" class="ai-form__input ai-form__select">
                                <option value="">در حال بارگذاری...</option>
                            </select>
                        </div>
                        <div class="ai-form__field">
                            <label class="ai-form__label">Preferred Day</label>
                            <select id="apptWeekday" class="ai-form__input ai-form__select">
                                <option value="">بدون ترجیح</option>
                                <option value="شنبه">شنبه</option>
                                <option value="یکشنبه">یکشنبه</option>
                                <option value="دوشنبه">دوشنبه</option>
                                <option value="سه‌شنبه">سه‌شنبه</option>
                                <option value="چهارشنبه">چهارشنبه</option>
                                <option value="پنجشنبه">پنجشنبه</option>
                                <option value="جمعه">جمعه</option>
                            </select>
                        </div>
                        <div class="ai-form__field">
                            <label class="ai-form__label">Backlog (optional)</label>
                            <input id="apptBacklog" type="text" class="ai-form__input" placeholder="e.g. درمان ریشه" />
                        </div>
                        <div class="ai-form__submit">
                            <button class="ai-form__btn" type="submit">Generate AI Suggestion</button>
                        </div>
                    </form>
                </div>
                <div class="ai-scheduling__right">
                    <div class="ai-result-card">
                        <h3 class="ai-result-card__title">AI Recommendations</h3>
                        <div id="appointmentAiResult" class="ai-result-card__body ai-result-card__body--empty">No request sent yet. Fill the form and click Generate.</div>
                    </div>
                </div>
            </div>
        `;

        const serviceSelect = document.getElementById("apptService");
        const insuranceSelect = document.getElementById("apptInsurance");
        const form = document.getElementById("appointmentAiForm");
        const resultBox = document.getElementById("appointmentAiResult");

        try {
            const [servicesRaw, insurancesRaw] = await Promise.all([
                API.getServicesCatalog(),
                API.getInsurancesCatalog()
            ]);

            const services = normalizeCatalogList(servicesRaw);
            const insurances = normalizeCatalogList(insurancesRaw);

            if (services.length > 0) {
                serviceSelect.innerHTML = `<option value="">انتخاب خدمت</option>` +
                    services.map(item => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join("");
            } else {
                serviceSelect.innerHTML = `<option value="">بدون کاتالوگ - دستی وارد کنید</option>`;
                serviceSelect.setAttribute("data-manual", "true");
                const field = serviceSelect.closest(".ai-form__field");
                if (field && !document.getElementById("apptServiceManual")) {
                    const manualInput = document.createElement("input");
                    manualInput.id = "apptServiceManual";
                    manualInput.type = "text";
                    manualInput.className = "ai-form__input";
                    manualInput.placeholder = "نام خدمت (فارسی)";
                    manualInput.style.marginTop = "8px";
                    field.appendChild(manualInput);
                }
            }

            insuranceSelect.innerHTML = `<option value="">انتخاب بیمه</option>` +
                insurances.map(item => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join("");
        } catch (error) {
            console.error("catalog load error:", error);
            serviceSelect.innerHTML = `<option value="">خطا در بارگذاری</option>`;
            insuranceSelect.innerHTML = `<option value="">خطا در بارگذاری</option>`;
        }

        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            let serviceVal = (document.getElementById("apptService")?.value || "").trim();
            const manualInput = document.getElementById("apptServiceManual");
            if (manualInput && manualInput.value) serviceVal = manualInput.value.trim();
            if (!serviceVal) {
                resultBox.className = "ai-result-card__body ai-result-card__body--error";
                resultBox.innerHTML = `<div class="ai-result-error">لطفاً یک خدمت را انتخاب کنید.</div>`;
                return;
            }

            resultBox.className = "ai-result-card__body ai-result-card__body--loading";
            resultBox.innerHTML = `<div class="ai-result-loading"><div class="ai-result-loading__spinner"></div><span>Calculating AI suggestions...</span></div>`;

            const payload = {
                service: serviceVal,
                insurance: (document.getElementById("apptInsurance")?.value || "").trim() || null,
                backlog: (document.getElementById("apptBacklog")?.value || "").trim() || null,
                doctor: null,
                weekday: (document.getElementById("apptWeekday")?.value || "").trim() || null
            };

            try {
                const result = await API.recommendSlot(payload);
                resultBox.className = "ai-result-card__body";
                resultBox.innerHTML = renderRecommendSlotResult(result, true);
                const bookBtn = resultBox.querySelector(".ai-book-recommended-btn");
                if (bookBtn) {
                    bookBtn.addEventListener("click", () => handleBookRecommended(result, resultBox));
                }
            } catch (error) {
                const msg = (error && error.message) ? String(error.message) : "خطای نامشخص";
                resultBox.className = "ai-result-card__body ai-result-card__body--error";
                resultBox.innerHTML = `<div class="ai-result-error">${escapeHtml(msg)}</div>`;
            }
        });
    }

    function renderKpiCard(label, value, hint) {
        return `
            <div class="kpi">
                <div class="kpi__label">${escapeHtml(label)}</div>
                <div class="kpi__value">${escapeHtml(value)}</div>
                <div class="kpi__hint">${escapeHtml(hint)}</div>
            </div>
        `;
    }

    function renderStatusItem(label, value) {
        return `
            <div class="status-item">
                <div class="status-item__label">${escapeHtml(label)}</div>
                <div class="status-item__value">
                    <span class="${badgeClass(value)}">${escapeHtml(value)}</span>
                </div>
            </div>
        `;
    }

    function renderMetricItem(label, value) {
        return `
            <div class="metric-item">
                <div class="metric-item__label">${escapeHtml(label)}</div>
                <div class="metric-item__value">${escapeHtml(String(value ?? "-"))}</div>
            </div>
        `;
    }

    function normalizePatientLookupRow(row) {
        const record_no =
            row.record_no ??
            row.recordNo ??
            row.RecordNo ??
            row.id ??
            "-";

        const patient_name =
            row.patient_name_canonical ??
            row.patient_name ??
            row.name ??
            row.full_name ??
            row.patient_name_clean ??
            "-";

        const mobile =
            row.mobile_canonical ??
            row.mobile ??
            row.phone ??
            row.phone_norm ??
            "-";

        const financial_tier =
            row.financial_tier ??
            row.tier ??
            "-";

        const last_payment_date_raw =
            row.last_payment_date_raw ??
            row.last_payment ??
            "-";

        const revenue =
            row.lifetime_net_received ??
            row.revenue ??
            null;

        return {
            record_no,
            patient_name,
            mobile,
            financial_tier,
            last_payment_date_raw,
            lifetime_net_received_display: revenue !== null ? formatMoney(revenue) : "-"
        };
    }

    function normalizeCatalogList(payload) {
        let raw = [];

        if (Array.isArray(payload)) raw = payload;
        else if (Array.isArray(payload.data)) raw = payload.data;
        else if (Array.isArray(payload.items)) raw = payload.items;
        else if (Array.isArray(payload.results)) raw = payload.results;
        else raw = [];

        return raw.map((item, index) => {
            if (typeof item === "string" || typeof item === "number") {
                return { value: String(item), label: String(item) };
            }

            const value =
                item.value ??
                item.code ??
                item.id ??
                item.name ??
                item.title ??
                String(index + 1);

            const label =
                item.label ??
                item.name ??
                item.title ??
                item.value ??
                item.code ??
                String(value);

            return {
                value: String(value),
                label: String(label)
            };
        });
    }

    const WEEKDAY_FA_TO_JS = { "شنبه": 6, "یکشنبه": 0, "دوشنبه": 1, "سه\u200cشنبه": 2, "سه‌شنبه": 2, "چهارشنبه": 3, "پنجشنبه": 4, "جمعه": 5 };

    function nextDateForWeekday(weekdayFa, timeStr) {
        const targetDow = WEEKDAY_FA_TO_JS[weekdayFa];
        if (targetDow === undefined) return null;
        const timePart = (timeStr || "").split("-")[0].trim() || "09:00";
        const [h, m] = timePart.split(":").map((x) => parseInt(x, 10) || 0);
        const now = new Date();
        const currentDow = now.getDay();
        let daysUntil = (targetDow - currentDow + 7) % 7;
        if (daysUntil === 0 && (now.getHours() > h || (now.getHours() === h && now.getMinutes() >= m))) daysUntil = 7;
        const d = new Date(now);
        d.setDate(d.getDate() + daysUntil);
        d.setHours(h, m, 0, 0);
        const y = d.getFullYear(), M = String(d.getMonth() + 1).padStart(2, "0"), D = String(d.getDate()).padStart(2, "0");
        const H = String(d.getHours()).padStart(2, "0"), Min = String(d.getMinutes()).padStart(2, "0");
        return `${y}-${M}-${D}T${H}:${Min}:00`;
    }

    async function handleBookRecommended(result, resultBox) {
        const recordNo = (document.getElementById("apptRecordNo")?.value || "").trim();
        if (!recordNo) {
            resultBox.innerHTML += `<div class="ai-result-error" style="margin-top:12px;">شماره پرونده را وارد کنید.</div>`;
            return;
        }
        const draft = result?.draft && typeof result.draft === "object" ? result.draft : null;
        const recs = Array.isArray(result?.recommendations) ? result.recommendations : [];
        const primary = draft || recs[0] || null;
        if (!primary) {
            resultBox.innerHTML += `<div class="ai-result-error" style="margin-top:12px;">پیشنهادی برای ثبت وجود ندارد.</div>`;
            return;
        }
        function val(r, ...keys) {
            if (!r) return null;
            for (const k of keys) {
                const v = r[k];
                if (v != null && v !== "" && v !== undefined) return String(v);
            }
            return null;
        }
        const weekday = val(primary, "weekday", "weekday_fa", "chosen_weekday");
        const timeStr = val(primary, "time", "start_time");
        const appointmentDate = nextDateForWeekday(weekday, timeStr);
        if (!appointmentDate) {
            resultBox.innerHTML += `<div class="ai-result-error" style="margin-top:12px;">امکان ساخت تاریخ از پیشنهاد وجود ندارد.</div>`;
            return;
        }
        let patient_id;
        try {
            const resolved = await API.resolveRecordNo(recordNo);
            patient_id = resolved?.patient_id;
        } catch (e) {
            resultBox.innerHTML += `<div class="ai-result-error" style="margin-top:12px;">بیمار با شماره پرونده ${escapeHtml(recordNo)} یافت نشد.</div>`;
            return;
        }
        let serviceVal = (document.getElementById("apptService")?.value || "").trim();
        const manualInput = document.getElementById("apptServiceManual");
        if (manualInput && manualInput.value) serviceVal = manualInput.value.trim();
        const insuranceVal = (document.getElementById("apptInsurance")?.value || "").trim() || null;
        const payload = {
            patient_id: Number(patient_id),
            treatment_type: serviceVal,
            payment_type: null,
            appointment_date: appointmentDate,
            notes: "AI recommended booking",
        };
        resultBox.className = "ai-result-card__body ai-result-card__body--loading";
        resultBox.innerHTML = `<div class="ai-result-loading"><div class="ai-result-loading__spinner"></div><span>ثبت نوبت...</span></div>`;
        try {
            const created = await API.createAppointment(payload);
            const dt = created?.appointment_date ? new Date(created.appointment_date) : null;
            const dtStr = dt ? dt.toLocaleDateString("fa-IR", { weekday: "long", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "-";
            resultBox.className = "ai-result-card__body";
            resultBox.innerHTML = `
                <div class="ai-rec-best"><span class="ai-rec-best__label">نوبت ثبت شد</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">شناسه نوبت</span><span class="ai-rec-value">${escapeHtml(String(created?.id ?? "-"))}</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">تاریخ و زمان</span><span class="ai-rec-value">${escapeHtml(dtStr)}</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">پزشک</span><span class="ai-rec-value">${escapeHtml(val(primary, "doctor", "doctor_name", "doctor_display") || "-")}</span></div>
            `;
        } catch (err) {
            const msg = (err && err.message) ? String(err.message) : "خطای نامشخص";
            const is409 = msg.includes("409") || msg.toLowerCase().includes("duplicate") || msg.includes("تکراری");
            resultBox.className = "ai-result-card__body ai-result-card__body--error";
            resultBox.innerHTML = `<div class="ai-result-error">${is409 ? "این نوبت قبلاً ثبت شده است." : escapeHtml(msg)}</div>`;
        }
    }

    function renderRecommendSlotResult(result, showBookButton) {
        if (!result || typeof result !== "object") {
            return `<div class="ai-result-empty">خروجی معتبری از AI دریافت نشد.</div>`;
        }

        const draft = result.draft && typeof result.draft === "object" ? result.draft : null;
        const recs = Array.isArray(result.recommendations) ? result.recommendations : [];
        const top5 = recs.slice(0, 5);
        const primary = draft || recs[0] || null;

        function val(r, ...keys) {
            if (!r) return "-";
            for (const k of keys) {
                const v = r[k];
                if (v != null && v !== "" && v !== undefined) return String(v);
            }
            return "-";
        }

        if (top5.length > 0) {
            const bestScore = val(primary, "score", "confidence", "confidence_score");
            let html = `<div class="ai-rec-best"><span class="ai-rec-best__label">Best AI Choice</span><span class="ai-rec-best__score">Confidence: ${escapeHtml(bestScore)}</span></div>`;
            html += `<div class="ai-rec-table-wrap"><table class="ai-rec-table"><thead><tr><th>Rank</th><th>Weekday</th><th>Time</th><th>Doctor</th><th>Score</th></tr></thead><tbody>`;
            top5.forEach((r, i) => {
                const rank = i + 1;
                const weekday = val(r, "weekday", "weekday_fa", "date");
                const time = val(r, "time", "start_time");
                const doctor = val(r, "doctor", "doctor_name", "doctor_display");
                const score = val(r, "score", "confidence");
                const rowClass = rank === 1 ? " ai-rec-table__row--best" : "";
                html += `<tr class="ai-rec-table__row${rowClass}"><td>${rank}</td><td>${escapeHtml(weekday)}</td><td>${escapeHtml(time)}</td><td>${escapeHtml(doctor)}</td><td>${escapeHtml(score)}</td></tr>`;
            });
            html += `</tbody></table></div>`;
            if (recs.length > 5) {
                html += `<div class="ai-rec-more">${recs.length} total slots — showing top 5</div>`;
            }
            if (showBookButton) {
                html += `<div style="margin-top:16px;"><button type="button" class="ai-book-recommended-btn btn btn--primary">ثبت نوبت پیشنهادی</button></div>`;
            }
            return html;
        }

        if (primary) {
            const suggestedDate = val(primary, "weekday", "weekday_fa", "date", "suggested_date");
            const suggestedTime = val(primary, "time", "start_time", "suggested_time");
            const doctor = val(primary, "doctor", "doctor_name", "doctor_display");
            const confidence = val(primary, "score", "confidence", "confidence_score");
            let html = `
                <div class="ai-rec-best"><span class="ai-rec-best__label">Best AI Choice</span><span class="ai-rec-best__score">Confidence: ${escapeHtml(confidence)}</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">Weekday</span><span class="ai-rec-value">${escapeHtml(suggestedDate)}</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">Time</span><span class="ai-rec-value">${escapeHtml(suggestedTime)}</span></div>
                <div class="ai-rec-row"><span class="ai-rec-label">Doctor</span><span class="ai-rec-value">${escapeHtml(doctor)}</span></div>
            `;
            if (showBookButton) {
                html += `<div style="margin-top:16px;"><button type="button" class="ai-book-recommended-btn btn btn--primary">ثبت نوبت پیشنهادی</button></div>`;
            }
            return html;
        }

        const entries = flattenObject(result);
        if (!entries.length) return `<div class="ai-result-empty">خروجی معتبری از AI دریافت نشد.</div>`;
        return `<div class="ai-rec-fallback">${entries.map(([k, v]) => `<div class="ai-rec-row"><span class="ai-rec-label">${escapeHtml(k)}</span><span class="ai-rec-value">${escapeHtml(String(v ?? "-"))}</span></div>`).join("")}</div>`;
    }

    function flattenObject(obj, prefix = "") {
        const rows = [];

        if (obj === null || obj === undefined) {
            rows.push([prefix || "value", "-"]);
            return rows;
        }

        if (typeof obj !== "object") {
            rows.push([prefix || "value", String(obj)]);
            return rows;
        }

        if (Array.isArray(obj)) {
            if (!obj.length) {
                rows.push([prefix || "list", "[]"]);
                return rows;
            }

            obj.forEach((item, idx) => {
                if (typeof item === "object" && item !== null) {
                    rows.push(...flattenObject(item, `${prefix}[${idx}]`));
                } else {
                    rows.push([`${prefix}[${idx}]`, String(item)]);
                }
            });
            return rows;
        }

        Object.entries(obj).forEach(([key, value]) => {
            const nextKey = prefix ? `${prefix}.${key}` : key;
            if (typeof value === "object" && value !== null) {
                rows.push(...flattenObject(value, nextKey));
            } else {
                rows.push([nextKey, String(value ?? "-")]);
            }
        });

        return rows;
    }

    function renderSimpleTableCard(title, subtitle, columns, rows) {
        const head = columns.map(col => `<th>${escapeHtml(col)}</th>`).join("");
        const body = rows.length
            ? rows.map(row => `
                <tr>
                    ${columns.map(col => `<td>${escapeHtml(row[col] ?? "-")}</td>`).join("")}
                </tr>
            `).join("")
            : `<tr><td colspan="${columns.length}">داده‌ای یافت نشد.</td></tr>`;

        return `
            <div class="card">
                <div class="card__header">
                    <div>
                        <h3 class="card__title">${escapeHtml(title)}</h3>
                        <div class="card__subtitle">${escapeHtml(subtitle)}</div>
                    </div>
                </div>
                <div class="card__body">
                    <div class="table-wrap">
                        <table class="table">
                            <thead><tr>${head}</tr></thead>
                            <tbody>${body}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    function normalizeSuggestionRow(row) {
        if (!row || typeof row !== "object") return {};

        const id =
            row.id ??
            row.suggestion_id ??
            row.suggestionId ??
            row.AppointmentSuggestionId ??
            null;

        const recordNo =
            row.record_no ??
            row.recordNo ??
            row.RecordNo ??
            row.patient_record_no ??
            row.patientRecordNo ??
            null;

        const patientName =
            row.patient_name ??
            row.patient_name_canonical ??
            row.PatientName ??
            row.patient ??
            null;

        const serviceName =
            row.service_name ??
            row.service ??
            row.service_title ??
            null;

        const insuranceName =
            row.insurance_name ??
            row.insurance ??
            row.insurer_name ??
            null;

        const suggestedSlot =
            row.suggested_slot ??
            row.slot ??
            row.suggested_time ??
            null;

        const priorityBand =
            row.priority_band ??
            row.scheduling_band ??
            null;

        const priorityScore =
            row.priority_score ??
            row.scheduling_priority_score ??
            null;

        const accepted = row.accepted;
        const notes = row.notes ?? row.review_notes ?? null;

        let statusText = "Pending";
        if (accepted === 1 || accepted === true) statusText = "Accepted";
        else if (accepted === 0 || accepted === false) statusText = "Rejected";

        return {
            id,
            recordNo,
            patientName,
            serviceName,
            insuranceName,
            suggestedSlot,
            priorityBand,
            priorityScore,
            accepted,
            statusText,
            notes
        };
    }

    function renderAiSuggestionRow(row) {
        const s = normalizeSuggestionRow(row);
        const idDisplay = s.id != null ? String(s.id) : "-";

        return `
            <tr data-suggestion-id="${escapeHtml(idDisplay)}">
                <td>${escapeHtml(idDisplay)}</td>
                <td>${escapeHtml(s.recordNo ?? "-")}</td>
                <td>${escapeHtml(s.patientName ?? "-")}</td>
                <td>${escapeHtml(s.serviceName ?? "-")}</td>
                <td>${escapeHtml(s.insuranceName ?? "-")}</td>
                <td>${escapeHtml(s.suggestedSlot ?? "-")}</td>
                <td>${escapeHtml(s.priorityBand ?? "-")}</td>
                <td>${escapeHtml(s.priorityScore != null ? String(s.priorityScore) : "-")}</td>
                <td>${escapeHtml(s.statusText)}</td>
                <td>${escapeHtml(s.notes ?? "-")}</td>
                <td>
                    <button class="table__action-btn ai-suggestion-accept" data-id="${escapeHtml(idDisplay)}">Accept</button>
                    <button class="table__action-btn ai-suggestion-reject" data-id="${escapeHtml(idDisplay)}">Reject</button>
                </td>
            </tr>
        `;
    }

    async function loadAiSuggestions() {
        const tbody = document.getElementById("aiSuggestionsTbody");
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="11">در حال بارگذاری پیشنهادها...</td>
            </tr>
        `;

        try {
            const payload = await API.getAppointmentSuggestions();
            const rows = Array.isArray(payload?.data)
                ? payload.data
                : Array.isArray(payload)
                    ? payload
                    : [];

            if (!rows.length) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="11">پیشنهاد فعالی برای بررسی وجود ندارد.</td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = rows.map(renderAiSuggestionRow).join("");
        } catch (error) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11">خطا در بارگذاری پیشنهادها: ${escapeHtml(error.message || "خطای نامشخص")}</td>
                </tr>
            `;
        }
    }

    async function reviewAiSuggestion(id, accepted) {
        if (!id) return;

        const notes = accepted
            ? "Accepted from dashboard"
            : "Rejected from dashboard";

        try {
            await API.reviewAppointmentSuggestion(id, {
                accepted,
                notes
            });

            showToast(accepted ? "پیشنهاد پذیرفته شد" : "پیشنهاد رد شد");
            await loadAiSuggestions();
        } catch (error) {
            showToast(error.message || "خطا در ثبت بازبینی پیشنهاد");
        }
    }

    function handleAiSuggestionsClick(e) {
        const target = e.target;
        if (!(target instanceof HTMLElement)) return;

        const id = target.getAttribute("data-id");
        if (!id) return;

        if (target.classList.contains("ai-suggestion-accept")) {
            reviewAiSuggestion(id, true);
        } else if (target.classList.contains("ai-suggestion-reject")) {
            reviewAiSuggestion(id, false);
        }
    }

    function bindAiSuggestionsSection() {
        const refreshBtn = document.getElementById("aiSuggestionsRefreshBtn");
        const tbody = document.getElementById("aiSuggestionsTbody");

        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => {
                loadAiSuggestions();
            });
        }

        if (tbody) {
            tbody.addEventListener("click", handleAiSuggestionsClick);
        }

        loadAiSuggestions();
    }

    function bindVipButtons() {
        document.querySelectorAll("[data-record-no]").forEach(btn => {
            btn.addEventListener("click", async () => {
                const recordNo = btn.getAttribute("data-record-no");
                await openPatientModal(recordNo);
            });
        });
    }

    async function openPatientModal(recordNo) {
        try {
            el.modalRecordNo.textContent = `Record No: ${recordNo}`;
            el.modalBody.innerHTML = `<div class="loading-state">در حال بارگذاری جزئیات بیمار...</div>`;
            el.modal.classList.remove("hidden");

            const data = await API.getPatientDetail(recordNo);
            const p = data.financial_profile || {};
            const o = data.operational_status || {};

            el.modalBody.innerHTML = `
                <div class="detail-grid">
                    <div class="detail-card">
                        <h4>پروفایل مالی</h4>
                        <div class="detail-list">
                            ${detailItem("Financial Tier", p.financial_tier)}
                            ${detailItem("Financial Score", p.financial_value_score)}
                            ${detailItem("Lifetime Txn Count", p.lifetime_txn_count)}
                            ${detailItem("Lifetime Revenue", formatMoney(p.lifetime_net_received))}
                            ${detailItem("Patient Paid", formatMoney(p.lifetime_patient_paid))}
                            ${detailItem("Insurer Paid", formatMoney(p.lifetime_insurer_paid))}
                            ${detailItem("Negative Net", formatMoney(p.lifetime_negative_net))}
                            ${detailItem("Negative Txn Count", p.lifetime_negative_txn_count)}
                            ${detailItem("Cash Txn Count", p.cash_txn_count)}
                            ${detailItem("Insurance Txn Count", p.insurance_txn_count)}
                            ${detailItem("Recent Txn Count", p.recent_txn_count)}
                            ${detailItem("Recent Net Revenue", formatMoney(p.recent_net_received))}
                        </div>
                    </div>

                    <div class="detail-card">
                        <h4>وضعیت عملیاتی</h4>
                        <div class="detail-list">
                            ${detailItem("Record No", p.record_no)}
                            ${detailItem("First Payment", p.first_payment_date_raw)}
                            ${detailItem("Last Payment", p.last_payment_date_raw)}
                            ${detailItem("Has Date Range", p.has_date_range)}
                            ${detailItem("In Follow-up Queue", o.in_followup_queue)}
                            ${detailItem("Follow-up Action", o.followup_action_type)}
                            ${detailItem("In Scheduling Top300", o.in_scheduling_top300)}
                            ${detailItem("Scheduling Band", o.scheduling_band)}
                            ${detailItem("Scheduling Score", o.scheduling_priority_score)}
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            el.modalBody.innerHTML = `<div class="error-state">خطا در دریافت جزئیات: ${escapeHtml(error.message)}</div>`;
        }
    }

    function detailItem(label, value) {
        let display = "-";
        if (value != null && value !== "") {
            if (typeof value === "object") {
                try {
                    display = JSON.stringify(value, null, 2);
                } catch {
                    display = String(value);
                }
            } else {
                display = String(value);
            }
        }
        return `
            <div class="detail-item">
                <div class="detail-item__label">${escapeHtml(label)}</div>
                <div class="detail-item__value">${escapeHtml(display)}</div>
            </div>
        `;
    }

    function bindGlobalEvents() {
        window.addEventListener("hashchange", render);

        el.refreshBtn.addEventListener("click", async () => {
            await render();
            showToast("داشبورد بروزرسانی شد");
        });

        el.closeModalBtn.addEventListener("click", closeModal);
        el.modal.addEventListener("click", (e) => {
            if (e.target.dataset.close === "true") closeModal();
        });
    }

    function closeModal() {
        el.modal.classList.add("hidden");
    }

    async function init() {
        bindGlobalEvents();
        await render();
    }

    return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);