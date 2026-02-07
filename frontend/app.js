async function upload() {
  let file = document.getElementById("file").files[0];
  if (!file) return alert("Escolha um arquivo");

  let form = new FormData();
  form.append("file", file);

  let res = await fetch("http://127.0.0.1:8000/upload-planilha", {
    method: "POST",
    body: form
  });

  let data = await res.json();
  document.getElementById("status").innerText = JSON.stringify(data, null, 2);
}

async function loadJobs() {
  let res = await fetch("http://127.0.0.1:8000/jobs");
  let data = await res.json();

  let div = document.getElementById("jobs");

  div.innerHTML = data.map(j => `
    <div class="job">
      <b>${j.job_id}</b> — ${j.status}
      <button onclick="viewJob('${j.job_id}')">Ver Resultado</button>
    </div>
  `).join("");
}

async function viewJob(id) {
  let res = await fetch(`http://127.0.0.1:8000/jobs/${id}`);
  let data = await res.json();
  alert(JSON.stringify(data, null, 2));
}

async function loadLogs() {
  let res = await fetch("http://127.0.0.1:8000/logs");
  let data = await res.text();
  document.getElementById("logs").innerText = data;
}
