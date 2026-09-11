(() => {
  const MASTER_KEY = "jobScraper.privateMaster.v1";
  const CONFIRMED_KEY = "jobScraper.userConfirmedSkills.v1";
  const TOP_JD_SKILLS = 10;

  const clean = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const key = (v) => clean(v).toLowerCase();
  const unique = (values) => {
    const seen = new Set();
    const out = [];
    for (const value of values || []) {
      const text = clean(value);
      const k = key(text);
      if (!text || seen.has(k)) continue;
      seen.add(k);
      out.push(text);
    }
    return out;
  };

  function evidenceSkills(master) {
    const skills = [...(master.base_skills || [])];
    for (const entry of [...(master.experience || []), ...(master.projects || [])]) {
      for (const bullet of entry.bullets || []) {
        if (bullet.verified === true) skills.push(...(bullet.skills || []));
      }
    }
    return new Set(unique(skills).map(key));
  }

  function readJsonStorage(storageKey, fallback) {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function hideOldGapLanguage() {
    const preview = document.getElementById("preview");
    if (!preview) return;
    for (const p of preview.querySelectorAll("p")) {
      if (clean(p.textContent).toLowerCase().startsWith("jd gaps not claimed:")) {
        p.style.display = "none";
      }
    }
  }

  function removePanel() {
    document.getElementById("jdSkillConfirmPanel")?.remove();
  }

  async function buildPanel() {
    hideOldGapLanguage();
    removePanel();

    const master = readJsonStorage(MASTER_KEY, null);
    const resultCard = document.getElementById("resultCard");
    if (!master || !resultCard || resultCard.classList.contains("hidden")) return;

    const jid = new URLSearchParams(location.search).get("job");
    if (!jid) return;

    let job;
    try {
      const response = await fetch("./job_signals.json", { cache: "no-store" });
      if (!response.ok) return;
      const feed = await response.json();
      job = feed?.jobs?.[jid];
    } catch {
      return;
    }
    if (!job) return;

    const topJd = unique(job.top_jd_skills || job.detected_skills || []).slice(0, TOP_JD_SKILLS);
    const evidence = evidenceSkills(master);
    const missing = topJd.filter((skill) => !evidence.has(key(skill)));
    if (!missing.length) return;

    const panel = document.createElement("section");
    panel.id = "jdSkillConfirmPanel";
    panel.setAttribute("aria-label", "Confirm JD skills you already know");
    panel.style.margin = "18px 0";
    panel.style.padding = "16px";
    panel.style.border = "1px solid rgba(148,163,184,.35)";
    panel.style.borderRadius = "12px";
    panel.style.background = "rgba(15,23,42,.35)";

    const title = document.createElement("h3");
    title.textContent = "Confirm Top JD skills already in your real skill set (Top 10)";
    title.style.margin = "0 0 6px";
    panel.appendChild(title);

    const note = document.createElement("p");
    note.className = "tiny muted";
    note.textContent = "Skills captured directly from the JD are used first. If the captured posting exposes fewer than 10 named skills, closely related skills for that role fill the remaining slots. Check only skills you genuinely know. Confirmed skills are saved in this browser and added to Technical Skills. Experience bullets are only prioritized when your existing verified experience supports the skill; the portal does not invent experience.";
    panel.appendChild(note);

    const options = document.createElement("div");
    options.style.display = "flex";
    options.style.flexWrap = "wrap";
    options.style.gap = "10px";
    options.style.margin = "12px 0";

    for (const skill of missing) {
      const label = document.createElement("label");
      label.style.display = "inline-flex";
      label.style.alignItems = "center";
      label.style.gap = "6px";
      label.style.padding = "8px 10px";
      label.style.border = "1px solid rgba(148,163,184,.35)";
      label.style.borderRadius = "999px";
      label.style.cursor = "pointer";

      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = skill;
      input.name = "confirmJdSkill";
      label.appendChild(input);
      label.appendChild(document.createTextNode(skill));
      options.appendChild(label);
    }
    panel.appendChild(options);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = "Confirm selected skills & rebuild resume";
    button.addEventListener("click", () => {
      const selected = [...panel.querySelectorAll('input[name="confirmJdSkill"]:checked')]
        .map((input) => clean(input.value))
        .filter(Boolean);
      if (!selected.length) return;

      const latestMaster = readJsonStorage(MASTER_KEY, master);
      latestMaster.base_skills = unique([...(latestMaster.base_skills || []), ...selected]);

      const history = readJsonStorage(CONFIRMED_KEY, []);
      const now = new Date().toISOString();
      const existing = new Map((Array.isArray(history) ? history : []).map((item) => [key(item.skill), item]));
      for (const skill of selected) {
        existing.set(key(skill), { skill, confirmed_at: now, source: "user-confirmed-from-job-description" });
      }
      latestMaster.user_confirmed_skills = unique([
        ...(latestMaster.user_confirmed_skills || []),
        ...selected,
      ]);

      localStorage.setItem(MASTER_KEY, JSON.stringify(latestMaster));
      localStorage.setItem(CONFIRMED_KEY, JSON.stringify([...existing.values()]));
      location.reload();
    });
    panel.appendChild(button);

    const metricGrid = resultCard.querySelector(".metricGrid");
    if (metricGrid?.nextSibling) resultCard.insertBefore(panel, metricGrid.nextSibling);
    else resultCard.appendChild(panel);
  }

  let timer = null;
  const schedule = () => {
    clearTimeout(timer);
    timer = setTimeout(buildPanel, 120);
  };

  const resultCard = document.getElementById("resultCard");
  if (resultCard) {
    const observer = new MutationObserver((mutations) => {
      if (mutations.some((mutation) => mutation.type === "attributes" && mutation.attributeName === "class")) {
        schedule();
      }
    });
    observer.observe(resultCard, { attributes: true, attributeFilter: ["class"] });
  }

  window.addEventListener("load", schedule);
  schedule();
})();
