// টেলিগ্রাম মিনি অ্যাপ চালু করা
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand(); // অ্যাপটিকে পুরো স্ক্রিনে বড় করা

// এই লিঙ্কটি আমরা পরে Render.com-এর লিঙ্ক দিয়ে পরিবর্তন করবো
const API_BASE_URL = "https://my-service-app-r98m.onrender.com"; 

// --- নেভিগেশন সিস্টেম ---
const allPages = document.querySelectorAll('.page');
const navButtons = document.querySelectorAll('.nav-button');

function showPage(pageId) {
    allPages.forEach(page => {
        page.classList.remove('active');
    });
    navButtons.forEach(button => {
        button.classList.remove('active');
    });

    const pageElement = document.getElementById(`page-${pageId}`);
    const buttonElement = document.querySelector(`.nav-button[data-page="${pageId}"]`);
    
    if (pageElement) pageElement.classList.add('active');
    if (buttonElement) buttonElement.classList.add('active');
}

navButtons.forEach(button => {
    button.addEventListener('click', () => {
        const pageId = button.getAttribute('data-page');
        showPage(pageId);
    });
});

// ডিফল্টভাবে সার্ভিস পেজ দেখানো
showPage('services');

// --- সার্ভিস লিস্টে ক্লিক করা ---
document.querySelectorAll('.service-item').forEach(item => {
    item.addEventListener('click', () => {
        const serviceKey = item.getAttribute('data-service');
        // (এখানে আমরা পরে প্রতিটি সার্ভিসের জন্য আলাদা ফর্ম লোড করার কোড লিখবো)
        alert(`আপনি "${serviceKey}" সার্ভিসটি সিলেক্ট করেছেন। ফর্মটি লোড হচ্ছে... (ডেমো)`);
        // showPage('order-form'); // ফর্ম পেজটি পরে চালু করা হবে
    });
});

// "ফিরে যান" বাটনে ক্লিক (যদি থাকে)
const backButton = document.getElementById('back-to-services');
if (backButton) {
    backButton.addEventListener('click', () => {
        showPage('services');
    });
}

// --- CSS-এর জন্য কিছু ইনপুট/বাটন স্টাইল (style.css এ যোগ করা ভালো) ---
// (এই কোডটি আপনার style.css ফাইলে যোগ করে দিলে ভালো হয়)
const styleOverrides = `
.form-card {
    background: var(--card-bg-color);
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.07);
}
.form-group {
    margin-bottom: 15px;
}
.form-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 5px;
    font-size: 0.9rem;
}
.form-group input, .form-group select {
    width: 100%;
    padding: 12px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    font-size: 1rem;
    box-sizing: border-box; /* এটি গুরুত্বপূর্ণ */
}
.btn-full {
    width: 100%;
    padding: 14px;
    font-size: 1.1rem;
    margin-top: 10px;
}
.btn-primary {
    background-color: var(--tg-theme-button-color);
    color: var(--tg-theme-button-text-color);
}
.btn-secondary {
    background-color: #e5e5ea;
    color: #000;
    margin-top: 15px;
}
`;
// স্টাইলগুলো হেডে যোগ করা
document.head.insertAdjacentHTML('beforeend', `<style>${styleOverrides}</style>`);

// --- ডেমো ডেটা লোড করা (পরে Render.com থেকে আসবে) ---
function loadInitialData() {
    // ডেমো ব্যালেন্স দেখানো
    document.getElementById('balance-display').innerText = '৳ ৫০০.০০ (ডেমো)';
    
    // ডেমো অর্ডার হিস্টরি দেখানো
    const historyContainer = document.getElementById('history-list-container');
    historyContainer.innerHTML = `
        <div class="history-row">
            <div>1</div>
            <div>🟧 আইডি কার্ড</div>
            <div><button class="btn btn-secondary" style="padding: 5px 8px; font-size: 0.75rem;">তথ্য দেখুন</button></div>
            <div><button class="status-btn success">🟢 Success</button></div>
            <div>160tk</div>
            <div>20 min</div>
        </div>
        <div class="history-row">
            <div>2</div>
            <div>🟥 সার্ভার কপি</div>
            <div><button class="btn btn-secondary" style="padding: 5px 8px; font-size: 0.75rem;">তথ্য দেখুন</button></div>
            <div><span class="status-pending">(🟡 Pending...)</span></div>
            <div>80tk</div>
            <div>10 min</div>
        </div>
    `;
    
    // ডেমো নোটিফিকেশন
    document.getElementById('notification-list').innerHTML = `
        <div style="padding: 10px; background: #fff; border-radius: 8px;">
            <strong>আপনার আইডি কার্ড অর্ডার (#1) সফল হয়েছে!</strong>
            <br><small style="color: #888;">২ মিনিট আগে</small>
        </div>
    `;
}

// অ্যাপ লোড হলে ডেমো ডেটা দেখানো
loadInitialData();

