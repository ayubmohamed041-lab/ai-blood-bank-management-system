/**
 * AI Blood Bank Management System - Frontend Controller
 * Integrates Biometric Scanning, XGBoost Predictions, Donor Management & Inventory
 */

// Global State
let currentLanguage = 'so'; // 'so' or 'en'
let probabilitiesChartInstance = null;
let featureImportanceChartInstance = null;
let lastExtractedFeatures = null;
let lastPredictedBloodGroup = null;

// Initialize Lucide icons and page on load
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initCharts();
    loadDashboardStats();
    loadInventory();
    loadDonors();
    loadRequests();
    loadAIMetrics();
    setupEventListeners();

    // Default scan initial sample (O+)
    setTimeout(() => {
        triggerFingerprintScan('O+');
    }, 400);
});

// Setup DOM Event Listeners
function setupEventListeners() {
    // 1. Language Toggle
    const langBtn = document.getElementById('lang-toggle-btn');
    if (langBtn) {
        langBtn.addEventListener('click', toggleLanguage);
    }

    // 2. Scanner Pad click
    const scannerPad = document.getElementById('scanner-pad');
    if (scannerPad) {
        scannerPad.addEventListener('click', () => {
            const selectedPreset = document.getElementById('preset-selector').value || 'O+';
            triggerFingerprintScan(selectedPreset);
        });
    }

    // 3. Scan Button
    const btnScanLive = document.getElementById('btn-scan-live');
    if (btnScanLive) {
        btnScanLive.addEventListener('click', () => {
            const selectedPreset = document.getElementById('preset-selector').value || 'O+';
            triggerFingerprintScan(selectedPreset);
        });
    }

    // 4. Preset Selector change
    const presetSelector = document.getElementById('preset-selector');
    if (presetSelector) {
        presetSelector.addEventListener('change', (e) => {
            triggerFingerprintScan(e.target.value);
        });
    }

    // 5. File Upload for Fingerprint
    const fileInput = document.getElementById('fingerprint-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFingerprintUpload);
    }

    // 6. Auto-fill Registration Form button
    const btnAutofill = document.getElementById('btn-autofill-form');
    if (btnAutofill) {
        btnAutofill.addEventListener('click', autofillFormFromScan);
    }

    // 7. Check Eligibility button in Form
    const btnCheckElig = document.getElementById('btn-check-eligibility');
    if (btnCheckElig) {
        btnCheckElig.addEventListener('click', checkFormEligibility);
    }

    // 8. Form input live updates for Donor Card
    ['form-name', 'form-country', 'form-phone', 'form-blood-group', 'form-hemoglobin', 'form-weight'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateDonorCardPreview);
        }
    });

    // 9. Donor Registration Form Submit
    const regForm = document.getElementById('donor-registration-form');
    if (regForm) {
        regForm.addEventListener('submit', handleDonorRegistration);
    }

    // 10. Donor Search Input
    const searchInput = document.getElementById('donor-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            loadDonors(e.target.value);
        }, 300));
    }

    // 11. Emergency Request Form Submit
    const reqForm = document.getElementById('emergency-request-form');
    if (reqForm) {
        reqForm.addEventListener('submit', handleEmergencyRequest);
    }
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `tab-${tabId}`) {
            content.classList.remove('hidden');
            content.classList.add('block');
        } else {
            content.classList.add('hidden');
            content.classList.remove('block');
        }
    });

    lucide.createIcons();
}

// Biometric Fingerprint Scanning Execution
async function triggerFingerprintScan(bloodGroupKey = 'O+') {
    const pad = document.getElementById('scanner-pad');
    const laser = document.getElementById('laser-line');
    const statusText = document.getElementById('scanner-status');
    const sound = document.getElementById('scan-beep');

    // UI Scanning state
    pad.classList.add('scanning');
    laser.classList.remove('hidden');
    statusText.innerHTML = `
        <span class="text-xs font-semibold text-rose-400 flex items-center justify-center gap-1.5 animate-pulse">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            Faraha waa la baarayaa... (Extracting Minutiae & Ridge Patterns...)
        </span>
    `;

    try {
        if (sound) {
            sound.currentTime = 0;
            sound.play().catch(() => {});
        }
    } catch(e) {}

    try {
        const response = await fetch('/api/scan_fingerprint', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ blood_group: bloodGroupKey })
        });
        const data = await response.json();

        // Allow scanline animation for 800ms
        setTimeout(() => {
            pad.classList.remove('scanning');
            laser.classList.add('hidden');
            statusText.innerHTML = `
                <span class="text-xs font-medium text-emerald-400 flex items-center justify-center gap-1.5">
                    <i data-lucide="check-circle" class="w-4 h-4 text-emerald-400"></i>
                    Baaritaanku waa guuleystay! (Scan Completed)
                </span>
            `;
            lucide.createIcons();

            // Update Fingerprint Image Preview
            if (data.image_url) {
                document.getElementById('fingerprint-img').src = data.image_url + '?t=' + Date.now();
            }

            renderScanResults(data);
        }, 850);

    } catch (err) {
        console.error('Scan error:', err);
        pad.classList.remove('scanning');
        laser.classList.add('hidden');
        statusText.innerHTML = `<span class="text-xs text-rose-400">Khalad ayaa dhacay intii lagu jiray baaritaanka.</span>`;
    }
}

// Upload Custom Fingerprint Image
async function handleFingerprintUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const pad = document.getElementById('scanner-pad');
    const laser = document.getElementById('laser-line');
    const statusText = document.getElementById('scanner-status');

    pad.classList.add('scanning');
    laser.classList.remove('hidden');
    statusText.innerHTML = `<span class="text-xs text-rose-400 animate-pulse">Sawirka faraha waa la falanqaynayaa...</span>`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload_fingerprint', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        setTimeout(() => {
            pad.classList.remove('scanning');
            laser.classList.add('hidden');
            statusText.innerHTML = `<span class="text-xs text-emerald-400">Sawirka faraha si guul leh ayaa loo falanqeeyay!</span>`;
            
            if (data.image_url) {
                document.getElementById('fingerprint-img').src = data.image_url + '?t=' + Date.now();
            }

            renderScanResults(data);
        }, 900);
    } catch (err) {
        console.error('Upload error:', err);
        pad.classList.remove('scanning');
        laser.classList.add('hidden');
        statusText.innerHTML = `<span class="text-xs text-rose-400">Khalad baa dhacay marka sawirka la falanqaynayay.</span>`;
    }
}

// Render Results of Fingerprint Scan
function renderScanResults(data) {
    const pred = data.prediction;
    const feat = data.features;

    lastExtractedFeatures = feat;
    lastPredictedBloodGroup = pred.predicted_blood_group;

    // Blood Group and Confidence
    document.getElementById('predicted-blood-group').innerText = pred.predicted_blood_group;
    document.getElementById('confidence-score').innerText = `${pred.confidence_percent}%`;

    const predBadge = document.getElementById('pred-badge');
    predBadge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    predBadge.innerText = 'XGBoost Confirmed';

    // Extracted Features
    document.getElementById('feat-pattern').innerText = `${feat.pattern_name} (Code ${feat.pattern_code})`;
    document.getElementById('feat-trc').innerText = `${feat.total_ridge_count} Ridges`;
    document.getElementById('feat-minutiae').innerText = `${feat.total_minutiae} (E: ${feat.minutiae_endings}, B: ${feat.minutiae_bifurcations})`;
    document.getElementById('feat-density').innerText = `${feat.ridge_density} /25mm²`;

    // Update Probabilities Bar Chart
    updateProbabilitiesChart(pred.class_probabilities, pred.predicted_blood_group);

    // Update Card Preview
    document.getElementById('card-blood-group').innerText = pred.predicted_blood_group;
}

// Initialize Charts
function initCharts() {
    // 1. Probabilities Chart
    const ctx = document.getElementById('probabilitiesChart').getContext('2d');
    probabilitiesChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
            datasets: [{
                label: 'Suurtagalnimada (Probability)',
                data: [0.1, 0.05, 0.15, 0.05, 0.1, 0.05, 0.45, 0.05],
                backgroundColor: '#f43f5e',
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1.0,
                    grid: { color: '#1e293b' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#cbd5e1', font: { size: 11, weight: 'bold' } }
                }
            }
        }
    });

    // 2. Feature Importance Chart
    const featCtx = document.getElementById('featureImportanceChart').getContext('2d');
    featureImportanceChartInstance = new Chart(featCtx, {
        type: 'bar',
        data: {
            labels: ['Total Ridge Count', 'Ridge Density', 'Pattern Code', 'Minutiae Bifurcations', 'Orientation Entropy', 'Core Delta Distance', 'Minutiae Endings'],
            datasets: [{
                label: 'XGBoost Feature Importance (Gain)',
                data: [0.32, 0.24, 0.16, 0.11, 0.08, 0.05, 0.04],
                backgroundColor: '#be123c',
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: '#1e293b' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#e2e8f0', font: { size: 11 } }
                }
            }
        }
    });
}

// Update Probabilities Chart
function updateProbabilitiesChart(probMap, predictedClass) {
    if (!probabilitiesChartInstance) return;

    const labels = Object.keys(probMap);
    const data = Object.values(probMap);

    const bgColors = labels.map(l => l === predictedClass ? '#10b981' : '#f43f5e');

    probabilitiesChartInstance.data.labels = labels;
    probabilitiesChartInstance.data.datasets[0].data = data;
    probabilitiesChartInstance.data.datasets[0].backgroundColor = bgColors;
    probabilitiesChartInstance.update();
}

// Autofill Registration Form from Fingerprint Scan
function autofillFormFromScan() {
    if (!lastPredictedBloodGroup) {
        alert(currentLanguage === 'so' ? 'Fadlan marka hore baar suulka!' : 'Please scan a fingerprint first!');
        return;
    }

    const bgSelect = document.getElementById('form-blood-group');
    if (bgSelect) {
        bgSelect.value = lastPredictedBloodGroup;
    }

    switchTab('registration');
    updateDonorCardPreview();

    // Trigger eligibility evaluation
    checkFormEligibility();
}

// Check Eligibility for the Form values using XGBoost
async function checkFormEligibility() {
    const payload = getFormData();

    try {
        const response = await fetch('/api/check_eligibility', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        const badge = document.getElementById('eligibility-status-badge');
        const title = document.getElementById('eligibility-title');
        const scoreText = document.getElementById('eligibility-score-text');
        const reasonBox = document.getElementById('eligibility-reason-box');
        const iconContainer = document.getElementById('eligibility-icon-container');
        const cardStatus = document.getElementById('card-status');

        if (result.can_donate) {
            badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
            badge.innerText = 'Eligible (Wuu Shubi Karaa)';

            iconContainer.className = 'w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3 ring-4 ring-emerald-500/10';
            iconContainer.innerHTML = `<i data-lucide="check" class="w-8 h-8"></i>`;

            title.className = 'text-xl font-bold text-emerald-400 mb-1';
            title.innerText = 'HAA, Dhiig wuu shubi karaa!';

            scoreText.innerHTML = `XGBoost Safety Score: <strong class="text-emerald-400">${result.eligibility_percent}%</strong>`;
            reasonBox.className = 'p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-emerald-200 leading-relaxed';
            reasonBox.innerText = result.explanation;

            cardStatus.className = 'text-emerald-400 font-semibold';
            cardStatus.innerText = 'Eligible';
        } else {
            badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30';
            badge.innerText = 'Ineligible (Ma Shubi Karo)';

            iconContainer.className = 'w-16 h-16 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mb-3 ring-4 ring-rose-500/10';
            iconContainer.innerHTML = `<i data-lucide="x" class="w-8 h-8"></i>`;

            title.className = 'text-xl font-bold text-rose-400 mb-1';
            title.innerText = 'MAYA, Dhiig ma shubi karo!';

            scoreText.innerHTML = `XGBoost Safety Score: <strong class="text-rose-400">${result.eligibility_percent}%</strong>`;
            reasonBox.className = 'p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/40 text-rose-300 leading-relaxed';
            reasonBox.innerText = result.explanation;

            cardStatus.className = 'text-rose-400 font-semibold';
            cardStatus.innerText = 'Deferred';
        }

        lucide.createIcons();
    } catch (err) {
        console.error('Eligibility check error:', err);
    }
}

// Get form payload
function getFormData() {
    return {
        full_name: document.getElementById('form-name').value.trim(),
        country: document.getElementById('form-country').value,
        phone: document.getElementById('form-phone').value.trim(),
        email: document.getElementById('form-email').value.trim(),
        blood_group: document.getElementById('form-blood-group').value,
        gender: document.getElementById('form-gender').value,
        age: parseInt(document.getElementById('form-age').value) || 25,
        weight_kg: parseFloat(document.getElementById('form-weight').value) || 65.0,
        hemoglobin: parseFloat(document.getElementById('form-hemoglobin').value) || 14.0,
        systolic_bp: parseInt(document.getElementById('form-systolic').value) || 120,
        diastolic_bp: parseInt(document.getElementById('form-diastolic').value) || 80,
        recency_months: parseInt(document.getElementById('form-recency').value) || 6,
        total_donations: parseInt(document.getElementById('form-total-donations').value) || 0,
        medical_flag: parseInt(document.getElementById('form-medical-flag').value) || 0,
        record_donation_now: document.getElementById('form-donate-now').checked,
        fingerprint_pattern: lastExtractedFeatures ? lastExtractedFeatures.pattern_name : 'Loop',
        fingerprint_ridge_count: lastExtractedFeatures ? lastExtractedFeatures.total_ridge_count : 140
    };
}

// Handle Donor Registration
async function handleDonorRegistration(e) {
    e.preventDefault();
    const payload = getFormData();

    if (!payload.full_name || !payload.phone) {
        alert(currentLanguage === 'so' ? 'Fadlan buuxi magaca iyo telefoonka qofka!' : 'Please enter full name and phone!');
        return;
    }

    try {
        const response = await fetch('/api/register_donor', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (result.success) {
            alert(currentLanguage === 'so' 
                ? `Ku-deeqaha ${payload.full_name} si guul leh ayaa loo diiwaangeliyay!` 
                : `Donor ${payload.full_name} registered successfully!`);
            
            // Refresh
            loadDashboardStats();
            loadInventory();
            loadDonors();
            switchTab('donors');
        } else {
            alert('Error: ' + result.message);
        }
    } catch (err) {
        console.error('Registration error:', err);
    }
}

// Live update ID Card Preview
function updateDonorCardPreview() {
    const name = document.getElementById('form-name').value.trim() || 'Axmed Cali Faarax';
    const country = document.getElementById('form-country').value || 'Somalia';
    const phone = document.getElementById('form-phone').value.trim() || '+252 61 555 1234';
    const bg = document.getElementById('form-blood-group').value || 'O+';
    const hb = document.getElementById('form-hemoglobin').value || '14.0';

    document.getElementById('card-name').innerText = name;
    document.getElementById('card-country').innerText = `${country} (${phone})`;
    document.getElementById('card-blood-group').innerText = bg;
    document.getElementById('card-hb').innerText = `${hb} g/dL`;
}

// Load Blood Inventory
async function loadInventory() {
    try {
        const res = await fetch('/api/inventory');
        const items = await res.json();

        const grid = document.getElementById('inventory-grid');
        grid.innerHTML = '';

        items.forEach(item => {
            const isLow = item.units_available < item.minimum_threshold;
            const bgBadgeClass = isLow ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
            const statusLabel = isLow ? 'Critical Low' : 'Adequate';

            const card = document.createElement('div');
            card.className = `p-5 rounded-3xl bg-slate-900/70 border ${isLow ? 'border-rose-600/60 shadow-rose-950/40' : 'border-slate-800'} shadow-xl flex flex-col justify-between transition hover:-translate-y-1`;
            card.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <span class="text-2xl font-black text-white">${item.blood_group}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-bold border ${bgBadgeClass}">${statusLabel}</span>
                </div>
                <div class="my-2">
                    <span class="text-4xl font-extrabold ${isLow ? 'text-rose-400' : 'text-slate-100'}">${item.units_available}</span>
                    <span class="text-xs text-slate-400 font-medium ml-1">Cutub (Units)</span>
                </div>
                <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <span>Heerka yar: ${item.minimum_threshold}</span>
                    <span class="text-rose-400 font-semibold cursor-pointer hover:underline" onclick="quickRequest('${item.blood_group}')">+ Codso</span>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (err) {
        console.error('Inventory error:', err);
    }
}

// Quick Request helper
function quickRequest(bloodGroup) {
    const sel = document.getElementById('req-blood-group');
    if (sel) sel.value = bloodGroup;
    switchTab('requests');
}

// Load Registered Donors
async function loadDonors(search = '') {
    try {
        const url = search ? `/api/donors?search=${encodeURIComponent(search)}` : '/api/donors';
        const res = await fetch(url);
        const donors = await res.json();

        const tbody = document.getElementById('donors-table-body');
        tbody.innerHTML = '';

        if (donors.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400 text-xs">Wax ku-deeqayaal ah lagama helin xogta.</td></tr>`;
            return;
        }

        donors.forEach(d => {
            const isEligible = d.eligibility_status === 'Eligible';
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-800/40 transition';
            tr.innerHTML = `
                <td class="py-3 px-4 font-semibold text-white">${d.full_name}</td>
                <td class="py-3 px-4 text-slate-400">${d.country}</td>
                <td class="py-3 px-4 font-mono text-slate-300">${d.phone}</td>
                <td class="py-3 px-4"><span class="px-2 py-1 rounded-lg bg-rose-950/60 text-rose-300 font-bold border border-rose-900/50">${d.blood_group}</span></td>
                <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold ${isEligible ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}">
                        ${d.eligibility_status}
                    </span>
                </td>
                <td class="py-3 px-4 text-slate-400">${d.fingerprint_pattern || 'Loop'} (TRC: ${d.fingerprint_ridge_count || 140})</td>
                <td class="py-3 px-4 text-slate-400">${d.total_donations} jeer</td>
                <td class="py-3 px-4 text-right">
                    <button onclick="recordNewDonation(${d.id})" class="px-2.5 py-1 rounded-lg text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium transition active:scale-95">
                        + Shub Dhiig
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (err) {
        console.error('Donors error:', err);
    }
}

// Record New Donation for existing donor
async function recordNewDonation(donorId) {
    if (!confirm(currentLanguage === 'so' ? 'Ma xaqiijinaysaa inaad diiwaangeliso 1 cutub oo dhiig ah qofkan?' : 'Confirm recording 1 unit of blood donation?')) return;

    try {
        const res = await fetch('/api/record_donation', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ donor_id: donorId })
        });
        const data = await res.json();
        if (data.success) {
            alert(currentLanguage === 'so' ? 'Dhiig shubista si guul leh ayaa loo diiwaangeliyay, kaydkiina wuu kordhay!' : 'Donation recorded successfully!');
            loadDashboardStats();
            loadInventory();
            loadDonors();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (e) {
        console.error(e);
    }
}

// Emergency Blood Request Submit
async function handleEmergencyRequest(e) {
    e.preventDefault();
    const payload = {
        patient_name: document.getElementById('req-patient').value.trim(),
        hospital_name: document.getElementById('req-hospital').value.trim(),
        contact_phone: document.getElementById('req-phone').value.trim(),
        blood_group: document.getElementById('req-blood-group').value,
        units_requested: parseInt(document.getElementById('req-units').value) || 1,
        urgency: document.getElementById('req-urgency').value
    };

    try {
        const res = await fetch('/api/blood_requests', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            alert(currentLanguage === 'so' ? 'Codsiga degdegga ah si guul leh ayaa loo gudbiyay!' : 'Emergency blood request submitted!');
            e.target.reset();
            loadRequests();
            loadDashboardStats();
        }
    } catch (err) {
        console.error('Request error:', err);
    }
}

// Load Blood Requests
async function loadRequests() {
    try {
        const res = await fetch('/api/blood_requests');
        const requests = await res.json();

        const container = document.getElementById('requests-list-container');
        container.innerHTML = '';

        if (requests.length === 0) {
            container.innerHTML = `<div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-400">Ma jiraan codsiyo degdeg ah oo sugaya.</div>`;
            return;
        }

        requests.forEach(r => {
            const isPending = r.status === 'Pending';
            const urgencyColor = r.urgency === 'Critical' ? 'text-red-400 border-red-500/30 bg-red-950/40' : (r.urgency === 'Urgent' ? 'text-amber-400 border-amber-500/30 bg-amber-950/40' : 'text-slate-300 border-slate-700 bg-slate-800/40');

            const item = document.createElement('div');
            item.className = 'p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3';
            item.innerHTML = `
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-sm font-bold text-white">${r.patient_name}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-full font-bold border ${urgencyColor}">${r.urgency}</span>
                        <span class="px-2 py-0.5 rounded-lg bg-rose-950/60 text-rose-300 font-bold text-xs border border-rose-900/40">${r.blood_group} (${r.units_requested} Units)</span>
                    </div>
                    <p class="text-xs text-slate-400">${r.hospital_name} &bull; Tel: <span class="text-slate-300">${r.contact_phone}</span> &bull; Taariikh: ${r.request_date}</p>
                </div>
                <div>
                    ${isPending 
                        ? `<button onclick="fulfillRequest(${r.id})" class="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30 transition active:scale-95">Bixi Dhiigga (Fulfill)</button>`
                        : `<span class="text-xs font-semibold text-emerald-400 flex items-center gap-1"><i data-lucide="check-circle-2" class="w-4 h-4"></i> La bixiyay</span>`
                    }
                </div>
            `;
            container.appendChild(item);
        });

        lucide.createIcons();
    } catch (err) {
        console.error('Requests error:', err);
    }
}

// Fulfill Request
async function fulfillRequest(reqId) {
    if (!confirm(currentLanguage === 'so' ? 'Ma xaqiijinaysaa bixinta dhiiggan isbitaalka?' : 'Confirm blood dispatch to hospital?')) return;

    try {
        const res = await fetch(`/api/fulfill_request/${reqId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert(currentLanguage === 'so' ? 'Dhiiggii si guul leh ayaa loo siiyay isbitaalka, kaydkiina waa laga jaray!' : 'Blood dispatched and deducted from inventory!');
            loadRequests();
            loadInventory();
            loadDashboardStats();
        } else {
            alert('Warning: ' + data.message);
        }
    } catch (e) {
        console.error(e);
    }
}

// Load Dashboard KPIs
async function loadDashboardStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();

        document.getElementById('nav-total-units').innerText = `${stats.total_units} Cutub`;
        document.getElementById('nav-total-donors').innerText = `${stats.total_donors} Qof`;
    } catch (e) {
        console.error(e);
    }
}

// Load AI Metrics
async function loadAIMetrics() {
    try {
        const res = await fetch('/api/ai_metrics');
        const metrics = await res.json();

        if (metrics.eligibility_model) {
            document.getElementById('xgb-elig-acc').innerText = `${(metrics.eligibility_model.accuracy * 100).toFixed(1)}%`;
            document.getElementById('xgb-elig-auc').innerText = metrics.eligibility_model.roc_auc.toFixed(2);
        }

        if (metrics.blood_group_model && featureImportanceChartInstance) {
            const imp = metrics.blood_group_model.feature_importance;
            const labels = Object.keys(imp);
            const vals = Object.values(imp);

            featureImportanceChartInstance.data.labels = labels;
            featureImportanceChartInstance.data.datasets[0].data = vals;
            featureImportanceChartInstance.update();
        }
    } catch (e) {
        console.error(e);
    }
}

// Language Toggle (Somali / English)
function toggleLanguage() {
    currentLanguage = currentLanguage === 'so' ? 'en' : 'so';
    document.getElementById('lang-label').innerText = currentLanguage === 'so' ? 'Somali / EN' : 'English / SO';

    document.querySelectorAll('.lang-text').forEach(el => {
        const text = el.getAttribute(`data-${currentLanguage}`);
        if (text) {
            el.innerText = text;
        }
    });
}

// Debounce Utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
