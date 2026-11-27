const $ = id => document.getElementById(id);
async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "حصل خطأ، حاول مرة تانية");
  return data;
}
function showMessage(id, message) { $(id).textContent = message; }
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function escapeAttr(value) { return escapeHtml(value); }

const serviceTemplates = [
  ["tiktok","ترويج فيديو TikTok عبر حملة إعلانية","إعداد حملة ترويج مدفوعة عبر أدوات الإعلان الرسمية."],
  ["tiktok","إدارة حملة TikTok للحساب التجاري","إعداد ومتابعة حملة إعلانية للحساب التجاري."],
  ["instagram","ترويج منشور Instagram بإعلان رسمي","حملة ترويج مدفوعة للوصول إلى جمهور مستهدف."],
  ["facebook","ترويج منشور Facebook بإعلان رسمي","حملة إعلانية لزيادة الوصول الحقيقي للمنشور."],
  ["youtube","ترويج فيديو YouTube عبر Google Ads","حملة فيديو مدفوعة عبر Google Ads."],
  ["telegram","ترويج قناة Telegram بإعلانات مباشرة","ترويج القناة عبر قنوات ومجتمعات ذات صلة."]
];
for (const [platform,title,description] of serviceTemplates) {
  const option = document.createElement("option");
  option.value = String(serviceTemplates.indexOf(serviceTemplates.find(x => x[1] === title)));
  option.textContent = platform.toUpperCase()+" — "+title;
  $("serviceTemplate").append(option);
}
$("serviceTemplate").addEventListener("change", () => {
  const item = serviceTemplates[Number($("serviceTemplate").value)];
  if (!item) return;
  const form = $("serviceForm");
  form.elements.platform.value = item[0];
  form.elements.title.value = item[1];
  form.elements.description.value = item[2];
  form.elements.min_quantity.value = 1;
  form.elements.max_quantity.value = 1;
  form.elements.price.value = "";
  form.elements.active.checked = false;
  $("serviceId").value = "";
  $("serviceSubmit").textContent = "إضافة الخدمة";
  $("cancelEdit").hidden = true;
});

async function loadProviderStatus() {
  try {
    const d = await api("/api/admin/provider/status");
    $("providerBalance").textContent = "متصل · الرصيد: "+d.balance+" "+d.currency;
  } catch (e) { $("providerBalance").textContent = e.message; }
}
async function loadProviderServices() {
  $("providerServices").textContent = "جاري تحميل خدمات TikTok من المورد...";
  try {
    const items = await api("/api/admin/provider/services");
    $("providerServices").innerHTML = items.length ? items.map(s =>
      '<article class="order-row"><b>'+escapeHtml(s.name)+'</b><p>رقم الخدمة: '+escapeHtml(s.provider_service_id)+' · السعر: '+escapeHtml(s.rate_usd)+'</p><p>الكمية: '+escapeHtml(s.min)+' إلى '+escapeHtml(s.max)+'</p><button data-import-provider="'+escapeHtml(s.provider_service_id)+'">استيراد للمتجر</button></article>'
    ).join("") : '<p class="muted">لا توجد خدمات TikTok في كتالوج المورد.</p>';
  } catch (e) { $("providerServices").textContent = e.message; }
}
$("providerCheck").addEventListener("click", loadProviderStatus);
$("providerLoadServices").addEventListener("click", loadProviderServices);

function renderOrders(orders) {
  const labels = {pending_payment:"بانتظار الدفع",paid:"تم الدفع",processing:"قيد التنفيذ",completed:"مكتمل",rejected:"مرفوض",cancelled:"ملغي"};
  const transitions = {pending_payment:["paid","rejected","cancelled"],paid:["processing","rejected","cancelled"],processing:["completed"],completed:[],rejected:[],cancelled:[]};
  $("ordersList").innerHTML = orders.length ? orders.map(o => {
    const options = [o.status,...(transitions[o.status] || [])];
    return '<article class="order-row"><div class="order-top"><b>طلب #'+o.id+' · '+escapeHtml(o.service_title)+'</b><span>'+o.total_price+' ج.م</span></div><p>العميل رقم '+o.customer_id+' · الكمية: '+o.quantity+'</p><p><a href="'+escapeAttr(o.target_link)+'" target="_blank" rel="noopener">فتح الرابط</a></p><p>الحالة: '+(labels[o.status] || o.status)+'</p><div class="order-actions"><select id="status-'+o.id+'">'+options.map(k=>'<option value="'+k+'">'+(labels[k]||k)+'</option>').join("")+'</select><button data-save-order="'+o.id+'">حفظ الحالة</button></div></article>';
  }).join("") : '<p class="muted">لسه مفيش طلبات.</p>';
}
function renderDeposits(items) {
  const methods = {vodafone_cash:"فودافون كاش",instapay:"إنستاباي",bank_transfer:"تحويل بنكي"};
  const states = {pending:"قيد المراجعة",approved:"تمت الموافقة",rejected:"مرفوض"};
  $("depositsList").innerHTML = items.length ? items.map(d =>
    '<article class="order-row"><div class="order-top"><b>شحن #'+d.id+' · '+d.amount+' جنيه</b><span>'+(states[d.status]||d.status)+'</span></div><p>العميل: '+escapeHtml(d.customer_name||("رقم "+d.customer_id))+' · '+escapeHtml(d.customer_email||"")+'</p><p>الطريقة: '+(methods[d.method]||d.method)+' · مرجع التحويل: '+escapeHtml(d.sender_reference||"غير مضاف")+'</p>'+
    (d.status==="pending" ? '<div class="order-actions"><button data-deposit-action="approved" data-deposit-id="'+d.id+'">تأكيد وإضافة الرصيد</button><button class="reject" data-deposit-action="rejected" data-deposit-id="'+d.id+'">رفض الطلب</button></div>' : (d.admin_note?'<p>ملاحظة: '+escapeHtml(d.admin_note)+'</p>':""))+'</article>'
  ).join("") : '<p class="muted">لا توجد طلبات شحن حتى الآن.</p>';
}
function renderServices(services) {
  const platforms = {tiktok:"TikTok",instagram:"Instagram",facebook:"Facebook",youtube:"YouTube",telegram:"Telegram"};
  $("serviceList").innerHTML = services.length ? services.map(s =>
    '<div class="service-row"><span><b>'+escapeHtml(s.title)+'</b><br><small>'+(platforms[s.platform]||escapeHtml(s.platform))+' · '+s.price+' جنيه / 1000 · '+(s.active?"نشطة":"مخفية")+'</small></span><span><button data-edit-service="'+s.id+'">تعديل</button> <button data-remove-service="'+s.id+'">إخفاء</button></span></div>'
  ).join("") : '<p class="muted">أضف أول خدمة من النموذج.</p>';
}
async function loadDashboard() {
  loadProviderStatus().catch(() => {});
  const summary = await api("/api/admin/summary");
  $("customersCount").textContent = summary.customers;
  $("ordersCount").textContent = summary.orders;
  $("pendingCount").textContent = summary.pending;
  $("revenueCount").textContent = Number(summary.revenue).toLocaleString("ar-EG");
  const [orders,services,deposits] = await Promise.all([
    api("/api/admin/orders"),api("/api/admin/services"),api("/api/admin/deposits")
  ]);
  renderOrders(orders); renderServices(services); renderDeposits(deposits);
}

$("loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  const button = e.currentTarget.querySelector('button[type="submit"],button:not([type])');
  const f = new FormData(e.currentTarget);
  showMessage("loginMessage","جاري تسجيل الدخول...");
  if (button) button.disabled = true;
  try {
    await api("/api/admin/login",{method:"POST",body:JSON.stringify({username:f.get("username"),password:f.get("password")})});
    $("loginCard").hidden = true;
    $("dashboard").hidden = false;
    await loadDashboard();
  } catch (err) {
    showMessage("loginMessage",err.message);
  } finally { if (button) button.disabled = false; }
});
$("logoutBtn").addEventListener("click",async()=>{try{await api("/api/logout",{method:"POST"});}finally{location.reload();}});
$("refreshBtn").addEventListener("click",()=>loadDashboard().catch(e=>alert(e.message)));
$("refreshDeposits").addEventListener("click",()=>loadDashboard().catch(e=>alert(e.message)));
$("serviceForm").addEventListener("submit",async e=>{
  e.preventDefault();
  const form=e.currentTarget, f=new FormData(form), serviceId=$("serviceId").value;
  const body={platform:f.get("platform"),title:f.get("title"),description:f.get("description"),price:Number(f.get("price")),min_quantity:Number(f.get("min_quantity")),max_quantity:Number(f.get("max_quantity")),active:form.elements.active.checked};
  try {
    await api(serviceId?"/api/admin/services/"+serviceId:"/api/admin/services",{method:serviceId?"PUT":"POST",body:JSON.stringify(body)});
    form.reset(); $("serviceId").value=""; $("serviceSubmit").textContent="إضافة الخدمة"; $("cancelEdit").hidden=true;
    showMessage("serviceMessage",serviceId?"تم تحديث الخدمة والسعر.":"تمت إضافة الخدمة.");
    await loadDashboard();
  } catch(err) { showMessage("serviceMessage",err.message); }
});
$("cancelEdit").addEventListener("click",()=>{$("serviceForm").reset();$("serviceId").value="";$("serviceSubmit").textContent="إضافة الخدمة";$("cancelEdit").hidden=true;});
document.addEventListener("click",async e=>{
  const save=e.target.closest("[data-save-order]"), remove=e.target.closest("[data-remove-service]"), edit=e.target.closest("[data-edit-service]"), deposit=e.target.closest("[data-deposit-action]"), imp=e.target.closest("[data-import-provider]");
  try {
    if(imp){
      const price=Number(prompt("اكتب سعر البيع لكل 1000 بالجنيه المصري:"));
      if(!Number.isInteger(price)||price<1)return;
      await api("/api/admin/provider/import",{method:"POST",body:JSON.stringify({provider_service_id:imp.dataset.importProvider,selling_price_egp:price,active:false})});
      alert("تم استيراد الخدمة وهي مخفية لحين مراجعة السعر."); await loadDashboard(); return;
    }
    if(deposit){
      const status=deposit.dataset.depositAction,id=deposit.dataset.depositId;
      const note=status==="rejected"?(prompt("سبب رفض طلب الشحن (اختياري):")||""):"";
      if(!confirm(status==="approved"?"تأكيد استلام التحويل وإضافة الرصيد؟":"تأكيد رفض طلب الشحن؟"))return;
      await api("/api/admin/deposits/"+id,{method:"PATCH",body:JSON.stringify({status,admin_note:note})}); await loadDashboard(); return;
    }
    if(edit){
      const services=await api("/api/admin/services"),s=services.find(x=>x.id===Number(edit.dataset.editService));
      if(!s)return;
      const form=$("serviceForm");
      form.elements.platform.value=s.platform;form.elements.title.value=s.title;form.elements.description.value=s.description;
      form.elements.price.value=s.price;form.elements.min_quantity.value=s.min_quantity;form.elements.max_quantity.value=s.max_quantity;
      form.elements.active.checked=s.active;$("serviceId").value=s.id;$("serviceSubmit").textContent="حفظ التعديلات";$("cancelEdit").hidden=false;
      form.scrollIntoView({behavior:"smooth",block:"center"});return;
    }
    if(save){const id=save.dataset.saveOrder;await api("/api/admin/orders/"+id,{method:"PATCH",body:JSON.stringify({status:$("status-"+id).value,admin_note:""})});await loadDashboard();return;}
    if(remove){
      if(!confirm("متأكد إنك عايز تخفي الخدمة؟"))return;
      const result=await api("/api/admin/services/"+remove.dataset.removeService,{method:"DELETE"});alert(result.message);await loadDashboard();
    }
  } catch(err){alert(err.message);}
});
api("/api/admin/summary").then(()=>{$("loginCard").hidden=true;$("dashboard").hidden=false;return loadDashboard();}).catch(()=>{});
