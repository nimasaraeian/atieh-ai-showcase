/**
 * API layer for Atieh Clinic Dashboard
 * Centralized fetch wrapper and endpoint functions
 */
(function (global) {
    'use strict';

    const origin = window.location.origin;
    const BASE = (origin && origin.startsWith('http')) ? origin : 'http://127.0.0.1:8000';

    async function request(path, opts = {}) {
        const url = path.startsWith('http') ? path : BASE + path;
        const res = await fetch(url, {
            headers: { 'Accept': 'application/json', ...opts.headers },
            ...opts
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const ct = res.headers.get('content-type');
        if (ct && ct.includes('application/json')) return res.json();
        return res.text();
    }

    const api = {
        getDashboardSummary: () => request('/financial/dashboard/summary'),
        getFollowupContactable: (params = {}) => {
            const q = new URLSearchParams();
            if (params.limit) q.set('limit', params.limit);
            if (params.offset) q.set('offset', params.offset);
            if (params.search) q.set('search', params.search);
            return request('/financial/followup/contactable?' + q);
        },
        getFollowupDaily: (params = {}) => {
            const q = new URLSearchParams();
            if (params.limit) q.set('limit', params.limit);
            if (params.offset) q.set('offset', params.offset);
            if (params.search) q.set('search', params.search);
            return request('/financial/followup/daily?' + q);
        },
        getSchedulingTop300: (params = {}) => {
            const q = new URLSearchParams();
            if (params.limit) q.set('limit', params.limit || 300);
            if (params.offset) q.set('offset', params.offset);
            if (params.search) q.set('search', params.search);
            return request('/financial/scheduling/top300?' + q);
        },
        getSchedulingPriority: (params = {}) => {
            const q = new URLSearchParams();
            if (params.limit) q.set('limit', params.limit || 500);
            if (params.offset) q.set('offset', params.offset);
            if (params.scheduling_band) q.set('scheduling_band', params.scheduling_band);
            if (params.action_type) q.set('action_type', params.action_type);
            if (params.financial_tier) q.set('financial_tier', params.financial_tier);
            return request('/financial/scheduling/priority?' + q);
        },
        getPatientLookup: (mobile) => request('/financial/patient-lookup?mobile=' + encodeURIComponent(mobile || '')),
        getPatients: (params = {}) => {
            const q = new URLSearchParams();
            if (params.search) q.set('search', params.search);
            if (params.limit) q.set('limit', params.limit || 50);
            return request('/patients?' + q);
        },
        getTreatmentTypes: () => request('/treatment-types'),
        getPaymentTypes: () => request('/payment-types?mode=insurers'),
        predictAppointment: (body) => request('/ai/predict-appointment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }),
        patientHistoryScore: (id) => request('/ai/patient-history-score/' + id),
        suggestSlots: (params) => {
            const q = new URLSearchParams(params);
            return request('/appointments/suggest-time?' + q);
        },
        createAppointment: (body) => request('/appointments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
    };

    global.AtiehAPI = api;
})(window);
