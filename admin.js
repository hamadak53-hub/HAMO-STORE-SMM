const $ = (id) => document.getElementById(id);
async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "حصل خطأ، حاول مرة تانية");
  return data;
}
function showMessage(id, text) { $(id).textContent = text; }
const serviceTemplates = [{"platform":"tiktok","title":"ترويج فيديو TikTok عبر حملة إعلانية","description":"إعداد أو إدارة حملة ترويج مدفوعة للوصول إلى جمهور حقيقي عبر أدوات الإعلان الرسمية."},{"platform":"tiktok","title":"إدارة حملة TikTok للحساب التجاري","description":"إعداد ومتابعة حملة إعلانية للحساب أو النشاط التجاري."},{"platform":"instagram","title":"ترويج منشور Instagram بإعلان رسمي","description":"إعداد حملة ترويج مدفوعة لمنشور للوصول إلى جمهور مستهدف حقيقي."},{"platform":"instagram","title":"إدارة حملة Instagram للحساب التجاري","description":"إعداد ومتابعة حملة إعلانية للحساب أو النشاط التجاري."},{"platform":"facebook","title":"ترويج منشور Facebook بإعلان رسمي","description":"إعداد حملة إعلانية لزيادة الوصول الحقيقي للمنشور."},{"platform":"facebook","title":"إدارة حملة Facebook للصفحة","description":"إعداد ومتابعة حملة إعلانية للصفحة أو النشاط التجاري."},{"platform":"youtube","title":"ترويج فيديو YouTube عبر Google Ads","description":"إعداد حملة فيديو مدفوعة للوصول إلى مشاهدين حقيقيين وفق سياسات YouTube."},{"platform":"youtube","title":"إدارة حملة إعلانية لقناة YouTube","description":"إعداد ومتابعة حملات ترويج محتوى القناة عبر أدوات Google Ads."},{"platform":"telegram","title":"ترويج قناة Telegram بإعلانات مباشرة","description":"تنسيق ترويج القناة عبر قنوات أو مجتمعات ذات صلة وبموافقة أصحابها."},{"platform":"telegram","title":"إدارة حملة اكتساب مشتركين حقيقيين لقناة Telegram","description":"تخطيط وقياس حملة ترويج للقناة عبر مصادر معلنة ومصرح بها."}];
function loadServiceTemplates(){
  const select=$("serviceTemplate");
  serviceTemplates.forEach((item,index)=>{const option=document.createElement("option");option.value=String(index);option.textContent=item.platform.toUpperCase()+" — "+item.title;select.append(option);});
}
loadServiceTemplates();
$("serviceTemplate").addEventListener("change",()=>{
  const item=serviceTemplates[Number($("serviceTemplate").value)];
  if(!item)return;
  const form=$("serviceForm");
  form.elements.platform.value=item.platform;
  form.elements.title.value=item.title;
  form.elements.description.value=item.description;
  form.elements.min_quantity.value=1;
  form.elements.max_quantity.value=1;
  form.elements.price.value="";
  form.elements.active.checked=false;
  $("serviceId").value="";
  $("serviceSubmit").textContent="إضافة الخدمة";
  $("cancelEdit").hidden=true;
  showMessage("serviceMessage","قالب جاهز: حدد سعر التنفيذ والكمية بعد الاتفاق مع المنفذ.");
});
async function loadDashboard() {
  const summary = await api("/api/admin/summary");
  $("customersCount").textContent = summary.customers;
  $("ordersCount").textContent = summary.orders;
  $("pendingCount").textContent = summary.pending;
  $("revenueCount").textContent = summary.revenue.toLocaleString("ar-EG");
  const [orders, services, deposits] = await Promise.all([api("/api/admin/orders"), api("/api/admin/services"), api("/api/admin/deposits")]);
  renderOrders(orders);
  renderServices(services);
  renderDeposits(deposits);
}
function renderOrders(orders) {
  const labels = {pending_payment:"بانتظار الدفع",paid:"تم الدفع",processing:"قيد التنفيذ",completed:"مكتمل",rejected:"مرفوض",cancelled:"ملغي"};
  const transitions = {pending_payment:["paid","rejected","cancelled"],paid:["processing","rejected","cancelled"],processing:["completed"],completed:[],rejected:[],cancelled:[]};
  $("ordersList").innerHTML = orders.length ? orders.map(o => {
    const options=[o.status,...(transitions[o.status]||[])];
    return `<article class="order-row"><div class="order-top"><b>طلب #${o.id} · ${escapeHtml(o.service_title)}</b><span>${o.total_price} ج.م</span></div><p>العميل رقم ${o.customer_id} · الكمية: ${o.quantity}</p><p><a href="${escapeAttr(o.target_link)}" target="_blank" rel="noopener">فتح الرابط</a></p><p>الحالة: ${labels[o.status] || o.status}</p><div class="order-actions"><select id="status-${o.id}">${options.map(k=>`<option value="${k}">${labels[k]||k}</option>`).join("")}</select><button data-save-order="${o.id}">حفظ الحالة</button></div></article>`;
  }).join("") : '<p class="muted">لسه مفيش طلبات.</p>';
}
function renderDeposits(items) {
  const methods={vodafone_cash:"فودافون كاش",instapay:"إنستاباي",bank_transfer:"تحويل بنكي"};
  const states={pending:"قيد المراجعة",approved:"تمت الموافقة",rejected:"مرفوض"};
  const pending=items.filter(x=>x.status==="pending");
  $("depositsList").innerHTML=items.length?items.map(d=>`<article class="order-row"><div class="order-top"><b>شحن #${d.id} · ${d.amount} جنيه</b><span>${states[d.status]||d.status}</span></div><p>العميل: ${escapeHtml(d.customer_name||("رقم "+d.customer_id))} · ${escapeHtml(d.customer_email||"")}</p><p>الطريقة: ${methods[d.method]||d.method} · مرجع التحويل: ${escapeHtml(d.sender_reference||"غير مضاف")}</p>${d.status==="pending"?`<div class="order-actions"><button data-deposit-action="approved" data-deposit-id="${d.id}">تأكيد وإضافة الرصيد</button><button class="reject" data-deposit-action="rejected" data-deposit-id="${d.id}">رفض الطلب</button></div>`:d.admin_note?`<p>ملاحظة: ${escapeHtml(d.admin_note)}</p>`:""}</article>`).join(""):'<p class="muted">لا توجد طلبات شحن حتى الآن.</p>';
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
$("refreshDeposits").addEventListener("click",()=>loadDashboard().catch(e=>alert(e.message)));
$("serviceForm").addEventListener("submit",async e=>{
  e.preventDefault();const form=e.currentTarget;const f=new FormData(form);
  const body={platform:f.get("platform"),title:f.get("title"),description:f.get("description"),price:Number(f.get("price")),min_quantity:Number(f.get("min_quantity")),max_quantity:Number(f.get("max_quantity")),active:form.elements.active.checked};
  const serviceId = $("serviceId").value;
  try{await api(serviceId ? "/api/admin/services/"+serviceId : "/api/admin/services",{method:serviceId ? "PUT" : "POST",body:JSON.stringify(body)});form.reset();$("serviceId").value="";$("serviceSubmit").textContent="إضافة الخدمة";$("cancelEdit").hidden=true;showMessage("serviceMessage",serviceId ? "تم تحديث الخدمة والسعر." : "تمت إضافة الخدمة.");await loadDashboard();}
  catch(err){showMessage("serviceMessage",err.message);}
});
$("cancelEdit").addEventListener("click",()=>{ $("serviceForm").reset(); $("serviceId").value=""; $("serviceSubmit").textContent="إضافة الخدمة"; $("cancelEdit").hidden=true; showMessage("serviceMessage","تم إلغاء التعديل."); });
document.addEventListener("click",async e=>{
  const save=e.target.closest("[data-save-order]");
  const remove=e.target.closest("[data-remove-service]");
  const edit=e.target.closest("[data-edit-service]");
  const deposit=e.target.closest("[data-deposit-action]");
  try{
    if(deposit){const id=deposit.dataset.depositId;const status=deposit.dataset.depositAction;const note=status==="rejected"?(prompt("سبب رفض طلب الشحن (اختياري):")||""):"";if(status==="rejected"&&!confirm("تأكيد رفض طلب الشحن؟"))return;if(status==="approved"&&!confirm("تأكيد استلام التحويل وإضافة المبلغ إلى محفظة العميل؟"))return;await api("/api/admin/deposits/"+id,{method:"PATCH",body:JSON.stringify({status,admin_note:note})});await loadDashboard();return;}
    if(edit){const services=await api("/api/admin/services");const s=services.find(x=>x.id===Number(edit.dataset.editService));if(!s)return;const form=$("serviceForm");form.elements.platform.value=s.platform;form.elements.title.value=s.title;form.elements.description.value=s.description;form.elements.price.value=s.price;form.elements.min_quantity.value=s.min_quantity;form.elements.max_quantity.value=s.max_quantity;form.elements.active.checked=s.active;$("serviceId").value=s.id;$("serviceSubmit").textContent="حفظ التعديلات";$("cancelEdit").hidden=false;showMessage("serviceMessage","تعديل الخدمة: "+s.title);form.scrollIntoView({behavior:"smooth",block:"center"});}
    if(save){const id=save.dataset.saveOrder;const status=$("status-"+id).value;await api("/api/admin/orders/"+id,{method:"PATCH",body:JSON.stringify({status,admin_note:""})});await loadDashboard();}
    if(remove){if(!confirm("متأكد إنك عايز تزيل الخدمة؟ لو عليها طلبات سابقة هنحتفظ بسجلها ونمنع طلبها من المتجر."))return;const result=await api("/api/admin/services/"+remove.dataset.removeService,{method:"DELETE"});alert(result.message);await loadDashboard();}
  }catch(err){alert(err.message);}
});
api("/api/admin/summary").then(()=>{$("loginCard").hidden=true;$("dashboard").hidden=false;return loadDashboard();}).catch(()=>{});
