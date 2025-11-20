const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const statusDiv = document.getElementById("uploadStatus");
const progressBar = document.getElementById("progressBar");
const eventsLog = document.getElementById("eventsLog");

uploadBtn.onclick = async () => {
  if (!fileInput.files.length) return alert("Choose a CSV file");
  const file = fileInput.files[0];

  statusDiv.innerText = "Preparing upload...";
  statusDiv.style.color = "black";
  progressBar.style.display = "block";
  progressBar.value = 0;
  
  const CHUNK_SIZE = 5 * 1024 * 1024;
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const uploadId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
  
  try {
    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      const formData = new FormData();
      formData.append('chunk', chunk);
      formData.append('chunkIndex', chunkIndex.toString());
      formData.append('totalChunks', totalChunks.toString());
      formData.append('uploadId', uploadId);
      formData.append('filename', file.name);
      
      const response = await fetch("/upload/chunk", {
        method: "POST",
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Chunk ${chunkIndex + 1} upload failed`);
      }
      
      const progress = Math.floor(((chunkIndex + 1) / totalChunks) * 100);
      progressBar.value = progress;
      statusDiv.innerText = `Uploading... ${progress}% (${chunkIndex + 1}/${totalChunks} chunks)`;
    }
    
    statusDiv.innerText = "Upload complete, processing...";
    
    const finalizeResponse = await fetch("/upload/finalize", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({uploadId: uploadId, filename: file.name})
    });
    
    if (!finalizeResponse.ok) {
      throw new Error("Failed to finalize upload");
    }
    
    const result = await finalizeResponse.json();
    
    statusDiv.innerText = "Processing started. Job ID: " + result.job_id;
    progressBar.value = 0;
    
    const es = new EventSource(`/events/import/${result.job_id}`);
    
    es.onmessage = (evt) => {
      if (!evt.data.trim()) return;
      const d = JSON.parse(evt.data);
      
      eventsLog.innerText += JSON.stringify(d) + "\n";
      
      if (d.status === "importing") {
        const pct = d.total ? Math.floor((d.processed / d.total) * 100) : 0;
        progressBar.value = pct;
        statusDiv.innerText = `Importing... ${pct}% (${d.processed}/${d.total})`;
      } 
      else if (d.status === "completed") {
        statusDiv.innerText = "Import Complete!";
        statusDiv.style.color = "green";
        progressBar.value = 100;
        es.close();
        loadProducts();
      }
      else if (d.status === "failed") {
        statusDiv.innerText = "Import Failed: " + (d.error || "");
        statusDiv.style.color = "red";
        es.close();
      }
    };
    
    es.onerror = (evt) => {
      console.error("SSE connection lost", evt);
    };
    
  } catch (err) {
    console.error(err);
    statusDiv.innerText = "Upload failed: " + err.message;
    statusDiv.style.color = "red";
    progressBar.style.display = "block";
  }
};

let currentPage = 1;
let currentLimit = 10;

async function loadProducts() {
  const sku = document.getElementById("filterSku").value;
  const name = document.getElementById("filterName").value;
  const description = document.getElementById("filterDescription").value;
  const active = document.getElementById("filterActive").value;

  const params = new URLSearchParams({
    limit: currentLimit,
    page: currentPage,
    sku, name, description
  });
  if (active) params.append("active", active);

  const res = await fetch("/products/?" + params.toString());
  const data = await res.json();
  const tbody = document.querySelector("#productsTable tbody");
  tbody.innerHTML = "";

  data.items.forEach(p => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
    <td>${p.id}</td>
    <td>${p.sku}</td>
    <td>${p.name}</td>
    <td>${p.description || ''}</td>
    <td>${p.active}</td>
    <td>
      <button class="editBtn" data-id="${p.id}">Edit</button>
      <button class="deleteBtn" data-id="${p.id}">Delete</button>
    </td>
  `;
    tbody.appendChild(tr);
  });

  document.getElementById("pageInfo").innerText = `Page ${data.page} / ${Math.ceil(data.total / currentLimit)}`;
}

document.querySelector("#productsTable tbody").addEventListener("click", async (e) => {
  const target = e.target;
  
  // Handle Edit button
  if (target.classList.contains("editBtn")) {
    const productId = parseInt(target.dataset.id);
    openModal(productId);
  }
  
  // Handle Delete button
  if (target.classList.contains("deleteBtn")) {
    const productId = parseInt(target.dataset.id);
    if (!confirm("Delete this product?")) return;
    
    try {
      await fetch(`/products/${productId}`, { method: "DELETE" });
      loadProducts();
    } catch (err) {
      console.error(err);
      alert("Failed to delete product");
    }
  }
});

document.getElementById("prevPage").onclick = () => { if(currentPage>1){currentPage--; loadProducts();} };
document.getElementById("nextPage").onclick = () => { currentPage++; loadProducts(); };
document.getElementById("refresh").onclick = () => { currentPage=1; loadProducts(); };

let editingId = null;
function openModal(id=null) {
  editingId = id;
  const modal = document.getElementById("productModal");
  modal.style.display = "block";

  document.getElementById("modalTitle").innerText = id ? "Edit Product" : "Add Product";
  if(id){
    fetch(`/products/${id}`).then(r=>r.json()).then(p=>{
      document.getElementById("modalSku").value = p.sku;
      document.getElementById("modalName").value = p.name;
      document.getElementById("modalDescription").value = p.description || "";
      document.getElementById("modalActive").checked = p.active;
    });
  } else {
    document.getElementById("modalSku").value = "";
    document.getElementById("modalName").value = "";
    document.getElementById("modalDescription").value = "";
    document.getElementById("modalActive").checked = true;
  }
}
document.getElementById("cancelModalBtn").onclick = () => {
  document.getElementById("productModal").style.display = "none";
}
document.getElementById("addProductBtn").onclick = () => openModal();

document.getElementById("saveProductBtn").onclick = async () => {
  const p = {
    sku: document.getElementById("modalSku").value,
    name: document.getElementById("modalName").value,
    description: document.getElementById("modalDescription").value,
    active: document.getElementById("modalActive").checked
  };
  try {
    let res;
    if (editingId) {
      res = await fetch(`/products/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p)
      });
    } else {
      res = await fetch("/products/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p)
      });
    }

    if (!res.ok) {
      const errData = await res.json();
      alert(errData.detail || "An error occurred");
      return; 
    }

    const data = await res.json();
    document.getElementById("productModal").style.display = "none";
    loadProducts();
  } catch (err) {
    console.error(err);
    alert("Something went wrong");
  }
}

window.edit = async (id) => {
  const r = await fetch(`/products/${id}`);
  const p = await r.json();
  const name = prompt("Name", p.name);
  if (name == null) return;
  p.name = name;
  await fetch(`/products/${id}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body: JSON.stringify(p)});
  loadProducts();
};

window.deleteProduct = async (id) => {
  if (!confirm("Delete?")) return;
  await fetch(`/products/${id}`, {method:"DELETE"});
  loadProducts();
};

async function deleteAllProducts() {
  const confirmDelete = confirm("Are you sure? This cannot be undone.");
  if (!confirmDelete) return;

  const btn = document.getElementById("deleteAllBtn");
  btn.disabled = true;
  btn.textContent = "Deleting...";

  try {
    const res = await fetch("/products/?confirm=true", { method: "DELETE" });

    if (!res.ok) {
      let errorText = "";
      try {
        const errorData = await res.json();
        errorText = errorData.detail || JSON.stringify(errorData);
      } catch (e) {
        errorText = await res.text();
      }
      alert(`Failed to delete products! ${errorText}`);
      return;
    }

    const data = await res.json();
    alert(`Deleted ${data.deleted} products successfully!`);

    document.getElementById("productsTableBody").innerHTML = "";
  } catch (err) {
    console.error(err);
    alert("Failed to delete products! See console for details.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Delete All Products";
  }
}

async function loadWebhooks() {
  const res = await fetch("/webhooks/");
  const data = await res.json();
  const tbody = document.getElementById("webhookTableBody");
  tbody.innerHTML = "";
  data.forEach(w => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${w.id}</td>
      <td>${w.url}</td>
      <td>${w.event_type}</td>
      <td>${w.enabled ? "Yes" : "No"}</td>
      <td>
        <button onclick="editWebhook(${w.id})">Edit</button>
        <button onclick="deleteWebhook(${w.id})">Delete</button>
        <button onclick="testWebhook(${w.id})">Test</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

document.getElementById("webhookForm").onsubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById("webhookId").value;
  const payload = {
    url: document.getElementById("webhookUrl").value,
    event_type: document.getElementById("webhookEvent").value,
    enabled: document.getElementById("webhookEnabled").checked
  };
  const method = id ? "PUT" : "POST";
  const url = id ? `/webhooks/${id}` : "/webhooks/";

  const res = await fetch(url, { method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload) });
  const data = await res.json();
  alert(id ? "Webhook updated!" : "Webhook added!");
  document.getElementById("webhookForm").reset();
  document.getElementById("webhookId").value = "";
  loadWebhooks();
};

async function editWebhook(id) {
  const res = await fetch(`/webhooks/`);
  const data = await res.json();
  const webhook = data.find(w => w.id === id);
  if (!webhook) return alert("Webhook not found");
  document.getElementById("webhookId").value = webhook.id;
  document.getElementById("webhookUrl").value = webhook.url;
  document.getElementById("webhookEvent").value = webhook.event_type;
  document.getElementById("webhookEnabled").checked = webhook.enabled;
}

async function deleteWebhook(id) {
  if (!confirm("Delete this webhook?")) return;
  await fetch(`/webhooks/${id}`, { method: "DELETE" });
  alert("Webhook deleted!");
  loadWebhooks();
}

async function testWebhook(id) {
  const res = await fetch(`/webhooks/${id}/test`, { method: "POST" });
  const data = await res.json();
  alert(`Status: ${data.status_code}\nResponse: ${data.response}`);
}

loadWebhooks();
