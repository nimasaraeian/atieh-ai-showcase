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

        if (state.route === "/") return renderDashboard();
        if (state.route === "/followup") return renderFollowup();
        if (state.route === "/top300") return renderTop300();
        if (state.route === "/priority") return renderPriority();
        if (state.route === "/patients") return renderPatients();
        if (state.route === "/appointment") return renderAppointment();

        setPageMeta("صفحه یافت نشد", "مسیر انتخاب شده معتبر نیست");
        el.content.innerHTML = `<div class="empty-state">این بخش هنوز پیاده‌سازی نشده است.</div>`;
    }

    async function renderDashboard() {
        setPageMeta("داشبورد مدیریتی", "نمای کلی وضعیت مالی، عملیاتی و هوشمند کلینیک");
        setLoading("در حال بارگذاری داشبورد...");

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
            `;

            bindVipButtons();
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
                                <th>سطح مالی</th>
                                <th>در Top300</th>
                                <th>در صف پیگیری</th>
                                <th>درآمد</th>
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

        tbody.innerHTML = `<tr><td colspan="8">در حال جستجو...</td></tr>`;

        try {
            const result = await API.getPatientsSearch(q, 50, 0);
            const rows = Array.isArray(result?.data) ? result.data : [];
            const count = result?.count ?? rows.length;

            tbody.innerHTML = "";

            if (rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8">بیماری پیدا نشد</td></tr>`;
                return;
            }

            rows.forEach(p => {
                const tr = document.createElement("tr");
                const recordNo = p.record_no ?? p.recordNo ?? "-";
                const hasDetail = recordNo && String(recordNo) !== "-";
                const patientName = p.patient_name ?? p.patient_name_canonical ?? "-";
                const mobile = p.mobile ?? p.mobile_canonical ?? "-";
                const inTop300 = p.in_top300 ? "بله" : "-";
                const inFollowup = p.in_followup_queue ? "بله" : "-";
                const revenue = p.lifetime_net_received != null
                    ? String(Math.round(Number(p.lifetime_net_received)).toLocaleString())
                    : "-";
                tr.innerHTML = `
                    <td>${escapeHtml(patientName)}</td>
                    <td>${escapeHtml(mobile)}</td>
                    <td>${escapeHtml(recordNo)}</td>
                    <td>${escapeHtml(p.financial_tier ?? "-")}</td>
                    <td>${escapeHtml(inTop300)}</td>
                    <td>${escapeHtml(inFollowup)}</td>
                    <td>${escapeHtml(revenue)}</td>
                    <td>${hasDetail ? `<button class="table__action-btn" data-record-no="${escapeHtml(String(recordNo))}">مشاهده</button>` : "-"}</td>
                `;
                tbody.appendChild(tr);
            });

            bindVipButtons();
        } catch (err) {
            console.error("patient search error:", err);
            const msg = err && err.message ? String(err.message) : "خطا در اتصال به سرور";
            tbody.innerHTML = `<tr><td colspan="8">${escapeHtml(msg)}</td></tr>`;
        }
    }

    async function renderAppointment() {
        setPageMeta("نوبت جدید", "اتصال مستقیم به AI Scheduling Engine");
        el.content.innerHTML = `
            <div class="grid" style="grid-template-columns: 1.1fr 0.9fr;">
                <div class="card">
                    <div class="card__header">
                        <div>
                            <h3 class="card__title">فرم پیشنهاد نوبت هوشمند</h3>
                            <div class="card__subtitle">خدمات، بیمه و پارامترهای کلیدی را وارد کنید</div>
                        </div>
                    </div>
                    <div class="card__body">
                        <form id="appointmentAiForm" class="detail-list">
                            <div class="detail-item" style="border-bottom:0; padding-bottom:0;">
                                <div style="width:100%;">
                                    <div class="detail-item__label" style="margin-bottom:8px;">Record No</div>
                                    <input id="apptRecordNo" type="text" placeholder="مثلاً 139990" style="width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff;" />
                                </div>
                            </div>

                            <div class="detail-item" style="border-bottom:0; padding-bottom:0;">
                                <div style="width:100%;">
                                    <div class="detail-item__label" style="margin-bottom:8px;">کد خدمت / Service</div>
                                    <select id="apptService" style="width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff;">
                                        <option value="">در حال بارگذاری...</option>
                                    </select>
                                </div>
                            </div>

                            <div class="detail-item" style="border-bottom:0; padding-bottom:0;">
                                <div style="width:100%;">
                                    <div class="detail-item__label" style="margin-bottom:8px;">بیمه / Insurance</div>
                                    <select id="apptInsurance" style="width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff;">
                                        <option value="">در حال بارگذاری...</option>
                                    </select>
                                </div>
                            </div>

                            <div class="detail-item" style="border-bottom:0; padding-bottom:0;">
                                <div style="width:100%;">
                                    <div class="detail-item__label" style="margin-bottom:8px;">روز هفته ترجیحی</div>
                                    <select id="apptWeekday" style="width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff;">
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
                            </div>

                            <div class="detail-item" style="border-bottom:0; padding-bottom:0;">
                                <div style="width:100%;">
                                    <div class="detail-item__label" style="margin-bottom:8px;">درمان نیمه‌کاره / Backlog (اختیاری)</div>
                                    <input id="apptBacklog" type="text" placeholder="مثلاً درمان ریشه" style="width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff;" />
                                </div>
                            </div>

                            <div style="display:flex; gap:12px; margin-top:8px;">
                                <button class="btn btn--primary" type="submit">دریافت پیشنهاد AI</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="card">
                    <div class="card__header">
                        <div>
                            <h3 class="card__title">نتیجه پیشنهاد نوبت</h3>
                            <div class="card__subtitle">خروجی AI Scheduling Engine</div>
                        </div>
                    </div>
                    <div class="card__body">
                        <div id="appointmentAiResult" class="empty-state">هنوز درخواستی ارسال نشده است.</div>
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
                serviceSelect.innerHTML = `<option value="">بدون کاتالوگ - لطفاً دستی وارد کنید</option>`;
                serviceSelect.setAttribute("data-manual", "true");
                const manualWrap = serviceSelect.closest(".detail-item");
                if (manualWrap && !document.getElementById("apptServiceManual")) {
                    const manualInput = document.createElement("input");
                    manualInput.id = "apptServiceManual";
                    manualInput.type = "text";
                    manualInput.placeholder = "نام خدمت (فارسی) مثلاً کشیدن دندان";
                    manualInput.style.cssText = "width:100%; padding:14px 16px; border-radius:14px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03); color:#fff; margin-top:8px;";
                    manualWrap.appendChild(manualInput);
                }
            }

            insuranceSelect.innerHTML = `<option value="">انتخاب بیمه</option>` +
                insurances.map(item => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join("");
        } catch (error) {
            console.error("catalog load error:", error);
            serviceSelect.innerHTML = `<option value="">خطا در بارگذاری خدمات</option>`;
            insuranceSelect.innerHTML = `<option value="">خطا در بارگذاری بیمه‌ها</option>`;
        }

        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            let serviceVal = (document.getElementById("apptService")?.value || "").trim();
            const manualInput = document.getElementById("apptServiceManual");
            if (manualInput && manualInput.value) serviceVal = manualInput.value.trim();
            if (!serviceVal) {
                resultBox.innerHTML = `<div class="error-state">لطفاً یک خدمت را انتخاب یا وارد کنید.</div>`;
                return;
            }

            const payload = {
                service: serviceVal,
                insurance: (document.getElementById("apptInsurance")?.value || "").trim() || null,
                backlog: (document.getElementById("apptBacklog")?.value || "").trim() || null,
                doctor: null,
                weekday: (document.getElementById("apptWeekday")?.value || "").trim() || null
            };

            resultBox.innerHTML = `<div class="loading-state">در حال دریافت پیشنهاد AI...</div>`;

            try {
                const result = await API.recommendSlot(payload);
                resultBox.innerHTML = renderRecommendSlotResult(result);
            } catch (error) {
                const msg = (error && error.message) ? String(error.message) : "خطای نامشخص";
                resultBox.innerHTML = `<div class="error-state">خطا در دریافت پیشنهاد: ${escapeHtml(msg)}</div>`;
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

    function renderRecommendSlotResult(result) {
        if (!result || typeof result !== "object") {
            return `<div class="empty-state">خروجی معتبری از AI دریافت نشد.</div>`;
        }

        const parts = [];

        if (result.run_id) {
            parts.push(`<div class="detail-item"><div class="detail-item__label">Run ID</div><div class="detail-item__value">${escapeHtml(String(result.run_id))}</div></div>`);
        }

        if (result.input && typeof result.input === "object") {
            parts.push(`<h4 style="margin:16px 0 8px;">ورودی</h4><div class="detail-list">${
                Object.entries(result.input).map(([k, v]) => detailItem(k, v)).join("")
            }</div>`);
        }

        if (result.draft && typeof result.draft === "object" && Object.keys(result.draft).length > 0) {
            parts.push(`<h4 style="margin:16px 0 8px;">پیشنهاد اصلی</h4><div class="detail-list">${
                Object.entries(result.draft).map(([k, v]) => detailItem(k, v)).join("")
            }</div>`);
        }

        const recs = Array.isArray(result.recommendations) ? result.recommendations : [];
        if (recs.length > 0) {
            const cols = recs[0] && typeof recs[0] === "object" ? Object.keys(recs[0]) : [];
            const headerRow = cols.length ? `<tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join("")}</tr>` : "";
            const bodyRows = recs.slice(0, 10).map(r =>
                `<tr>${cols.map(c => `<td>${escapeHtml(String(r[c] ?? "-"))}</td>`).join("")}</tr>`
            ).join("");
            parts.push(`<h4 style="margin:16px 0 8px;">پیشنهادات (${recs.length})</h4><div class="table-wrap"><table class="table"><thead>${headerRow}</thead><tbody>${bodyRows}</tbody></table></div>`);
        }

        if (result.counts && typeof result.counts === "object") {
            parts.push(`<div class="detail-list" style="margin-top:12px;">${
                Object.entries(result.counts).map(([k, v]) => detailItem(k, v)).join("")
            }</div>`);
        }

        if (parts.length === 0) {
            const entries = flattenObject(result);
            if (!entries.length) return `<div class="empty-state">خروجی معتبری از AI دریافت نشد.</div>`;
            parts.push(`<div class="detail-list">${entries.map(([k, v]) => detailItem(k, v)).join("")}</div>`);
        }

        return `<div class="detail-card"><h4>پاسخ AI Scheduling Engine</h4>${parts.join("")}</div>`;
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