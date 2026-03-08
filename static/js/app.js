/**
 * Atieh Clinic Dashboard – App logic and pages
 */
(function () {
    'use strict';

    const API = window.AtiehAPI;
    const $ = id => document.getElementById(id);
    const $q = (el, sel) => (el || document).querySelector(sel);
    const $qa = (el, sel) => Array.from((el || document).querySelectorAll(sel));

    let currentRoute = '/';
    let selectedPatient = null;
    let selectedSlot = null;
    let treatmentTypes = [];
    let paymentTypes = [];

    // ── Routing ─────────────────────────────────────────────────────────────
    function getRoute() {
        const hash = window.location.hash || '#/';
        return hash.slice(1) || '/';
    }

    function navigate(route) {
        window.location.hash = route || '/';
    }

    function render(route) {
        currentRoute = route || getRoute();
        $qa('.nav-item').forEach(a => {
            a.classList.toggle('active', a.getAttribute('data-route') === currentRoute || (currentRoute === '/' && a.getAttribute('data-route') === '/'));
        });
        const titles = { '/': 'داشبورد', '/appointment': 'نوبت جدید', '/followup': 'صف پیگیری روزانه', '/top300': 'اولویت نوبت ۳۰۰', '/priority': 'اولویت AI', '/patients': 'جستجوی بیمار' };
        const titleEl = $('page-title');
        const subtitleEl = $('page-subtitle');
        if (titleEl) titleEl.textContent = titles[currentRoute] || 'داشبورد';
        const subtitles = { '/': 'خلاصه وضعیت عملیاتی', '/appointment': 'ثبت نوبت با پیشنهاد AI', '/followup': 'صف پیگیری روزانه متعادل', '/top300': '۳۰۰ بیمار برتر', '/priority': 'فیلتر بر اساس باند و نوع اقدام', '/patients': 'جستجو در صف قابل تماس' };
        if (subtitleEl) subtitleEl.textContent = subtitles[currentRoute] || '';
        const content = $('page-content');
        if (!content) { console.error('page-content not found'); return; }
        if (currentRoute === '/') renderDashboard(content);
        else if (currentRoute === '/appointment') renderAppointment(content);
        else if (currentRoute === '/followup') renderFollowup(content);
        else if (currentRoute === '/top300') renderTop300(content);
        else if (currentRoute === '/priority') renderPriority(content);
        else if (currentRoute === '/patients') renderPatients(content);
    }

    // ── Toast ───────────────────────────────────────────────────────────────
    function toast(msg, type = 'info') {
        const el = $('toast');
        if (!el) return;
        el.textContent = msg;
        el.className = 'toast show';
        setTimeout(() => el.classList.remove('show'), 3000);
    }

    // ── Reusable components ─────────────────────────────────────────────────
    function Loading() { return '<div class="loading">در حال بارگذاری...</div>'; }
    function Empty(msg) { return '<div class="empty">' + (msg || 'هیچ داده‌ای یافت نشد') + '</div>'; }
    function Error(msg) { return '<div class="error">' + (msg || 'خطا در بارگذاری') + '</div>'; }

    function fmtNum(n) { return n != null ? Number(n).toLocaleString('fa-IR') : '–'; }

    function badgeClass(score) {
        if (typeof score !== 'number') return 'badge--neutral';
        if (score >= 90) return 'badge--danger';
        if (score >= 70) return 'badge--warning';
        return 'badge--accent';
    }

    // ── Dashboard ───────────────────────────────────────────────────────────
    async function renderDashboard(container) {
        container.innerHTML = Loading();
        try {
            const d = await API.getDashboardSummary();
            container.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-card stat-card--accent">
                        <div class="stat-card__value">${fmtNum(d.total_followup_contactable)}</div>
                        <div class="stat-card__label">پیگیری قابل تماس</div>
                    </div>
                    <div class="stat-card stat-card--accent">
                        <div class="stat-card__value">${fmtNum(d.total_daily_balanced)}</div>
                        <div class="stat-card__label">صف روزانه متعادل</div>
                    </div>
                    <div class="stat-card stat-card--accent">
                        <div class="stat-card__value">${fmtNum(d.total_scheduling_top300)}</div>
                        <div class="stat-card__label">اولویت نوبت ۳۰۰</div>
                    </div>
                    <div class="stat-card stat-card--danger">
                        <div class="stat-card__value">${fmtNum(d.critical_priority_count)}</div>
                        <div class="stat-card__label">بحرانی</div>
                    </div>
                    <div class="stat-card stat-card--warning">
                        <div class="stat-card__value">${fmtNum(d.high_priority_count)}</div>
                        <div class="stat-card__label">بالا</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-card__value">${fmtNum(d.medium_priority_count)}</div>
                        <div class="stat-card__label">متوسط</div>
                    </div>
                </div>
                <div class="quick-links" style="margin-top:1.5rem">
                    <a href="#/followup" class="quick-link">صف پیگیری روزانه</a>
                    <a href="#/top300" class="quick-link">اولویت نوبت ۳۰۰</a>
                    <a href="#/priority" class="quick-link">اولویت AI</a>
                    <a href="#/appointment" class="quick-link">نوبت جدید</a>
                    <a href="#/patients" class="quick-link">جستجوی بیمار</a>
                </div>
            `;
        } catch (e) {
            container.innerHTML = Error('خطا در بارگذاری داشبورد');
        }
    }

    // ── Data table (reusable, sortable) ─────────────────────────────────────
    function renderTable(container, columns, rows, opts = {}) {
        if (!rows || rows.length === 0) {
            container.innerHTML = Empty(opts.emptyMsg);
            return;
        }
        let sortedRows = rows.slice();
        let sortCol = null;
        let sortDir = 1;

        function render() {
            const th = columns.map((c, i) => {
                const isSorted = sortCol === i;
                const arrow = isSorted ? (sortDir > 0 ? ' ▲' : ' ▼') : '';
                return '<th class="th-sort" data-col="' + i + '">' + c.label + arrow + '</th>';
            }).join('');
            const trs = sortedRows.map(r => {
                const tds = columns.map(c => {
                    let v = c.get ? c.get(r) : (r[c.key] ?? '–');
                    if (c.badge) v = '<span class="badge ' + badgeClass(v) + '">' + v + '</span>';
                    if (c.fmt === 'number') v = fmtNum(v);
                    return '<td>' + (v != null && v !== '' ? v : '–') + '</td>';
                }).join('');
                return '<tr>' + tds + '</tr>';
            }).join('');
            container.innerHTML = '<div class="table-wrap"><table class="table"><thead><tr>' + th + '</tr></thead><tbody>' + trs + '</tbody></table></div>';
            container.querySelectorAll('.th-sort').forEach(th => {
                th.addEventListener('click', () => {
                    const col = +th.dataset.col;
                    if (sortCol === col) sortDir *= -1; else { sortCol = col; sortDir = 1; }
                    const k = columns[col].key;
                    sortedRows.sort((a, b) => {
                        const va = a[k];
                        const vb = b[k];
                        if (va == null && vb == null) return 0;
                        if (va == null) return sortDir;
                        if (vb == null) return -sortDir;
                        return (va < vb ? -1 : va > vb ? 1 : 0) * sortDir;
                    });
                    render();
                });
            });
        }
        render();
    }

    // ── Followup page ───────────────────────────────────────────────────────
    async function renderFollowup(container) {
        const search = (container.getAttribute('data-search') || '').trim();
        container.innerHTML = Loading();
        try {
            const res = await API.getFollowupDaily({ limit: 500, search: search || undefined });
            const cols = [
                { label: 'نام بیمار', key: 'patient_name_canonical' },
                { label: 'موبایل', key: 'mobile_canonical' },
                { label: 'ردۀ مالی', key: 'financial_tier' },
                { label: 'نوع اقدام', key: 'action_type' },
                { label: 'امتیاز', key: 'action_priority_score' },
                { label: 'درآمد کل', key: 'lifetime_net_received', fmt: 'number' },
                { label: 'آخرین پرداخت', key: 'last_payment_date_raw' },
                { label: 'توصیه پیگیری', key: 'followup_recommendation' }
            ];
            container.innerHTML = `
                <div class="panel">
                    <div class="panel__header">
                        <div class="toolbar">
                            <input type="text" class="input" id="followup-search" placeholder="جستجو نام یا موبایل..." value="${(search || '')}">
                            <button class="btn btn--outline" id="followup-refresh">بروزرسانی</button>
                        </div>
                    </div>
                    <div class="panel__body">
                        <div id="followup-table"></div>
                    </div>
                </div>
            `;
            renderTable($('followup-table'), cols, res.data || []);
            $('followup-search').addEventListener('input', debounce(() => {
                container.setAttribute('data-search', $('followup-search').value);
                renderFollowup(container);
            }, 400));
            $('followup-refresh').addEventListener('click', () => renderFollowup(container));
        } catch (e) {
            container.innerHTML = Error();
        }
    }

    // ── Top300 page ─────────────────────────────────────────────────────────
    async function renderTop300(container) {
        const search = (container.getAttribute('data-search') || '').trim();
        container.innerHTML = Loading();
        try {
            const res = await API.getSchedulingTop300({ limit: 300, search: search || undefined });
            const cols = [
                { label: 'نام بیمار', key: 'patient_name_canonical' },
                { label: 'موبایل', key: 'mobile_canonical' },
                { label: 'ردۀ مالی', key: 'financial_tier' },
                { label: 'نوع اقدام', key: 'action_type' },
                { label: 'امتیاز', key: 'scheduling_priority_score', badge: true },
                { label: 'باند', key: 'scheduling_band' },
                { label: 'درآمد کل', key: 'lifetime_net_received', fmt: 'number' },
                { label: 'آخرین پرداخت', key: 'last_payment_date_raw' }
            ];
            container.innerHTML = `
                <div class="panel">
                    <div class="panel__header">
                        <div class="toolbar">
                            <input type="text" class="input" id="top300-search" placeholder="جستجو نام یا موبایل..." value="${(search || '')}">
                            <button class="btn btn--outline" id="top300-refresh">بروزرسانی</button>
                        </div>
                    </div>
                    <div class="panel__body">
                        <div id="top300-table"></div>
                    </div>
                </div>
            `;
            renderTable($('top300-table'), cols, res.data || []);
            $('top300-search').addEventListener('input', debounce(() => {
                container.setAttribute('data-search', $('top300-search').value);
                renderTop300(container);
            }, 400));
            $('top300-refresh').addEventListener('click', () => renderTop300(container));
        } catch (e) {
            container.innerHTML = Error();
        }
    }

    // ── Priority page ───────────────────────────────────────────────────────
    async function renderPriority(container) {
        const band = container.getAttribute('data-band') || '';
        const action = container.getAttribute('data-action') || '';
        const tier = container.getAttribute('data-tier') || '';
        container.innerHTML = Loading();
        try {
            const res = await API.getSchedulingPriority({
                limit: 500,
                scheduling_band: band || undefined,
                action_type: action || undefined,
                financial_tier: tier || undefined
            });
            const cols = [
                { label: 'نام بیمار', key: 'patient_name_canonical' },
                { label: 'موبایل', key: 'mobile_canonical' },
                { label: 'ردۀ مالی', key: 'financial_tier' },
                { label: 'نوع اقدام', key: 'action_type' },
                { label: 'باند', key: 'scheduling_band' },
                { label: 'امتیاز', key: 'scheduling_priority_score' },
                { label: 'درآمد کل', key: 'lifetime_net_received', fmt: 'number' },
                { label: 'آخرین پرداخت', key: 'last_payment_date_raw' }
            ];
            container.innerHTML = `
                <div class="panel">
                    <div class="panel__header">
                <div class="toolbar filters">
                    <select class="input" id="filter-band"><option value="">همه باندها</option><option value="CRITICAL_PRIORITY">بحرانی</option><option value="HIGH_PRIORITY">بالا</option><option value="MEDIUM_PRIORITY">متوسط</option></select>
                    <select class="input" id="filter-action"><option value="">همه اقدامات</option><option value="VIP_ACTIVE">VIP_ACTIVE</option><option value="VIP_RECALL">VIP_RECALL</option><option value="HIGH_ACTIVE">HIGH_ACTIVE</option><option value="HIGH_RECALL">HIGH_RECALL</option><option value="PRIORITY_ACTIVE">PRIORITY_ACTIVE</option><option value="MEDIUM_WARM">MEDIUM_WARM</option><option value="MEDIUM_REACTIVATE">MEDIUM_REACTIVATE</option><option value="NORMAL">NORMAL</option></select>
                    <select class="input" id="filter-tier"><option value="">همه رده‌ها</option><option value="VIP">VIP</option><option value="HIGH">HIGH</option><option value="MEDIUM">MEDIUM</option><option value="LOW">LOW</option></select>
                    <button class="btn btn--outline" id="priority-refresh">بروزرسانی</button>
                </div>
                    </div>
                    <div class="panel__body">
                <div id="priority-table"></div>
                    </div>
                </div>
            `;
            $('filter-band').value = band;
            $('filter-action').value = action;
            $('filter-tier').value = tier;
            renderTable($('priority-table'), cols, res.data || []);
            $('filter-band').addEventListener('change', () => { container.setAttribute('data-band', $('filter-band').value); renderPriority(container); });
            $('filter-action').addEventListener('change', () => { container.setAttribute('data-action', $('filter-action').value); renderPriority(container); });
            $('filter-tier').addEventListener('change', () => { container.setAttribute('data-tier', $('filter-tier').value); renderPriority(container); });
            $('priority-refresh').addEventListener('click', () => renderPriority(container));
        } catch (e) {
            container.innerHTML = Error();
        }
    }

    // ── Patients search ─────────────────────────────────────────────────────
    async function renderPatients(container) {
        const search = (container.getAttribute('data-search') || '').trim();
        container.innerHTML = `
            <div class="panel">
                <div class="panel__header">
                    <label class="form-label">جستجو در صف پیگیری قابل تماس</label>
                    <input type="text" class="input" id="patients-search" placeholder="نام یا موبایل..." value="${search}" style="max-width:320px">
                </div>
                <div class="panel__body">
                    <div id="patients-table"></div>
                </div>
            </div>
        `;
        const tableEl = $('patients-table');
        tableEl.innerHTML = Loading();
        try {
            const res = await API.getFollowupContactable({ limit: 300, search: search || undefined });
            const cols = [
                { label: 'نام بیمار', key: 'patient_name_canonical' },
                { label: 'موبایل', key: 'mobile_canonical' },
                { label: 'ردۀ مالی', key: 'financial_tier' },
                { label: 'نوع اقدام', key: 'action_type' },
                { label: 'امتیاز', key: 'action_priority_score' },
                { label: 'درآمد کل', key: 'lifetime_net_received', fmt: 'number' },
                { label: 'آخرین پرداخت', key: 'last_payment_date_raw' },
                { label: 'توصیه', key: 'followup_recommendation' }
            ];
            renderTable(tableEl, cols, res.data || []);
        } catch (e) {
            tableEl.innerHTML = Error();
        }
        $('patients-search').addEventListener('input', debounce(() => {
            container.setAttribute('data-search', $('patients-search').value);
            renderPatients(container);
        }, 400));
    }

    // ── New Appointment ─────────────────────────────────────────────────────
    async function renderAppointment(container) {
        container.innerHTML = Loading();
        try {
        if (typeof API === 'undefined') {
            container.innerHTML = Error('خطا: API بارگذاری نشده.');
            return;
        }
        if (!treatmentTypes.length) {
            try { treatmentTypes = await API.getTreatmentTypes(); } catch (_) {}
            treatmentTypes = Array.isArray(treatmentTypes) ? treatmentTypes : (treatmentTypes?.value || []);
        }
        if (!paymentTypes.length) {
            try { paymentTypes = await API.getPaymentTypes(); } catch (_) {}
            paymentTypes = Array.isArray(paymentTypes) ? paymentTypes : (paymentTypes?.value || []);
        }
        const treatOpts = (treatmentTypes || []).map(t => '<option value="' + (t.id || t.value || '') + '">' + (t.label || t.name || t.id || '') + '</option>').join('');
        const payOpts = (paymentTypes || []).map(p => '<option value="' + (p.id || p.value || '') + '">' + (p.label || p.name || p.id || '') + '</option>').join('');
        container.innerHTML = `
            <div class="card" style="max-width:560px">
                <h3 class="card-title">ثبت نوبت جدید</h3>
                <div class="form-group autocomplete">
                    <label class="form-label">بیمار</label>
                    <input type="text" class="input" id="apt-patient" placeholder="نام یا موبایل..." autocomplete="off">
                    <div id="apt-results" class="autocomplete-results" style="display:none"></div>
                </div>
                <div id="apt-financial" class="patient-financial" style="display:none"></div>
                <div class="form-group">
                    <label class="form-label">نوع درمان</label>
                    <select class="input" id="apt-treatment"><option value="">انتخاب...</option>${treatOpts}</select>
                </div>
                <div class="form-group">
                    <label class="form-label">نوع پرداخت</label>
                    <select class="input" id="apt-payment"><option value="">انتخاب...</option>${payOpts}</select>
                </div>
                <div class="form-group">
                    <label class="form-label">تاریخ/زمان (اختیاری)</label>
                    <input type="datetime-local" class="input" id="apt-date">
                </div>
                <div class="form-group">
                    <label class="form-label">یادداشت</label>
                    <textarea class="input" id="apt-notes" rows="2"></textarea>
                </div>
                <div style="margin-top:1rem">
                    <button class="btn btn--outline" id="apt-suggest">پیشنهاد زمان</button>
                    <button class="btn btn--primary" id="apt-submit" disabled>ثبت نوبت</button>
                </div>
            </div>
            <div class="card" style="margin-top:1rem;max-width:400px">
                <h3 class="card-title">پیشنهادات AI</h3>
                <div id="apt-ai-summary">امتیاز پایه: – | امتیاز AI: –</div>
                <div id="apt-slots" class="slots"></div>
            </div>
        `;

        const patientInput = $('apt-patient');
        const resultsEl = $('apt-results');
        const financialEl = $('apt-financial');

        patientInput.addEventListener('input', debounce(async () => {
            const q = patientInput.value.trim();
            if (q.length < 2) { resultsEl.style.display = 'none'; return; }
            try {
                const res = await API.getPatients({ search: q, limit: 10 });
                const list = Array.isArray(res) ? res : [];
                if (!list.length) { resultsEl.innerHTML = '<div class="autocomplete-item">یافت نشد</div>'; }
                else {
                    resultsEl.innerHTML = list.map(p => '<div class="autocomplete-item" data-id="' + p.id + '" data-name="' + (p.name||'') + '" data-phone="' + (p.phone||'') + '">' + (p.name||'') + ' – ' + (p.phone||'') + '</div>').join('');
                    resultsEl.querySelectorAll('.autocomplete-item').forEach(el => {
                        el.addEventListener('click', () => {
                            selectedPatient = { id: el.dataset.id, name: el.dataset.name, phone: el.dataset.phone };
                            patientInput.value = (el.dataset.name || '') + ' – ' + (el.dataset.phone || '');
                            resultsEl.style.display = 'none';
                            updateAptSubmit();
                            fetchFinancialAndAI();
                        });
                    });
                }
                resultsEl.style.display = 'block';
            } catch (_) { resultsEl.style.display = 'none'; }
        }, 300));

        patientInput.addEventListener('blur', () => setTimeout(() => { resultsEl.style.display = 'none'; }, 200));

        function fetchFinancialAndAI() {
            const phone = selectedPatient?.phone || '';
            financialEl.style.display = 'none';
            if (!phone) return;
            API.getPatientLookup(phone).then(d => {
                if (d.found && d.data) {
                    financialEl.innerHTML = '<span class="badge badge--accent">' + (d.data.financial_tier||'') + '</span> <span class="badge badge--neutral">' + (d.data.action_type||'') + '</span> امتیاز: ' + (d.data.scheduling_priority_score ?? d.data.action_priority_score ?? '–');
                    financialEl.style.display = 'flex';
                }
            }).catch(() => {});
            if (selectedPatient?.id) API.patientHistoryScore(selectedPatient.id).then(h => {
                $('apt-ai-summary').textContent = 'امتیاز پایه: ' + (h.history_score != null ? h.history_score.toFixed(1) : '–');
            }).catch(() => {});
        }

        function updateAptSubmit() {
            const hasPatient = !!selectedPatient;
            const treatment = $('apt-treatment')?.value;
            const date = $('apt-date')?.value || selectedSlot;
            $('apt-submit').disabled = !(hasPatient && treatment && (date || selectedSlot));
        }

        $('apt-treatment').addEventListener('change', () => { updateAptSubmit(); if (selectedPatient) API.predictAppointment({ patient_id: selectedPatient.id, treatment_type: $('apt-treatment').value, payment_type: $('apt-payment').value || undefined }).then(d => { $('apt-ai-summary').textContent = 'امتیاز پایه: ' + (d.history_score != null ? d.history_score.toFixed(1) : '–') + ' | امتیاز AI: ' + (d.ai_priority_score != null ? d.ai_priority_score.toFixed(1) : '–'); }).catch(() => {}); });
        $('apt-payment').addEventListener('change', updateAptSubmit);
        $('apt-date').addEventListener('change', updateAptSubmit);

        $('apt-suggest').addEventListener('click', async () => {
            if (!selectedPatient || !$('apt-treatment').value) { toast('بیمار و نوع درمان را انتخاب کنید', 'error'); return; }
            try {
                const res = await API.suggestSlots({ treatment_type: $('apt-treatment').value, patient_id: selectedPatient.id, max_suggestions: 5 });
                const slots = res.suggested_times || res.suggestions || [];
                const slotsEl = $('apt-slots');
                slotsEl.innerHTML = '';
                slots.forEach(s => {
                    const d = new Date(s);
                    const btn = document.createElement('button');
                    btn.className = 'slot-btn';
                    btn.textContent = d.toLocaleDateString('fa-IR') + ' ' + d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
                    btn.addEventListener('click', () => {
                        $qa('.slot-btn').forEach(b => b.classList.remove('selected'));
                        btn.classList.add('selected');
                        selectedSlot = s;
                        updateAptSubmit();
                    });
                    slotsEl.appendChild(btn);
                });
                toast(slots.length ? slots.length + ' زمان پیشنهاد شد' : 'زمانی یافت نشد');
            } catch (e) { toast('خطا'); }
        });

        $('apt-submit').addEventListener('click', async () => {
            if (!selectedPatient || !$('apt-treatment').value) return;
            const date = selectedSlot || $('apt-date').value;
            if (!date) { toast('زمان را انتخاب کنید'); return; }
            try {
                await API.createAppointment({ patient_id: selectedPatient.id, treatment_type: $('apt-treatment').value, appointment_date: new Date(date).toISOString(), payment_type: $('apt-payment').value || undefined, notes: $('apt-notes').value || undefined });
                toast('نوبت ثبت شد');
                selectedPatient = null; selectedSlot = null;
                patientInput.value = ''; $('apt-treatment').value = ''; $('apt-payment').value = ''; $('apt-date').value = ''; $('apt-notes').value = '';
                $('apt-slots').innerHTML = ''; financialEl.style.display = 'none';
            } catch (e) { toast('خطا در ثبت'); }
        });
        } catch (e) {
            container.innerHTML = Error('خطا در بارگذاری: ' + (e.message || 'نامشخص'));
        }
    }

    function debounce(fn, ms) {
        let t;
        return function () { clearTimeout(t); t = setTimeout(() => fn.apply(this, arguments), ms); };
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    window.addEventListener('hashchange', () => render());
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => render());
    } else {
        render();
    }
})();
