const platformServices = {
  tiktok: { title: "خدمات تيك توك", services: ["إعجابات تيك توك", "مشاهدات تيك توك", "متابعين تيك توك"] },
  instagram: { title: "خدمات إنستجرام", services: ["إعجابات إنستجرام", "مشاهدات إنستجرام", "متابعين إنستجرام"] },
  facebook: { title: "خدمات فيسبوك", services: ["إعجابات فيسبوك", "متابعين فيسبوك", "مشاهدات فيديوهات فيسبوك"] },
  youtube: { title: "خدمات يوتيوب", services: ["مشاهدات يوتيوب", "مشتركين يوتيوب", "إعجابات يوتيوب"] }
};

const platformIcons = ["♥", "◉", "♟"];
const platformDescriptions = ["خدمات إعجابات للمحتوى", "خدمات مشاهدات للفيديوهات", "خدمات متابعين للحسابات"];
const platformNames = { tiktok: "تيك توك", instagram: "إنستجرام", facebook: "فيسبوك", youtube: "يوتيوب" };

const serviceGrid = document.getElementById("serviceGrid");
const platformTitle = document.getElementById("selectedPlatformTitle");
const modal = document.getElementById("orderModal");
const serviceInput = document.getElementById("serviceName");
const feedback = document.getElementById("formFeedback");

function renderServices(platform) {
  const data = platformServices[platform];
  platformTitle.textContent = data.title;
  serviceGrid.innerHTML = data.services.map((service, index) => `
    <article class="service-card">
      <div class="service-icon">${platformIcons[index]}</div>
      <div><h4>${service.replace(platformNames[platform], "").trim()}</h4><p>${platformDescriptions[index]}</p></div>
      <button class="order-btn" data-service="${service}">اطلب الخدمة <span>←</span></button>
    </article>`).join("");
}

document.querySelectorAll(".platform-card").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".platform-card").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderServices(button.dataset.platform);
  });
});

function openOrder(service) {
  serviceInput.value = service;
  feedback.textContent = "";
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  document.getElementById("accountLink").focus();
}

function closeOrder() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

serviceGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-service]");
  if (button) openOrder(button.dataset.service);
});

document.getElementById("modalClose").addEventListener("click", closeOrder);
modal.addEventListener("click", (event) => { if (event.target === modal) closeOrder(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeOrder(); });

document.getElementById("orderForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const link = document.getElementById("accountLink").value.trim();
  const quantity = Number(document.getElementById("quantity").value);
  const email = document.getElementById("customerEmail").value.trim();
  const password = document.getElementById("customerPassword").value;
  const name = document.getElementById("customerName").value.trim();
  const phone = document.getElementById("customerPhone").value.trim();
  const serviceId = Number(window.selectedServiceId || 0);
  if (!serviceId || !link || !Number.isInteger(quantity) || quantity < 1) { feedback.textContent = "اختار خدمة وراجع الرابط والكمية."; return; }
  feedback.textContent = "جاري إرسال الطلب...";
  try {
    const me = await fetch("/api/me", {credentials:"same-origin"});
    if (me.status === 401) {
      const reg = await fetch("/api/register", {method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,email,phone,password})});
      const regData = await reg.json(); if (!reg.ok) throw new Error(regData.detail || "تعذر إنشاء الحساب");
    } else if (!me.ok) { throw new Error("تعذر التحقق من الحساب"); }
    const res = await fetch("/api/orders", {method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({service_id:serviceId,target_link:link,quantity})});
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || "تعذر إرسال الطلب");
    feedback.textContent = "تم إنشاء طلبك رقم #" + data.order.id + ". احتفظ بالرقم لمتابعته.";
  } catch (err) { feedback.textContent = err.message; }
});
document.getElementById("menuToggle").addEventListener("click", () => {
  document.querySelector(".desktop-nav").classList.toggle("show");
});
document.querySelectorAll(".desktop-nav a").forEach((link) => {
  link.addEventListener("click", () => document.querySelector(".desktop-nav").classList.remove("show"));
});
document.getElementById("year").textContent = new Date().getFullYear();