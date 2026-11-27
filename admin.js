const $ = (id) => document.getElementById(id);
async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "حصل خطأ، حاول مرة تانية");
  return data;
}
function showMessage(id, text) { $(id).textContent = text; }
async function loadDashboard() {
  const summary = await api("/api/admin/summary");
  $("customersCount").textContent = summary.customers;
  $("ordersCount").textContent = summary.orders;
  $("pendingCount").textContent = summary.pending;
  $("revenueCount").textContent = summary.revenue.toLocaleString("ar-EG");
  const [orders, services] = await Promise.all([api("/api/admin/orders"), api("/api/admin/services")]);
  renderOrders(orders);
  renderServices(services);
}
function renderOrders(orders) {
  const labels = {pending_payment:"بانتظار الدفع",paid:"تم الدفع",processing:"قيد التنفيذ",completed:"مكتمل",rejected:"مرفوض",cancelled:"ملغي"};
  $("ordersList").innerHTML = orders.length ? orders.map(o => `<article class="order-row"><div class="order-top"><b>طلب #${o.id} · ${o.service_title}</b><span>${o.total_price} ج.م</span></div><p>العميل رقم ${o.customer_id} · الكمية: ${o.quantity}</p><p><a href="${escapeAttr(o.target_link)}" target="_blank" rel="noopener">فتح الرابط</a></p><p>الحالة: ${labels[o.status] || o.status}</p><div class="order-actions"><select id="status-${o.id}">${Object.entries(labels).map(([k,v])=>`<option value="${k}" ${o.status===k?"selected":""}>${v}</option>`).join("")}</select><button data-save-order="${o.id}">حفظ الحالة</button></div></article>`).join("") : '<p class="muted">لسه مفيش طلبات.</p>';
}
function renderServices(services) {
  const platforms = {tiktok:"TikTok",instagram:"Instagram",facebook:"Facebook",youtube:"YouTube",telegram:"Telegram"};
  $("serviceList").innerHTML = services.length ? services.map(s => `<div class="service-row"><span><b>${escapeHtml(s.title)}</b><br><small>${platforms[s.platform] || escapeHtml(s.platform)} · ${s.price} جنيه / 1000 · ${s.active ? "نشطة" : "مخفية"}</small></span><span><button data-edit-service="${s.id}">تعديل</button> <button data-remove-service="${s.id}">إخفاء</button></span></div>`).join("") : '<p class="muted">أضف أول خدمة من النموذج.</p>';
}
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function escapeAttr(value) { return escapeHtml(value); }
$("loginForm").addEventListener("submit", async e => {
  e.preventDefault(); const f = new FormData(e.currentTarget);
  try { await api("/api/admin/login",{method:"POST",body:JSON.stringify({username:f.get("username"),password:f.get("password")})}); $("loginCard").hidden=true; $("dashboard").hidden=false; await loadDashboard(); }
  catch(err){showMessage("loginMessage",err.message);}
});
$("logoutBtn").addEventListener("click",async()=>{await api("/api/logout",{method:"POST"});location.reload();});
$("refreshBtn").addEventListener("click",()=>loadDashboard().catch(e=>alert(e.message)));
$("serviceForm").addEventListener("submit",async e=>{
  e.preventDefault();const form=e.currentTarget;const f=new FormData(form);
  const body={platform:f.get("platform"),title:f.get("title"),description:f.get("description"),price:Number(f.get("price")),min_quantity:Number(f.get("min_quantity")),max_quantity:Number(f.get("max_quantity")),active:true};
  const serviceId = $("serviceId").value;
  try{await api(serviceId ? "/api/admin/services/"+serviceId : "/api/admin/services",{method:serviceId ? "PUT" : "POST",body:JSON.stringify(body)});form.reset();$("serviceId").value="";$("serviceSubmit").textContent="إضافة الخدمة";$("cancelEdit").hidden=true;showMessage("serviceMessage",serviceId ? "تم تحديث الخدمة والسعر." : "تمت إضافة الخدمة.");await loadDashboard();}
  catch(err){showMessage("serviceMessage",err.message);}
});
$("cancelEdit").addEventListener("click",()=>{ $("serviceForm").reset(); $("serviceId").value=""; $("serviceSubmit").textContent="إضافة الخدمة"; $("cancelEdit").hidden=true; showMessage("serviceMessage","تم إلغاء التعديل."); });
document.addEventListener("click",async e=>{
  const save=e.target.closest("[data-save-order]");
  const remove=e.target.closest("[data-remove-service]");
  const edit=e.target.closest("[data-edit-service]");
  try{
    if(edit){const services=await api("/api/admin/services");const s=services.find(x=>x.id===Number(edit.dataset.editService));if(!s)return;const form=$("serviceForm");form.elements.platform.value=s.platform;form.elements.title.value=s.title;form.elements.description.value=s.description;form.elements.price.value=s.price;form.elements.min_quantity.value=s.min_quantity;form.elements.max_quantity.value=s.max_quantity;$("serviceId").value=s.id;$("serviceSubmit").textContent="حفظ التعديلات";$("cancelEdit").hidden=false;showMessage("serviceMessage","تعديل الخدمة: "+s.title);form.scrollIntoView({behavior:"smooth",block:"center"});}
    if(save){const id=save.dataset.saveOrder;const status=$("status-"+id).value;await api("/api/admin/orders/"+id,{method:"PATCH",body:JSON.stringify({status,admin_note:""})});await loadDashboard();}
    if(remove){if(!confirm("متأكد إنك عايز تزيل الخدمة؟ لو عليها طلبات سابقة هنحتفظ بسجلها ونمنع طلبها من المتجر."))return;const result=await api("/api/admin/services/"+remove.dataset.removeService,{method:"DELETE"});alert(result.message);await loadDashboard();}
  }catch(err){alert(err.message);}
});
api("/api/admin/summary").then(()=>{$("loginCard").hidden=true;$("dashboard").hidden=false;return loadDashboard();}).catch(()=>{});
