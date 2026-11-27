const $=id=>document.getElementById(id);
async function api(url,options={}){const r=await fetch(url,{credentials:"same-origin",headers:{"Content-Type":"application/json",...(options.headers||{})},...options});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"حدث خطأ، حاول مرة أخرى");return d}
const money=n=>Number(n||0).toLocaleString("ar-EG")+" ج.م";
const date=s=>new Date(s).toLocaleString("ar-EG");
const kinds={deposit:"شحن رصيد",order:"طلب خدمة",refund:"استرداد",adjustment:"تعديل إداري"};
const states={pending:"قيد المراجعة",approved:"تمت الموافقة",rejected:"مرفوض"};
function render(data){
 $("balance").innerHTML=money(data.balance).replace(" ج.م","")+" <small>جنيه</small>";
 $("transactions").innerHTML=data.transactions.length?data.transactions.map(t=>'<article class="row"><div><b>'+ (kinds[t.kind]||t.kind)+'</b><small>'+t.note+' · '+date(t.created_at)+'</small></div><strong class="'+(t.amount>=0?"plus":"minus")+'">'+(t.amount>0?"+":"")+money(t.amount)+'<small>الرصيد: '+money(t.balance_after)+'</small></strong></article>').join(""):'<p class="hint">لا توجد عمليات حتى الآن.</p>';
 $("deposits").innerHTML=data.deposits.length?data.deposits.map(d=>'<article class="row"><div><b>طلب شحن #'+d.id+' · '+money(d.amount)+'</b><small>'+d.method+' · '+date(d.created_at)+(d.sender_reference?' · مرجع: '+d.sender_reference:'')+'</small>'+(d.admin_note?'<small>ملاحظة الإدارة: '+d.admin_note+'</small>':'')+'</div><span class="state '+d.status+'">'+(states[d.status]||d.status)+'</span></article>').join(""):'<p class="hint">لم ترسل طلبات شحن بعد.</p>';
}
async function load(){try{await api("/api/me");const data=await api("/api/wallet");render(data)}catch(e){if(e.message.includes("سجل الدخول")){$("loginPanel").hidden=false;document.querySelector(".balance-card").hidden=true;document.querySelector(".layout").hidden=true;document.querySelector(".deposits").hidden=true;return} $("feedback").textContent=e.message}}
$("walletLogin").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await api("/api/login",{method:"POST",body:JSON.stringify({email:f.get("email"),password:f.get("password")})});location.reload()}catch(err){$("loginFeedback").textContent=err.message}});
$("depositForm").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.currentTarget);$("feedback").textContent="جاري إرسال الطلب...";try{const d=await api("/api/deposits",{method:"POST",body:JSON.stringify({amount:Number(f.get("amount")),method:f.get("method"),sender_reference:f.get("sender_reference")})});$("feedback").textContent=d.message;e.currentTarget.reset();await load()}catch(err){$("feedback").textContent=err.message}});
load();