// ===== টেলিগ্রাম মিনি অ্যাপ চালু করা =====
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand(); // অ্যাপটিকে পুরো স্ক্রিনে বড় করা
tg.BackButton.hide(); // ডিফল্ট 'Back' বাটন হাইড করা

// ===== কনফিগারেশন =====
// এই লিঙ্কটি Render.com থেকে স্বয়ংক্রিয়ভাবে আসা উচিত
// (এটি আপনার script.js-এ আগে সেট করা আছে)
const API_BASE_URL = "https://my-service-app-r98m.onrender.com"; 

let products = {}; // বট থেকে লোড হবে
let userBalance = 0; // বট থেকে লোড হবে

// ===== Helper Functions =====
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(`page-${pageId}`).classList.add('active');
    const navBtn = document.querySelector(`.nav-button[data-page="${pageId}"]`);
    if (navBtn) navBtn.classList.add('active');
}

function showLoader(message) {
    const loader = document.createElement('div');
    loader.id = 'loader-overlay';
    loader.innerHTML = `<div class="loader-content"><div class="spinner"></div><p>${message}</p></div>`;
    document.body.appendChild(loader);
}

function hideLoader() {
    const loader = document.getElementById('loader-overlay');
    if (loader) {
        loader.remove();
    }
}

function showAlert(message, isError = false) {
    const alertBox = document.createElement('div');
    alertBox.className = `alert-box ${isError ? 'error' : 'success'}`;
    alertBox.innerText = message;
    document.body.appendChild(alertBox);
    setTimeout(() => {
        alertBox.classList.add('show');
    }, 10);
    setTimeout(() => {
        alertBox.classList.remove('show');
        setTimeout(() => alertBox.remove(), 500);
    }, 3000);
}

// ===== ১. 초기 데이터 로드 (Render.com থেকে) =====
async function loadInitialData() {
    if (!tg.initDataUnsafe || !tg.initDataUnsafe.user) {
        showAlert("টেলিগ্রাম ইউজার ডেটা পাওয়া যায়নি।", true);
        return;
    }
    
    showLoader("তথ্য লোড হচ্ছে...");
    try {
        const response = await fetch(`${API_BASE_URL}/get_init_data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: tg.initDataUnsafe.user })
        });

        if (!response.ok) {
            throw new Error(`সার্ভার এরর: ${response.statusText}`);
        }

        const data = await response.json();

        // ক. ব্যালেন্স আপডেট
        userBalance = parseFloat(data.balance.replace('৳ ', '')) || 0;
        document.getElementById('balance-display').innerText = data.balance;

        // খ. প্রোডাক্ট লিস্ট লোড
        products = data.products;
        loadServiceList(products);

        // গ. অর্ডার হিস্টরি লোড
        loadOrderHistory(data.orders);
        
        // ঘ. নোটিফিকেশন লোড
        loadNotifications(data.notifications);

    } catch (error) {
        logger.error("ডেটা লোড করতে ব্যর্থ:", error);
        showAlert(`ডেটা লোড করতে ব্যর্থ: ${error.message}`, true);
    } finally {
        hideLoader();
    }
}

// ===== ২. সার্ভিস লিস্ট দেখানো =====
function loadServiceList(products) {
    const container = document.getElementById('service-list-container');
    container.innerHTML = ''; // পুরানো লিস্ট পরিষ্কার করা
    
    for (const key in products) {
        const service = products[key];
        if (!service.enabled) continue; // বন্ধ সার্ভিস বাদ দেওয়া

        const serviceHtml = `
            <div class="service-item" data-service="${key}">
                <img src="logo_placeholder.png" alt="logo" class="service-logo"> <div class="service-info">
                    <strong>${service.name}</strong>
                    <span>ডেলিভারি: ${service.delivery}</span>
                </div>
                <strong class="service-price">💰 ${service.price} টাকা</strong>
            </div>
        `;
        container.innerHTML += serviceHtml;
    }

    // নতুন করে ইভেন্ট লিসেনার যোগ করা
    document.querySelectorAll('.service-item').forEach(item => {
        item.addEventListener('click', () => {
            const serviceKey = item.getAttribute('data-service');
            loadOrderForm(serviceKey);
            showPage('order-form');
        });
    });
}

// ===== ৩. অর্ডার ফর্ম তৈরি করা (আপনার চাহিদা অনুযায়ী) =====
function loadOrderForm(serviceKey) {
    const service = products[serviceKey];
    const container = document.getElementById('order-form-container');
    container.innerHTML = ''; // পুরানো ফর্ম পরিষ্কার করা

    let formHtml = `<div class="form-card"><h3>${service.name}</h3>`;
    let subOptionKey = null;

    // ক. সাব-অপশন (যেমন: NID vs Voter Slip)
    if (service.sub_options) {
        formHtml += `
            <div class="form-group">
                <label for="sub-option-select">সার্ভিসের ধরন সিলেক্ট করুন:</label>
                <select id="sub-option-select">
                    <option value="">-- সিলেক্ট করুন --</option>
                    ${Object.keys(service.sub_options).map(key => 
                        `<option value="${key}">${service.sub_options[key].name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="price-display">
                <strong>মূল্য: <span id="dynamic-price">৳ ${service.price}</span></strong>
            </div>
            <hr>
            <div id="sub-option-fields"></div>
        `;
    } 
    // খ. সাধারণ সার্ভিস (যেখানে সাব-অপশন নেই)
    else {
        formHtml += `
            <div class="price-display">
                <strong>মূল্য: ৳ ${service.price}</strong>
            </div>
            <hr>
            ${generateFormFields(service.fields)}
            <button class="btn btn-primary btn-full" id="submit-order-btn">✅ অর্ডার করুন</button>
        `;
    }

    formHtml += `</div>`;
    container.innerHTML = formHtml;

    // গ. ইভেন্ট লিসেনার যোগ করা
    if (service.sub_options) {
        document.getElementById('sub-option-select').addEventListener('change', (e) => {
            subOptionKey = e.target.value;
            const fieldsContainer = document.getElementById('sub-option-fields');
            if (subOptionKey) {
                const subService = service.sub_options[subOptionKey];
                // (ভবিষ্যতে সাব-অপশনের আলাদা দাম এখানে সেট করা যাবে)
                // document.getElementById('dynamic-price').innerText = `৳ ${subService.price || service.price}`;
                
                fieldsContainer.innerHTML = generateFormFields(subService.fields);
                fieldsContainer.innerHTML += `<button class="btn btn-primary btn-full" id="submit-order-btn">✅ অর্ডার করুন</button>`;
                addSubmitListener(serviceKey, subOptionKey); // সাবমিট বাটন যোগ
            } else {
                fieldsContainer.innerHTML = '';
            }
        });
    } else {
        addSubmitListener(serviceKey, null); // সাবমিট বাটন যোগ
    }

    // "ফিরে যান" বাটনে ক্লিক
    document.getElementById('back-to-services').addEventListener('click', () => {
        showPage('services');
    });
}

// ফর্মের ইনপুট ঘর তৈরি করার হেল্পার
function generateFormFields(fields) {
    if (!fields) return '';
    return fields.map(field => `
        <div class="form-group">
            <label for="field-${field.label}">${field.label}</label>
            ${field.type === 'photo' ? 
            `<input type="text" id="field-${field.label}" placeholder="টেলিগ্রাম চ্যাটে ছবি আপলোড করুন (API পরে যোগ হবে)">` :
            `<input type="text" id="field-${field.label}" placeholder="${field.example || ''}">`
            }
        </div>
    `).join('');
}

// ===== ৪. অর্ডার সাবমিট করা =====
function addSubmitListener(serviceKey, subOptionKey) {
    document.getElementById('submit-order-btn').addEventListener('click', async () => {
        const service = products[serviceKey];
        const price = service.price; // (পরে সাব-অপশনের দাম যোগ হবে)

        // ব্যালেন্স চেক
        if (userBalance < price) {
            showAlert("দুঃখিত, আপনার পর্যাপ্ত ব্যালেন্স নেই।", true);
            return;
        }

        const fields = subOptionKey ? service.sub_options[subOptionKey].fields : service.fields;
        const formData = {};
        let allFieldsValid = true;

        fields.forEach(field => {
            const input = document.getElementById(`field-${field.label}`);
            if (!input.value) {
                allFieldsValid = false;
            }
            formData[field.label] = input.value;
        });

        if (!allFieldsValid) {
            showAlert("অনুগ্রহ করে সব তথ্য পূরণ করুন।", true);
            return;
        }
        
        showLoader("অর্ডার সাবমিট করা হচ্ছে...");

        try {
            const response = await fetch(`${API_BASE_URL}/submit_order`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    user: tg.initDataUnsafe.user,
                    service_key: serviceKey,
                    sub_option_key: subOptionKey,
                    form_data: formData
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || "সার্ভার এরর");
            }

            // সফল হলে
            showAlert(result.message || "অর্ডার সফল হয়েছে!", false);
            tg.close(); // অ্যাপ বন্ধ করে দেওয়া

        } catch (error) {
            logger.error("অর্ডার সাবমিট করতে ব্যর্থ:", error);
            showAlert(`অর্ডার সাবমিট করতে ব্যর্থ: ${error.message}`, true);
        } finally {
            hideLoader();
        }
    });
}

// ===== ৫. অর্ডার হিস্টরি দেখানো (আপনার টেবিল ডিজাইন) =====
function loadOrderHistory(orders) {
    const container = document.getElementById('history-list-container');
    container.innerHTML = ''; // পুরানো লিস্ট পরিষ্কার করা

    if (orders.length === 0) {
        container.innerHTML = "<p style='padding: 15px; text-align: center;'>আপনি এখনও কোনো অর্ডার করেননি।</p>";
        return;
    }

    orders.forEach((order, index) => {
        let statusHtml = '';
        if (order.status === 'Success' || order.status === 'Completed') {
            statusHtml = `<button class="status-btn success" data-order-id="${order.id}" data-delivery-type="${order.delivery_type}">🟢 Success</button>`;
        } else if (order.status === 'Pending') {
            statusHtml = `<span class="status-pending">(🟡 Pending...)</span>`;
        } else if (order.status === 'Cancelled' || order.status === 'Not Found') {
            statusHtml = `<span class="status-cancelled">(🚫 ${order.status})</span>`;
        } else {
            statusHtml = `<span>(${order.status})</span>`;
        }

        const rowHtml = `
            <div class="history-row">
                <div>${index + 1}</div>
                <div><strong>${order.type}</strong></div>
                <div><button class="btn btn-secondary info-btn" data-order-info='${JSON.stringify(order.info_data)}'>তথ্য দেখুন</button></div>
                <div>${statusHtml}</div>
                <div>${order.rate}</div>
                <div>${order.time}</div>
            </div>
        `;
        container.innerHTML += rowHtml;
    });

    // "তথ্য দেখুন" বাটন
    document.querySelectorAll('.info-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const infoData = JSON.parse(e.target.getAttribute('data-order-info'));
            let infoText = "আপনি এই তথ্যগুলো জমা দিয়েছিলেন:\n\n";
            for (const label in infoData) {
                infoText += `${label}: ${infoData[label]}\n`;
            }
            alert(infoText); // সহজ পপ-আপ
        });
    });

    // "Success" বাটন (ডেলিভারি)
    document.querySelectorAll('.status-btn.success').forEach(button => {
        button.addEventListener('click', (e) => {
            const orderId = e.target.getAttribute('data-order-id');
            const deliveryType = e.target.getAttribute('data-delivery-type');
            
            if (deliveryType === 'pdf') {
                alert(`অর্ডার #${orderId} এর PDF ডাউনলোড করা হচ্ছে... (API পরে যোগ হবে)`);
                // window.open(`${API_BASE_URL}/download_pdf?order_id=${orderId}`);
            } else {
                alert(`অর্ডার #${orderId} এর টেক্সট তথ্য দেখুন... (API পরে যোগ হবে)`);
                // (এখানে টেক্সট দেখানোর পপ-আপ কোড থাকবে)
            }
        });
    });
}

// ===== ৬. নোটিফিকেশন দেখানো =====
function loadNotifications(notifications) {
    const container = document.getElementById('notification-list');
    container.innerHTML = '';
    
    if (notifications.length === 0) {
        container.innerHTML = "<p style='padding: 15px; text-align: center;'>কোনো নতুন নোটিফিকেশন নেই।</p>";
        return;
    }

    notifications.forEach(notif => {
        container.innerHTML += `
            <div class="notification-item">
                <strong>${notif.text}</strong>
                <small>${notif.time}</small>
            </div>
        `;
    });
}

// ===== ৭. নেভিগেশন চালু করা =====
navButtons.forEach(button => {
    button.addEventListener('click', () => {
        const pageId = button.getAttribute('data-page');
        showPage(pageId);
    });
});

// ===== ৮. CSS স্টাইল যোগ করা (CSS ফাইলে না থাকলে) =====
const styleOverrides = `
#loader-overlay {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
    z-index: 9999; color: white; flex-direction: column;
}
.loader-content {
    background: rgba(0,0,0,0.8); padding: 20px; border-radius: 10px;
}
.spinner {
    width: 40px; height: 40px; border: 4px solid #f3f3f3;
    border-top: 4px solid var(--tg-theme-button-color);
    border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px auto;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.alert-box {
    position: fixed; top: -100px; left: 50%; transform: translateX(-50%);
    background-color: var(--success-color); color: white; padding: 14px 20px;
    border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    font-weight: 600; z-index: 10000; transition: top 0.5s ease-in-out;
}
.alert-box.error { background-color: var(--danger-color); }
.alert-box.show { top: 20px; }

.form-card { background: var(--card-bg-color); padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.07); }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; font-weight: 600; margin-bottom: 5px; font-size: 0.9rem; }
.form-group input, .form-group select { width: 100%; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
.price-display { font-size: 1.1rem; margin: 10px 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 20px 0; }
.btn-full { width: 100%; padding: 14px; font-size: 1.1rem; margin-top: 10px; }
.btn-primary { background-color: var(--tg-theme-button-color); color: var(--tg-theme-button-text-color); }
.btn-secondary { background-color: #e5e5ea; color: #000; }
.notification-item { padding: 10px; background: var(--card-bg-color); border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; }
.notification-item small { color: var(--tg-theme-hint-color); font-size: 0.8rem; }
`;
document.head.insertAdjacentHTML('beforeend', `<style>${styleOverrides}</style>`);


// ===== ৯. অ্যাপ চালু করা =====
// অ্যাপ লোড হলে Render.com থেকে আসল ডেটা লোড করা
document.addEventListener('DOMContentLoaded', loadInitialData);
