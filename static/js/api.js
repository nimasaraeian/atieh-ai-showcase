const API = (() => {
    /**
     * Extract a readable error message from API error payload.
     * Handles: string detail, array of validation errors, nested objects.
     */
    function extractErrorMessage(payload) {
        if (!payload) return "خطای نامشخص";
        const d = payload.detail ?? payload.error ?? payload.message;
        if (typeof d === "string") return d;
        if (Array.isArray(d)) {
            const msgs = d.map((x) => (x && x.msg) || JSON.stringify(x)).filter(Boolean);
            return msgs.length ? msgs.join("; ") : "خطای اعتبارسنجی";
        }
        if (d && typeof d === "object") return (d.msg ?? d.message ?? JSON.stringify(d));
        return `Request failed: ${payload.status ?? "unknown"}`;
    }

    async function request(path, options = {}) {
        const response = await fetch(path, {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            ...options
        });

        let payload = null;
        const text = await response.text();

        try {
            payload = text ? JSON.parse(text) : null;
        } catch {
            payload = text;
        }

        if (!response.ok) {
            const message = extractErrorMessage(payload) || `Request failed: ${response.status}`;
            throw new Error(message);
        }

        return payload;
    }

    return {
        getDashboardSummary: () => request("/financial/dashboard/summary"),
        getDashboardInsights: () => request("/financial/dashboard/insights"),
        getDashboardKpis: () => request("/financial/dashboard/kpis"),
        getDashboardTrends: (limit = 12) => request(`/financial/dashboard/trends?limit=${limit}`),
        getTopVIPs: (limit = 10, offset = 0) => request(`/financial/top-vips?limit=${limit}&offset=${offset}`),
        getPatientDetail: (recordNo) => request(`/financial/patient/${recordNo}`),

        getFollowupQueue: (limit = 100, offset = 0) =>
            request(`/financial/followup/contactable?limit=${limit}&offset=${offset}`),

        getFollowupDaily: (limit = 100, offset = 0) =>
            request(`/financial/followup/daily?limit=${limit}&offset=${offset}`),

        getTop300: (limit = 100, offset = 0) =>
            request(`/financial/scheduling/top300?limit=${limit}&offset=${offset}`),

        getPriority: (limit = 100, offset = 0) =>
            request(`/financial/scheduling/priority?limit=${limit}&offset=${offset}`),

        patientLookup: (q = "", limit = 50, offset = 0) =>
            request(`/financial/patient-lookup?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`),

        getPatientsSearch: (q = "", limit = 50, offset = 0) =>
            request(`/api/staff/patients/search?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`),

        getServicesCatalog: () => request("/ai/engine/catalog/services"),
        getInsurancesCatalog: () => request("/ai/engine/catalog/insurances"),

        recommendSlot: (payload) =>
            request("/ai/engine/recommend-slot", {
                method: "POST",
                body: JSON.stringify(payload)
            }),

        getPatients: (search = "", limit = 20, offset = 0) =>
            request(`/patients?search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}`),

        resolveRecordNo: (recordNo) =>
            request(`/patients/by-record-no/${encodeURIComponent(String(recordNo || "").trim())}`),

        createAppointment: (payload) =>
            request("/appointments", {
                method: "POST",
                body: JSON.stringify(payload)
            }),

        getAppointmentSuggestions: () =>
            request("/financial/appointment-suggestions"),

        reviewAppointmentSuggestion: (id, payload) =>
            request(`/financial/appointment-suggestions/${id}/review`, {
                method: "POST",
                body: JSON.stringify(payload)
            })
    };
})();