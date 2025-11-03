// ===== টেলিগ্রাম মিনি অ্যাপ চালু করা =====
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.BackButton.onClick(showServiceListPage); // 'Back' বাটনে ক্লিক করলে সার্ভিস পেজে ফিরবে
tg.BackButton.hide(); // প্রথমে বাটনটি হাইড রাখা

// ===== আপনার bot.py থেকে প্রোডাক্ট লিস্ট (সঠিক করা) =====
// (Python-এর "True" কে JavaScript-এর "true" করা হয়েছে)
const products = {
    "SERVER_COPY": {
        "name": "সার্ভার কপি", "price": 80, "enabled": true, "delivery": "১০ মিনিট",
        "fields": [{"label": "NID নাম্বার", "type": "text", "example": "10/13/17 সংখ্যা"}, {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}]
    },
    "ID_CARD": {
        "name": "আইডি কার্ড", "price": 160, "enabled": true, "delivery": "২০ মিনিট",
        "sub_options": {
            "nid": {"name": "এনআইডি নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]},
            "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "ভোটার স্লিপ নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}
        }
    },
    "SMART_CARD": {
        "name": "স্মার্ট কার্ড", "price": 350, "enabled": true, "delivery": "২০ মিনিট",
        "sub_options": {
             "nid": {"name": "এনআইডি নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]},
            "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "ভোটার স্লিপ নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}
        }
    },
     "BIOMETRIC": {
        "name": "বায়োমেট্রিক", "price": 650, "enabled": true, "delivery": "৩০ মিনিট",
        "sub_options": {
            "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "LOCATION": {
        "name": "লোকেশ", "price": 850, "enabled": true, "delivery": "৩০ মিনিট",
        "sub_options": {
             "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "CALL_LIST": {
        "name": "কল লিস্ট", "price": 1900, "enabled": true, "delivery": "২৪/৪৮ ঘন্টা",
        "sub_options": {
             "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "ID_TO_NUMBER": {
        "name": "আইডি টু নাম্বার", "price": 900, "enabled": true, "delivery": "২০ মিনিট",
        "fields": [{"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম সাল", "type": "text", "example": "YYYY"}]
    },
    "TIN_CERTIFICATE": {
        "name": "টিন সার্টিফিকেট", "price": 200, "enabled": true, "delivery": "১০ মিনিট",
        "sub_options": {
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}]},
            "tin": {"name": "TIN NO", "fields": [{"label": "TIN NO", "type": "text"}]},
            "mobile": {"name": "MOBILE NO", "fields": [{"label": "MOBILE NO", "type": "text"}]},
            "old_tin": {"name": "OLD TIN NO", "fields": [{"label": "OLD TIN NO", "type": "text"}]},
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}]}
        }
    },
    "BKASH_INFO": { "name": "বিকাশ ইনফর্মেশন", "price": 2500, "enabled": true, "delivery": "অফিস টাইম", "fields": [{"label": "বিকাশ নাম্বার", "type": "text"}]},
    "NAGAD_INFO": { "name": "নগদ ইনফর্মেশন", "price": 1500, "enabled": true, "delivery": "অফিস টাইম", "fields": [{"label": "নগদ নাম্বার", "type": "text"}]},
    "LOST_ID_CARD": {
        "name": "হারানো আইডি কার্ড", "price": 1600, "enabled": true, "delivery": "অফিস টাইম", 
        "fields": [ 
            {"label": "নাম", "type": "text"}, {"label": "পিতার নাম", "type": "text"}, {"label": "মাতার নাম", "type": "text"}, 
            {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, 
            {"label": "ইউনিয়ন", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, {"label": "গ্রাম", "type": "text"}, 
            {"label": "জন্ম নিবন্ধন (যদি থাকে)", "type": "text"}, {"label": "ব্যক্তির ছবি", "type": "photo"} 
        ]
    },
    "NEW_BIRTH_CERTIFICATE": {
        "name": "নতুন জন্ম নিবন্ধন", "price": 2400, "enabled": true, "delivery": "৪৮ ঘন্টা", 
        "fields": [ 
            {"label": "নাম (বাংলায়)", "type": "text"}, {"label": "Name (ENGLISH)", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}, 
            {"label": "পিতার নাম (বাংলায়)", "type": "text"}, {"label": "Father's Name (ENGLISH)", "type": "text"}, {"label": "মাতার নাম (বাংলায়)", "type": "text"}, 
            {"label": "Mother's Name (ENGLISH)", "type": "text"}, {"label": "কততম সন্তান", "type": "text"}, {"label": "জন্মস্থান", "type": "text"}, 
            {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, 
            {"label": "ইউনিয়ন", "type": "text"}, {"label": "গ্রাম", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, 
            {"label": "পোস্ট অফিস", "type": "text"}, {"label": "পিতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "পিতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"}, 
            {"label": "মাতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "মাতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"} 
        ]
    },
     "MRP_PASSPORT": {
        "name": "MRP পাসপোর্ট SB", "price": 1400, "enabled": true, "delivery": "অফিস টাইম", 
        "sub_options": { 
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]} 
        }
    },
    "E_PASSPORT": {
        "name": "ই-পাসপোর্ট SB", "price": 1400, "enabled": true, "delivery": "অফিস টাইম", 
        "sub_options": { 
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]} 
        }
    }
};

// ===== Helper Functions =====
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById(`page-${pageId}`).classList.add('active');
    
    if (pageId === 'services') {
        tg.BackButton.hide();
        document.getElementById('header-description').innerText = "অনুগ্রহ করে একটি সার্ভিস সিলেক্ট করুন এবং তথ্য পূরণ করুন।";
    } else {
        tg.BackButton.show();
        document.getElementById('header-description').innerText = "অনুগ্রহ করে নিচের ফর্মটি পূরণ করুন।";
    }
}

function showLoader(show) {
    document.getElementById('loader-overlay').style.display = show ? 'flex' : 'none';
}

function showAlert(message) {
    alert(message);
}

// ===== ১. সার্ভিস লিস্ট দেখানো =====
function loadServiceList() {
    const container = document.getElementById('service-list-container');
    container.innerHTML = ''; 
    
    for (const key in products) {
        const service = products[key];
        // enabled: true (সঠিক JavaScript) চেক করা হচ্ছে
        if (!service.enabled) continue; 

        const serviceHtml = `
            <div class="service-item" data-service="${key}">
                <div class="service-info">
                    <strong>${service.name}</strong>
                    <span>ডেলিভারি: ${service.delivery}</span>
                </div>
                <strong class="service-price">💰 ${service.price} টাকা</strong>
            </div>
        `;
        container.innerHTML += serviceHtml;
    }

    // ইভেন্ট লিসেনার যোগ করা
    document.querySelectorAll('.service-item').forEach(item => {
        item.addEventListener('click', () => {
            const serviceKey = item.getAttribute('data-service');
            loadOrderForm(serviceKey);
            showPage('order-form');
        });
    });
}

// ===== ২. অর্ডার ফর্ম তৈরি করা =====
function loadOrderForm(serviceKey) {
    const service = products[serviceKey];
    const container = document.getElementById('order-form-container');
    container.innerHTML = '';

    let formHtml = `<div class="form-card"><h3>${service.name}</h3>`;
    let subOptionKey = null;

    if (service.sub_options) {
        formHtml += `
            <div class="form-group">
                <label for="sub-option-select">সার্ভিসের ধরন সিলেক্ট করুন:</label>
                <select id="sub-option-select" class="form-control">
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
    else {
        formHtml += `
            <div class="price-display">
                <strong>মূল্য: ৳ ${service.price}</strong>
            </div>
            <hr>
            ${generateFormFields(service.fields)}
            <button class="btn btn-primary" id="submit-order-btn">✅ অর্ডার সাবমিট করুন</button>
        `;
    }

    formHtml += `</div>`;
    container.innerHTML = formHtml;

    if (service.sub_options) {
        document.getElementById('sub-option-select').addEventListener('change', (e) => {
            subOptionKey = e.target.value;
            const fieldsContainer = document.getElementById('sub-option-fields');
            if (subOptionKey) {
                const subService = service.sub_options[subOptionKey];
                fieldsContainer.innerHTML = generateFormFields(subService.fields);
                fieldsContainer.innerHTML += `<button class="btn btn-primary" id="submit-order-btn">✅ অর্ডার সাবমিট করুন</button>`;
                addSubmitListener(serviceKey, subOptionKey); 
            } else {
                fieldsContainer.innerHTML = '';
            }
        });
    } else {
        addSubmitListener(serviceKey, null); 
    }

    // "ফিরে যান" বাটনে ক্লিক
    document.getElementById('back-to-services').addEventListener('click', () => {
        showPage('services');
    });
}

function generateFormFields(fields) {
    if (!fields) return '';
    return fields.map(field => `
        <div class="form-group">
            <label for="field-${field.label}">${field.label}</label>
            ${field.type === 'photo' ? 
            `<p class="photo-notice">ℹ️ ছবির জন্য, অনুগ্রহ করে অর্ডার সাবমিট করার পর বটকে সরাসরি ছবি পাঠান।</p>` :
            `<input type="text" class="form-control" id="field-${field.label}" placeholder="${field.example || ''}">`
            }
        </div>
    `).join('');
}

// ===== ৩. অর্ডার সাবমিট করা (tg.sendData ব্যবহার করে) =====
function addSubmitListener(serviceKey, subOptionKey) {
    document.getElementById('submit-order-btn').addEventListener('click', () => {
        
        showLoader(true); // লোডার দেখানো

        const service = products[serviceKey];
        const fields = subOptionKey ? service.sub_options[subOptionKey].fields : service.fields;
        const formData = {};
        let allFieldsValid = true;

        fields.forEach(field => {
            if (field.type !== 'photo') { // ছবি ছাড়া অন্য ইনপুটগুলো চেক
                const input = document.getElementById(`field-${field.label}`);
                if (!input || !input.value) { // ইনপুট ভ্যালু আছে কিনা চেক
                    allFieldsValid = false;
                }
                if(input) { // ইনপুট থাকলে তবেই ডেটা নেওয়া
                    formData[field.label] = input.value;
                }
            }
        });

        if (!allFieldsValid) {
            showAlert("অনুগ্রহ করে সব তথ্য পূরণ করুন।");
            showLoader(false); // লোডার হাইড
            return;
        }
        
        // বটকে পাঠানোর জন্য ডেটা প্রস্তুত করা
        const dataToSend = {
            service_key: serviceKey,
            sub_option_key: subOptionKey,
            form_data: formData
        };

        // টেলিগ্রাম বটকে ডেটা পাঠানো
        // tg.sendData() কল করার পর, বট উত্তর পাঠালে অ্যাপটি স্বয়ংক্রিয়ভাবে বন্ধ হয়ে যাবে
        tg.sendData(JSON.stringify(dataToSend));
        
        // tg.close(); // এটি আমরা বট থেকে কল করবো
    });
}

// ===== অ্যাপ চালু করা =====
document.addEventListener('DOMContentLoaded', () => {
    loadServiceList();
    showPage('services');
});
