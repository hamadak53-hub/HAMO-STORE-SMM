const $ = (id) => document.getElementById(id);
const serviceGrid = $("serviceGrid"), modal = $("orderModal"), serviceInput = $("serviceName"), feedback = $("formFeedback");
let selectedServiceId = 0, catalog = [], loggedInUser = null;
const titles = {tiktok:"خدمات تيك توك",instagram:"خدمات إنستجرام",facebook:"خدمات فيسبوك",youtube:"خدمات يوتيوب",telegram:"خدمات تليجرام",snapchat:"خدمات سناب شات",x:"خدمات X / تويتر",linkedin:"خدمات لينكدإن",threads:"خدمات Threads",discord:"خدمات Discord",spotify:"خدمات Spotify",twitch:"خدمات Twitch",jaco:"خدمات Jaco",other:"خدمات أخرى"};
async function loadServices(platform="tiktok"){
  try { const res=await fetch("/api/services"); catalog=await res.json(); } catch(e){ catalog=[]; }
  $("selectedPlatformTitle").textContent=titles[platform]||"الخدمات المتاحة";
  const items=catalog.filter(s=>s.platform===platform&&s.active);
  serviceGrid.innerHTML="";
  if(!items.length){serviceGrid.innerHTML='<div class="empty-state">الخدمات دي لسه مش مضافة. تابعنا قريبًا ❤️</div>';return;}
  items.forEach((s,i)=>{const card=document.createElement("article");card.className="service-card";
    const icon=document.createElement("div");icon.className="service-icon";icon.textContent=["♥","◉","♟"][i%3];
    const info=document.createElement("div");const h=document.createElement("h4");h.textContent=s.title;const p=document.createElement("p");p.textContent=(s.description||"متاحة للطلب")+" · "+s.price+" جنيه / 1000";info.append(h,p);
    const btn=document.createElement("button");btn.className="order-btn";btn.textContent=loggedInUser?"اطلب الخدمة ←":"سجّل الدخول للطلب ←";btn.dataset.id=s.id;btn.dataset.title=s.title;btn.dataset.min=s.min_quantity;btn.dataset.max=s.max_quantity;
    card.append(icon,info,btn);serviceGrid.append(card);
  });
}
document.querySelectorAll(".platform-card").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".platform-card").forEach(x=>x.classList.remove("active"));b.classList.add("active");loadServices(b.dataset.platform);}));
function openOrder(btn){selectedServiceId=Number(btn.dataset.id);serviceInput.value=btn.dataset.title;$("quantity").min=btn.dataset.min;$("quantity").max=btn.dataset.max;feedback.textContent="";
  ["customerName","customerEmail","customerPhone","customerPassword"].forEach(id=>{const el=$(id);const wrap=el.previousElementSibling;const visible=!loggedInUser&&id!=="customerPhone";el.required=visible;if(wrap&&wrap.tagName==="LABEL")wrap.hidden=!!loggedInUser;el.hidden=!!loggedInUser;if(id==="customerName"&&loggedInUser)el.value=loggedInUser.name;if(id==="customerEmail"&&loggedInUser)el.value=loggedInUser.email;});
  $("customerLogin").hidden=!!loggedInUser;$("orderForm").querySelector(".submit-btn").textContent=loggedInUser?"تأكيد الطلب ←":"إنشاء الحساب وإرسال الطلب ←";
  modal.classList.add("open");modal.setAttribute("aria-hidden","false");document.body.style.overflow="hidden";$("accountLink").focus();}
function closeOrder(){modal.classList.remove("open");modal.setAttribute("aria-hidden","true");document.body.style.overflow="";}
serviceGrid.addEventListener("click",async e=>{
  const btn=e.target.closest("button[data-id]");if(!btn)return;
  try {
    const res=await fetch("/api/me",{credentials:"same-origin"});
    if(!res.ok){window.location.href="/login?next=/";return;}
    loggedInUser=await res.json();
    openOrder(btn);
  } catch { window.location.href="/login?next=/"; }
});
$("modalClose").addEventListener("click",closeOrder);modal.addEventListener("click",e=>{if(e.target===modal)closeOrder();});document.addEventListener("keydown",e=>{if(e.key==="Escape")closeOrder();});
$("customerLogin").addEventListener("click",async()=>{const email=prompt("اكتب البريد الإلكتروني");if(!email)return;const password=prompt("اكتب كلمة المرور");if(!password)return;try{const res=await fetch("/api/login",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});const data=await res.json();if(!res.ok)throw new Error(data.detail||"تعذر تسجيل الدخول");$("customerName").required=false;$("customerPassword").required=false;$("customerName").value=data.user.name;$("customerEmail").value=data.user.email;$("customerPassword").value="";feedback.textContent="تم تسجيل الدخول. كمل طلبك."; }catch(err){feedback.textContent=err.message;}});
$("orderForm").addEventListener("submit",async e=>{e.preventDefault();const link=$("accountLink").value.trim(),quantity=Number($("quantity").value),email=$("customerEmail").value.trim(),password=$("customerPassword").value,name=$("customerName").value.trim(),phone=$("customerPhone").value.trim();
  if(!selectedServiceId||!link||!Number.isInteger(quantity)||quantity<Number($("quantity").min)||quantity>Number($("quantity").max)){feedback.textContent="راجع الخدمة والرابط والكمية.";return;}
  feedback.textContent="جاري إنشاء الحساب وإرسال الطلب...";
  try{const me=await fetch("/api/me",{credentials:"same-origin"});if(me.status===401){const reg=await fetch("/api/register",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,email,phone,password})});const rd=await reg.json();if(!reg.ok)throw new Error(rd.detail||"تعذر إنشاء الحساب");loggedInUser=rd.user;}else if(!me.ok)throw new Error("تعذر التحقق من الحساب");else loggedInUser=await me.json();
    const res=await fetch("/api/orders",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({service_id:selectedServiceId,target_link:link,quantity})});const data=await res.json();if(!res.ok)throw new Error(data.detail||"تعذر إرسال الطلب");feedback.textContent="تم إنشاء طلبك رقم #"+data.order.id+". احتفظ بالرقم لمتابعته.";
  }catch(err){feedback.textContent=err.message;}
});
$("menuToggle").addEventListener("click",()=>document.querySelector(".desktop-nav").classList.toggle("show"));document.querySelectorAll(".desktop-nav a").forEach(a=>a.addEventListener("click",()=>document.querySelector(".desktop-nav").classList.remove("show")));
$("year").textContent=new Date().getFullYear();fetch("/api/me",{credentials:"same-origin"}).then(r=>r.ok?r.json():null).then(user=>{loggedInUser=user;document.querySelectorAll(".order-btn").forEach(btn=>{btn.textContent=loggedInUser?"اطلب الخدمة ←":"سجّل الدخول للطلب ←";});}).catch(()=>{});loadServices();