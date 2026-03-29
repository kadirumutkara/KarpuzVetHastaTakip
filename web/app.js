const state = {
  token: null,
  session: null,
  cases: [],
  users: [],
  testTypes: [],
  selectedTests: [],
  selectedCaseId: null,
  selectedUserId: null,
  selectedTestTypeId: null,
  selectedTestCategory: "Tumu",
};

const shortFields = [
  ["protocol_no", "Protokol No"],
  ["acceptance_date", "Kabul Tarihi"],
  ["sender_clinic", "Gonderen Klinik"],
  ["owner_name", "Hayvan Sahibi"],
  ["owner_phone", "Telefon"],
  ["patient_name", "Hasta Adi"],
  ["species", "Tur"],
  ["breed", "Irk"],
  ["birth_date", "Dogum Tarihi"],
  ["gender", "Cinsiyet"],
  ["neutered", "Kisirlik"],
  ["material", "Materyal"],
  ["sample_location", "Numune Bolgesi"],
  ["urgency", "Oncelik"],
  ["status", "Durum"],
  ["assigned_pathologist", "Sorumlu Patolog"],
  ["fee", "Ucret"],
];
const longFields = [
  ["pre_diagnosis", "On Tani / Hikaye"],
  ["gross_findings", "Makroskopi"],
  ["micro_findings", "Histopatoloji"],
  ["diagnosis", "Tani"],
  ["report_summary", "Sonuc Ozeti"],
  ["notes", "Notlar"],
];

function el(id){ return document.getElementById(id); }

function formatMoney(value){
  return `${Number(value || 0).toFixed(2)} TL`;
}

function triggerPdfDownload(endpoint){
  if(!state.selectedCaseId){
    el("case-message").textContent = "PDF için önce bir vaka seçin.";
    return;
  }
  const url = `${endpoint}?token=${encodeURIComponent(state.token)}&id=${state.selectedCaseId}&download=1`;
  window.open(url, "_blank", "noopener");
  el("case-message").textContent = "PDF indiriliyor...";
}

function switchScreen(id){
  document.querySelectorAll(".screen").forEach(x=>x.classList.remove("active"));
  el(id).classList.add("active");
}

function switchTab(name){
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active", x.dataset.tab===name));
  document.querySelectorAll(".tab-panel").forEach(x=>x.classList.toggle("active", x.id===`tab-${name}`));
}

async function api(path, options={}){
  const response = await fetch(path, {
    headers: {"Content-Type":"application/json"},
    ...options
  });
  const data = await response.json();
  if(!response.ok || data.ok===false) throw new Error(data.error || "İşlem başarısız");
  return data;
}

function buildForm(containerId, fields, long=false){
  const container = el(containerId);
  for (const [name, label] of fields){
    const wrap = document.createElement("div");
    if(long) wrap.className = "field-full";
    let inputHtml = `<input data-field="${name}" type="text">`;
    if (long) {
      inputHtml = `<textarea data-field="${name}"></textarea>`;
    } else if (name === "status") {
      inputHtml = `<select data-field="${name}"><option>Kabul Edildi</option><option>Makroskopi Bekliyor</option><option>Rapor Hazirlaniyor</option><option>Tamamlandi</option></select>`;
    } else if (name === "fee") {
      inputHtml = `<input data-field="${name}" type="number" step="0.01" min="0" readonly>`;
    } else if (name === "acceptance_date" || name === "birth_date") {
      inputHtml = `<input data-field="${name}" type="date">`;
    }
    wrap.innerHTML = `<label>${label}</label>${inputHtml}`;
    container.appendChild(wrap);
  }
}

function getCasePayload(){
  const payload = {};
  document.querySelectorAll("#case-form [data-field]").forEach(node=>payload[node.dataset.field]=node.value);
  if(state.selectedCaseId) payload.id = state.selectedCaseId;
  payload.token = state.token;
  payload.selected_tests = state.selectedTests.map(item => ({
    test_type_id: item.test_type_id,
    quantity: Number(item.quantity || 1),
    unit_price: Number(item.unit_price || 0)
  }));
  return payload;
}

function fillCaseForm(item = {}){
  state.selectedCaseId = item.id || null;
  document.querySelectorAll("#case-form [data-field]").forEach(node=>{
    node.value = item[node.dataset.field] ?? "";
  });
  state.selectedTests = (item.tests || []).map(test => ({...test}));
  renderSelectedTests();
  renderSelectedCaseSummary(item.id ? item : null);
  if (!state.selectedTests.length) {
    const feeField = document.querySelector('#case-form [data-field="fee"]');
    if (feeField) feeField.value = item.fee ? Number(item.fee).toFixed(2) : "";
  }
}

function fillUserForm(item = {}){
  state.selectedUserId = item.id || null;
  document.querySelectorAll("#user-form [data-field]").forEach(node=>{
    if(node.dataset.field === "password") node.value = "";
    else node.value = item[node.dataset.field] ?? (node.dataset.field === "role" ? "user" : node.dataset.field === "is_active" ? "1" : "");
  });
}

function getUserPayload(){
  const payload = { token: state.token };
  document.querySelectorAll("#user-form [data-field]").forEach(node=>payload[node.dataset.field]=node.value);
  if(state.selectedUserId) payload.id = state.selectedUserId;
  return payload;
}

function getTestTypePayload(){
  const payload = { token: state.token };
  document.querySelectorAll("#test-type-form [data-field]").forEach(node=>payload[node.dataset.field]=node.value);
  if(state.selectedTestTypeId) payload.id = state.selectedTestTypeId;
  return payload;
}

function getUniqueCategories(){
  const categories = Array.from(new Set(state.testTypes.map(item => item.category || "Genel")));
  categories.sort((a, b) => a.localeCompare(b, "tr"));
  return ["Tumu", ...categories];
}

function renderStats(counts){
  el("stats").innerHTML = [
    ["Toplam", counts.total],
    ["Kabul", counts.kabul],
    ["Makro", counts.makro],
    ["Rapor", counts.rapor],
    ["Tamamlanan", counts.tamamlandi],
    ["Toplam Tutar", formatMoney(counts.total_revenue)],
  ].map(([k,v])=>`<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  const finance = el("finance-summary");
  if (finance) {
    finance.innerHTML = [
      ["Toplam İşlem Tutarı", formatMoney(counts.total_revenue)],
      ["Vaka Başına Ortalama", formatMoney(counts.average_revenue)],
      ["Tamamlanan Vaka", counts.tamamlandi],
    ].map(([label, value])=>`<div class="summary-box"><div class="label">${label}</div><div class="value">${value}</div></div>`).join("");
  }
}

function renderCases(targetId, cases){
  const table = el(targetId);
  table.innerHTML = `
    <thead><tr>
      <th>ID</th><th>Protokol</th><th>Hasta</th><th>Sahip</th><th>Klinik</th><th>Durum</th><th>Tutar</th><th>Kabul</th>
    </tr></thead>
    <tbody>
      ${cases.map(item=>`<tr class="clickable" data-case-id="${item.id}">
        <td>${item.id ?? ""}</td><td>${item.protocol_no ?? ""}</td><td>${item.patient_name ?? ""}</td>
        <td>${item.owner_name ?? ""}</td><td>${item.sender_clinic ?? ""}</td><td>${item.status ?? ""}</td><td>${formatMoney(item.fee)}</td><td>${item.acceptance_date ?? ""}</td>
      </tr>`).join("")}
    </tbody>`;
  table.querySelectorAll("[data-case-id]").forEach(row=>{
    row.addEventListener("click", ()=>{
      const item = state.cases.find(x=>String(x.id)===row.dataset.caseId);
      fillCaseForm(item);
      switchTab("case-form");
    });
  });
}

function renderSelectedCaseSummary(item){
  const target = el("selected-case-summary");
  if (!target) return;
  if (!item) {
    target.className = "case-summary empty-state";
    target.textContent = "Soldaki listeden bir hasta / vaka seçin.";
    return;
  }
  const testCount = (item.tests || []).reduce((sum, test) => sum + Number(test.quantity || 0), 0);
  target.className = "case-summary";
  target.innerHTML = [
    ["Protokol No", item.protocol_no],
    ["Hasta Adı", item.patient_name],
    ["Hayvan Sahibi", item.owner_name],
    ["Gönderen Klinik", item.sender_clinic],
    ["Tür / Irk", `${item.species || "-"} / ${item.breed || "-"}`],
    ["Materyal", item.material],
    ["Durum", item.status],
    ["Yapılan Tetkik", testCount ? `${testCount} adet` : "Henüz seçilmedi"],
    ["Toplam İşlem Tutarı", formatMoney(item.fee)],
    ["Tanı Özeti", item.diagnosis || item.report_summary || "-"],
  ].map(([label, value])=>`<div class="summary-row"><div class="label">${label}</div><div class="value">${value || "-"}</div></div>`).join("");
}

function renderUsers(){
  const table = el("users-table");
  table.innerHTML = `
    <thead><tr><th>ID</th><th>Kullanici</th><th>Ad Soyad</th><th>Rol</th><th>Durum</th></tr></thead>
    <tbody>
      ${state.users.map(item=>`<tr class="clickable" data-user-id="${item.id}">
        <td>${item.id}</td><td>${item.username}</td><td>${item.full_name ?? ""}</td><td>${item.role}</td><td>${item.is_active ? "Aktif":"Pasif"}</td>
      </tr>`).join("")}
    </tbody>`;
  table.querySelectorAll("[data-user-id]").forEach(row=>{
    row.addEventListener("click", ()=>{
      const item = state.users.find(x=>String(x.id)===row.dataset.userId);
      fillUserForm(item);
      switchTab("users");
    });
  });
}

function renderSelectedTests(){
  const table = el("case-tests-table");
  const total = state.selectedTests.reduce((sum, item)=>sum + Number(item.total_price || (item.quantity * item.unit_price)), 0);
  const feeField = document.querySelector('#case-form [data-field="fee"]');
  if (feeField) feeField.value = total ? total.toFixed(2) : "";
  table.innerHTML = `
    <thead><tr><th>Kod</th><th>Tetkik</th><th>Adet</th><th>Birim Fiyat</th><th>Toplam</th><th></th></tr></thead>
    <tbody>
      ${state.selectedTests.map((item, index)=>`<tr>
        <td>${item.test_code}</td><td>${item.test_name}</td>
        <td><input class="line-input test-quantity-input" data-index="${index}" type="number" min="1" value="${item.quantity}"></td>
        <td><input class="line-input test-price-input" data-index="${index}" type="number" min="0" step="0.01" value="${Number(item.unit_price).toFixed(2)}"></td>
        <td>${Number(item.total_price || item.quantity * item.unit_price).toFixed(2)}</td>
        <td><button class="secondary remove-test-button" data-index="${index}">Sil</button></td>
      </tr>`).join("")}
      <tr><td colspan="4"><b>Toplam</b></td><td><b>${total.toFixed(2)} TL</b></td><td></td></tr>
    </tbody>`;
  table.querySelectorAll(".test-quantity-input").forEach(input=>{
    input.addEventListener("input", ()=>{
      const item = state.selectedTests[Number(input.dataset.index)];
      if(!item) return;
      item.quantity = Math.max(1, Number(input.value || 1));
      item.total_price = item.quantity * Number(item.unit_price || 0);
      renderSelectedTests();
    });
  });
  table.querySelectorAll(".test-price-input").forEach(input=>{
    input.addEventListener("input", ()=>{
      const item = state.selectedTests[Number(input.dataset.index)];
      if(!item) return;
      item.unit_price = Math.max(0, Number(input.value || 0));
      item.total_price = item.quantity * Number(item.unit_price || 0);
      renderSelectedTests();
    });
  });
  table.querySelectorAll(".remove-test-button").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      state.selectedTests.splice(Number(btn.dataset.index), 1);
      renderSelectedTests();
    });
  });
}

function renderTestTypesTable(){
  const query = (el("test-type-search")?.value || "").trim().toLocaleLowerCase("tr");
  const filteredTypes = state.testTypes.filter(item => {
    if (!query) return true;
    return [item.code, item.name, item.category].some(value => String(value || "").toLocaleLowerCase("tr").includes(query));
  });
  const table = el("test-types-table");
  if (table) {
    table.innerHTML = `
      <thead><tr><th>ID</th><th>Kategori</th><th>Kod</th><th>Tetkik Adi</th><th>Fiyat</th><th>Durum</th></tr></thead>
      <tbody>
        ${filteredTypes.map(item=>`<tr class="clickable" data-test-type-id="${item.id}">
          <td>${item.id}</td><td>${item.category || "Genel"}</td><td>${item.code}</td><td>${item.name}</td><td>${Number(item.unit_price).toFixed(2)} TL</td><td>${item.is_active ? "Aktif":"Pasif"}</td>
        </tr>`).join("")}
      </tbody>`;
    table.querySelectorAll("[data-test-type-id]").forEach(row=>{
      row.addEventListener("click", ()=>{
        const item = state.testTypes.find(x=>String(x.id)===row.dataset.testTypeId);
        state.selectedTestTypeId = item.id;
        document.querySelectorAll("#test-type-form [data-field]").forEach(node=>{
          node.value = item[node.dataset.field] ?? "";
        });
        switchTab("pricing");
      });
    });
  }
  const categoryFilter = el("test-category-filter");
  if (categoryFilter) {
    const previousValue = state.selectedTestCategory || "Tumu";
    categoryFilter.innerHTML = getUniqueCategories().map(category=>`<option value="${category}">${category}</option>`).join("");
    categoryFilter.value = getUniqueCategories().includes(previousValue) ? previousValue : "Tumu";
    state.selectedTestCategory = categoryFilter.value;
  }
  const select = el("test-type-select");
  if (select) {
    const visibleTests = state.testTypes.filter(x=>x.is_active && (state.selectedTestCategory === "Tumu" || (x.category || "Genel") === state.selectedTestCategory));
    select.innerHTML = visibleTests.map(item=>`<option value="${item.id}">${item.category || "Genel"} / ${item.code} - ${item.name} (${Number(item.unit_price).toFixed(2)} TL)</option>`).join("");
  }
}

async function bootstrap(){
  const data = await api(`/api/bootstrap?token=${encodeURIComponent(state.token)}`);
  state.session = data.session;
  state.cases = data.cases;
  state.users = data.users || [];
  state.testTypes = data.test_types || [];
  el("session-info").textContent = `Giris yapan: ${state.session.full_name || state.session.username} (${state.session.role})`;
  renderStats(data.counts);
  renderCases("dashboard-table", state.cases.filter(x=>x.status !== "Tamamlandi"));
  renderCases("cases-table", state.cases);
  renderSelectedCaseSummary(state.selectedCaseId ? state.cases.find(item => item.id === state.selectedCaseId) : null);
  document.querySelectorAll(".admin-only").forEach(node=>node.classList.toggle("hidden", state.session.role !== "admin"));
  renderTestTypesTable();
  if(state.session.role === "admin") renderUsers();
}

document.addEventListener("DOMContentLoaded", ()=>{
  el("case-form").innerHTML = "";
  buildForm("case-form", shortFields);
  buildForm("case-form", longFields, true);
  const userForm = el("user-form");
  userForm.innerHTML = `
    <div><label>Kullanici Adi</label><input data-field="username" type="text"></div>
    <div><label>Ad Soyad</label><input data-field="full_name" type="text"></div>
    <div><label>Yeni Sifre</label><input data-field="password" type="password"></div>
    <div><label>Rol</label><select data-field="role"><option>admin</option><option selected>user</option></select></div>
    <div><label>Aktif</label><select data-field="is_active"><option value="1" selected>1</option><option value="0">0</option></select></div>
  `;
  const testTypeForm = el("test-type-form");
  if (testTypeForm) {
    testTypeForm.innerHTML = `
      <div><label>Kategori</label><input data-field="category" type="text" placeholder="Biyopsi, Nekropsi, Sitoloji"></div>
      <div><label>Kod</label><input data-field="code" type="text"></div>
      <div><label>Tetkik Adi</label><input data-field="name" type="text"></div>
      <div><label>Fiyat</label><input data-field="unit_price" type="number" min="0" step="0.01"></div>
      <div><label>Aktif</label><select data-field="is_active"><option value="1" selected>1</option><option value="0">0</option></select></div>
    `;
  }
  fillCaseForm({status:"Kabul Edildi"});
  fillUserForm({});
  el("login-username").focus();

  el("login-button").addEventListener("click", async ()=>{
    el("login-error").textContent = "";
    try{
      const data = await api("/api/login", {
        method:"POST",
        body: JSON.stringify({
          username: el("login-username").value,
          password: el("login-password").value
        })
      });
      state.token = data.token;
      await bootstrap();
      switchScreen("main-screen");
    }catch(err){
      el("login-error").textContent = err.message;
    }
  });
  el("login-password").addEventListener("keydown", (event)=>{
    if(event.key === "Enter") el("login-button").click();
  });
  el("login-username").addEventListener("keydown", (event)=>{
    if(event.key === "Enter") el("login-password").focus();
  });

  document.querySelectorAll(".tab").forEach(tab=>tab.addEventListener("click", ()=>switchTab(tab.dataset.tab)));
  el("test-category-filter")?.addEventListener("change", (event)=>{
    state.selectedTestCategory = event.target.value;
    renderTestTypesTable();
  });
  el("test-type-search")?.addEventListener("input", ()=>renderTestTypesTable());

  el("search-button").addEventListener("click", async ()=>{
    const data = await api(`/api/cases?token=${encodeURIComponent(state.token)}&q=${encodeURIComponent(el("search-input").value)}&status=${encodeURIComponent(el("status-filter").value)}`);
    state.cases = data.cases;
    renderStats(data.counts);
    renderCases("cases-table", state.cases);
  });

  el("save-case-button").addEventListener("click", async ()=>{
    try{
      const data = await api("/api/cases", {method:"POST", body: JSON.stringify(getCasePayload())});
      el("case-message").textContent = "Vaka kaydedildi.";
      await bootstrap();
      fillCaseForm(data.case);
      switchTab("cases");
    }catch(err){
      el("case-message").textContent = err.message;
    }
  });

  el("new-case-button").addEventListener("click", ()=>{
    el("case-message").textContent = "";
    fillCaseForm({status:"Kabul Edildi"});
  });

  el("add-test-button").addEventListener("click", ()=>{
    const testTypeId = Number(el("test-type-select").value);
    const quantity = Math.max(1, Number(el("test-quantity").value || 1));
    const testType = state.testTypes.find(item => item.id === testTypeId);
    if(!testType) return;
    const existing = state.selectedTests.find(item => item.test_type_id === testTypeId);
    if(existing){
      existing.quantity += quantity;
      existing.total_price = existing.quantity * Number(existing.unit_price);
    } else {
      state.selectedTests.push({
        test_type_id: testType.id,
        quantity,
        unit_price: Number(testType.unit_price),
        total_price: quantity * Number(testType.unit_price),
        test_code: testType.code,
        test_name: testType.name
      });
    }
    renderSelectedTests();
  });

  el("pdf-button").addEventListener("click", async ()=>{
    triggerPdfDownload("/api/export/pdf");
  });

  el("billing-pdf-button").addEventListener("click", async ()=>{
    if(!state.selectedCaseId){
      el("case-message").textContent = "Borç detayı için önce vaka seçin.";
      return;
    }
    triggerPdfDownload("/api/export/billing");
  });

  el("request-form-pdf-button").addEventListener("click", async ()=>{
    if(!state.selectedCaseId){
      el("case-message").textContent = "Analiz talep formu için önce vaka seçin.";
      return;
    }
    triggerPdfDownload("/api/export/request-form");
  });

  el("proforma-pdf-button").addEventListener("click", async ()=>{
    if(!state.selectedCaseId){
      el("case-message").textContent = "Proforma için önce vaka seçin.";
      return;
    }
    triggerPdfDownload("/api/export/proforma");
  });

  el("import-button").addEventListener("click", async ()=>{
    try{
      const data = await api("/api/import", {method:"POST", body: JSON.stringify({token: state.token, path: el("import-path").value})});
      state.cases = data.cases;
      renderStats(data.counts);
      renderCases("cases-table", state.cases);
      renderCases("dashboard-table", state.cases.filter(x=>x.status !== "Tamamlandi"));
      el("import-result").textContent = `${data.imported} kayit aktarıldı.`;
    }catch(err){
      el("import-result").textContent = err.message;
    }
  });

  el("save-user-button").addEventListener("click", async ()=>{
    try{
      const data = await api("/api/users", {method:"POST", body: JSON.stringify(getUserPayload())});
      state.users = data.users;
      renderUsers();
      el("user-message").textContent = "Kullanici kaydedildi.";
      fillUserForm({});
    }catch(err){
      el("user-message").textContent = err.message;
    }
  });

  el("new-user-button").addEventListener("click", ()=>fillUserForm({}));

  const saveTestTypeButton = el("save-test-type-button");
  if (saveTestTypeButton) {
    saveTestTypeButton.addEventListener("click", async ()=>{
      try{
        const data = await api("/api/test-types", {method:"POST", body: JSON.stringify(getTestTypePayload())});
        state.testTypes = data.test_types;
        renderTestTypesTable();
        el("test-type-message").textContent = "Tetkik tanımı kaydedildi.";
        state.selectedTestTypeId = null;
        document.querySelectorAll("#test-type-form [data-field]").forEach(node=>{
          node.value = node.dataset.field === "is_active" ? "1" : "";
        });
      }catch(err){
        el("test-type-message").textContent = err.message;
      }
    });
  }

  const newTestTypeButton = el("new-test-type-button");
  if (newTestTypeButton) {
    newTestTypeButton.addEventListener("click", ()=>{
      state.selectedTestTypeId = null;
      document.querySelectorAll("#test-type-form [data-field]").forEach(node=>{
        node.value = node.dataset.field === "is_active" ? "1" : "";
      });
    });
  }
});
