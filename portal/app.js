import {
  AlignmentType,
  BorderStyle,
  Document,
  Packer,
  Paragraph,
  TextRun,
} from "docx";

const MASTER_KEY = "jobScraper.privateMaster.v1";
const MAX_SKILLS = 15;

const ROLE_CORE_SKILLS = {
  "data-engineering": [
    "Python", "SQL", "PostgreSQL", "Apache Spark", "Kafka", "Apache Airflow",
    "dbt", "AWS", "Redshift", "BigQuery", "Terraform", "Docker",
    "REST APIs", "JSON", "Pandas"
  ],
  "software-engineering": [
    "Python", "JavaScript", "SQL", "PostgreSQL", "REST APIs", "GitHub Actions",
    "Docker", "AWS", "Microsoft Azure", "Supabase", "JSON", "Kubernetes",
    "Terraform", "HTML5", "CSS"
  ],
  "cloud-devops": [
    "Microsoft Azure", "AWS", "Terraform", "Docker", "Kubernetes", "PowerShell",
    "Bash", "GitHub Actions", "PostgreSQL", "REST APIs", "JSON", "Kafka",
    "Helm", "Python", "SQL"
  ],
  "machine-learning": [
    "Python", "Machine Learning", "Pandas", "NumPy", "Apache Spark", "SQL",
    "AWS", "Microsoft Azure", "Docker", "Kafka", "Streamlit", "BigQuery",
    "PostgreSQL", "REST APIs", "JSON"
  ],
  "data-analytics": [
    "SQL", "Excel", "BigQuery", "PostgreSQL", "Python", "Pandas", "NumPy",
    "Supabase", "Apache Spark", "dbt", "Streamlit", "Machine Learning",
    "REST APIs", "JSON", "JavaScript"
  ],
  "general-technical": [
    "Python", "SQL", "PostgreSQL", "AWS", "Microsoft Azure", "Docker",
    "GitHub Actions", "REST APIs", "JSON", "Excel", "Pandas", "NumPy",
    "Terraform", "JavaScript", "Apache Spark"
  ]
};

const EXPERIENCE_LIMITS = {
  "data-engineering": {
    "aramark-data-ops": 5,
    "ltimindtree-cloud": 5,
    "infra-developers-web": 1,
  },
  "software-engineering": {
    "aramark-data-ops": 5,
    "ltimindtree-cloud": 4,
    "infra-developers-web": 2,
  },
  "cloud-devops": {
    "aramark-data-ops": 3,
    "ltimindtree-cloud": 6,
    "infra-developers-web": 1,
  },
  "machine-learning": {
    "aramark-data-ops": 4,
    "ltimindtree-cloud": 4,
    "infra-developers-web": 1,
  },
  "data-analytics": {
    "aramark-data-ops": 5,
    "ltimindtree-cloud": 3,
    "infra-developers-web": 1,
  },
  "general-technical": {
    "aramark-data-ops": 4,
    "ltimindtree-cloud": 4,
    "infra-developers-web": 1,
  }
};

let currentJob = null;
let currentMaster = null;
let currentCandidate = null;

const $ = (id) => document.getElementById(id);
const clean = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const key = (v) => clean(v).toLowerCase();

function escapeHtml(value) {
  return clean(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[ch]));
}

function unique(values) {
  const seen = new Set();
  const out = [];
  for (const value of values || []) {
    const cleaned = clean(value);
    const k = key(cleaned);
    if (!cleaned || seen.has(k)) continue;
    seen.add(k);
    out.push(cleaned);
  }
  return out;
}

function profileLabel(profile) {
  return ({
    "data-engineering": "Data Engineering",
    "software-engineering": "Software Engineering",
    "cloud-devops": "Cloud / DevOps",
    "machine-learning": "ML / Data Science",
    "data-analytics": "Data Analytics",
    "general-technical": "Technical"
  })[profile] || "Technical";
}

function profileSummary(profile) {
  const summaries = {
    "data-engineering": "Data and cloud engineer with professional Azure experience and hands-on ETL/ELT, streaming, data warehouse, SQL, Python, and cloud data-platform projects. Currently completing an M.S. in Data Science, Analytics & Engineering at Arizona State University.",
    "software-engineering": "Software and data engineer with full-stack JavaScript/PostgreSQL experience, production Azure cloud engineering background, and hands-on API, automation, and cloud projects. Currently completing an M.S. in Data Science, Analytics & Engineering at Arizona State University.",
    "cloud-devops": "Cloud and data engineer with professional Azure infrastructure experience and hands-on Terraform, Kubernetes, Docker, CI/CD, monitoring, incident-response, and AWS projects. Currently completing an M.S. in Data Science, Analytics & Engineering at Arizona State University.",
    "machine-learning": "M.S. Data Science candidate with Python and machine-learning experience, cloud engineering background, and hands-on data pipelines, model-oriented analytics, and scalable infrastructure projects.",
    "data-analytics": "Data and operations analyst with SQL, Excel, BigQuery, PostgreSQL, reconciliation, data-quality, and reporting experience, backed by professional Azure cloud engineering experience and an M.S. in Data Science in progress.",
    "general-technical": "M.S. Data Science candidate with professional Azure cloud engineering experience and hands-on software, data, automation, and cloud projects."
  };
  return summaries[profile] || summaries["general-technical"];
}

function buildSummary(profile, jdSkills, allSkills) {
  const base = profileSummary(profile);
  const strongest = unique(jdSkills).slice(0, 5);
  if (strongest.length >= 2) {
    return `${base} Key strengths aligned to this role include ${strongest.join(", ")}.`;
  }
  const core = unique(allSkills).slice(0, 5);
  return core.length
    ? `${base} Core technical strengths include ${core.join(", ")}.`
    : base;
}

function profileBoost(profile, projectId) {
  const map = {
    "data-engineering": ["fraud-pipeline-aws", "job-market-pipeline", "graph-analytics-pipeline"],
    "software-engineering": ["job-market-pipeline", "graph-analytics-pipeline", "fraud-pipeline-aws"],
    "cloud-devops": ["graph-analytics-pipeline", "fraud-pipeline-aws", "job-market-pipeline"],
    "machine-learning": ["resume-job-matching", "fraud-pipeline-aws", "graph-analytics-pipeline"],
    "data-analytics": ["fraud-pipeline-aws", "resume-job-matching", "job-market-pipeline"]
  };
  const ids = map[profile] || [];
  const pos = ids.indexOf(projectId);
  return pos < 0 ? 0 : (6 - pos * 2);
}

function skillSet(values) {
  return new Set((values || []).map(key).filter(Boolean));
}

function masterBaseMap(master) {
  return new Map((master.base_skills || []).map((s) => [key(s), clean(s)]));
}

function masterEvidenceSkills(master) {
  const evidence = [...(master.base_skills || [])];
  for (const entry of [...(master.experience || []), ...(master.projects || [])]) {
    for (const bullet of entry.bullets || []) {
      if (bullet.verified === true) evidence.push(...(bullet.skills || []));
    }
  }
  return new Map(unique(evidence).map((s) => [key(s), s]));
}

function selectSkills(master, job, profile) {
  const base = masterBaseMap(master);
  const evidence = masterEvidenceSkills(master);
  const publicVerified = unique(job.verified_skills || []);
  const detected = unique(job.detected_skills || []);

  const jdSkills = [];
  for (const skill of (publicVerified.length ? publicVerified : detected)) {
    const direct = evidence.get(key(skill)) || base.get(key(skill));
    if (direct) {
      jdSkills.push(direct);
    } else if (publicVerified.some((s) => key(s) === key(skill))) {
      jdSkills.push(clean(skill));
    }
  }

  const roleCore = [];
  for (const desired of ROLE_CORE_SKILLS[profile] || ROLE_CORE_SKILLS["general-technical"]) {
    const hit = evidence.get(key(desired)) || base.get(key(desired));
    if (hit) roleCore.push(hit);
  }

  const all = unique([...jdSkills, ...roleCore]).slice(0, MAX_SKILLS);
  const selectedSet = skillSet(all);
  const selectedJd = unique(jdSkills).filter((s) => selectedSet.has(key(s)));
  const jdSet = skillSet(selectedJd);
  const addedCore = all.filter((s) => !jdSet.has(key(s)));

  return { all, jd: selectedJd, core: addedCore };
}

function scoringSkills(job) {
  return job.effective_skills || job.verified_skills || job.detected_skills || [];
}

function scoreBullet(bullet, job, profile, projectId = "") {
  if (!bullet || bullet.verified !== true) return -9999;
  const effective = skillSet(scoringSkills(job));
  const directJd = skillSet(job.verified_skills || job.detected_skills);
  let score = 0;

  for (const skill of bullet.skills || []) {
    const k = key(skill);
    if (directJd.has(k)) score += 14;
    else if (effective.has(k)) score += 7;
  }

  const body = key(`${bullet.text || ""} ${(bullet.keywords || []).join(" ")}`);
  for (const term of job.signal_terms || []) {
    if (body.includes(key(term))) score += 4;
  }

  const titleWords = key(job.title).split(/\s+/).filter((x) => x.length >= 4);
  for (const word of titleWords) {
    if (body.includes(word)) score += 1;
  }

  if (projectId) score += profileBoost(profile, projectId);
  return score;
}

function selectBullets(entry, job, profile, maxBullets, projectId = "") {
  const verified = (entry.bullets || [])
    .filter((b) => b.verified === true)
    .map((b, index) => ({ ...b, _score: scoreBullet(b, job, profile, projectId), _index: index }))
    .sort((a, b) => b._score - a._score || a._index - b._index);

  if (!verified.length) return [];
  const positive = verified.filter((b) => b._score > 0);
  return (positive.length ? positive : verified.slice(0, 1)).slice(0, maxBullets);
}

function experienceLimit(profile, entryId) {
  return EXPERIENCE_LIMITS[profile]?.[entryId]
    ?? EXPERIENCE_LIMITS["general-technical"]?.[entryId]
    ?? 3;
}

function selectedEntryMatches(entry, job) {
  const jd = skillSet(job.verified_skills || job.detected_skills);
  const matched = [];
  for (const bullet of entry.selectedBullets || []) {
    for (const skill of bullet.skills || []) {
      if (jd.has(key(skill))) matched.push(skill);
    }
    const body = key(`${bullet.text || ""} ${(bullet.keywords || []).join(" ")}`);
    for (const term of job.signal_terms || []) {
      if (body.includes(key(term))) matched.push(term);
    }
  }
  return unique(matched).slice(0, 7);
}

function selectProjects(master, job, profile) {
  const projects = (master.projects || []).map((project) => {
    const bullets = selectBullets(project, job, profile, 2, project.id);
    const score = bullets.reduce((sum, b) => sum + Math.max(0, b._score), 0) + profileBoost(profile, project.id);
    return {
      ...project,
      selectedBullets: bullets,
      _score: score,
      matchedSignals: selectedEntryMatches({ selectedBullets: bullets }, job),
    };
  });
  projects.sort((a, b) => b._score - a._score);
  return projects.filter((p) => p.selectedBullets.length && p._score > 0).slice(0, 2);
}

function validateMaster(master) {
  if (!master || typeof master !== "object") throw new Error("The selected JSON is not a resume master object.");
  if (!clean(master?.contact?.name)) throw new Error("master.contact.name is required.");
  if (!Array.isArray(master.experience) || !master.experience.length) throw new Error("master.experience is required.");
  for (const item of [...(master.experience || []), ...(master.projects || []), ...(master.education || [])]) {
    if (item.locked !== true) throw new Error("Every experience, project, and education entry must have locked=true.");
  }
}

function buildCandidate(master, job) {
  validateMaster(master);
  const profile = job.profile || "general-technical";
  const skillBundle = selectSkills(master, job, profile);
  const scoringJob = { ...job, effective_skills: skillBundle.all };

  const experience = (master.experience || []).map((entry) => {
    const selectedBullets = selectBullets(
      entry,
      scoringJob,
      profile,
      experienceLimit(profile, entry.id)
    );
    return {
      ...entry,
      selectedBullets,
      matchedSignals: selectedEntryMatches({ selectedBullets }, job),
    };
  });

  const projects = selectProjects(master, scoringJob, profile);
  return {
    contact: master.contact,
    summary: buildSummary(profile, skillBundle.jd, skillBundle.all),
    skills: skillBundle.all,
    jdSkills: skillBundle.jd,
    coreSkills: skillBundle.core,
    experience,
    projects,
    education: master.education || [],
    certifications: master.certifications || [],
    profile,
  };
}

function renderJob(job) {
  $("jobTitle").textContent = job.title || "Job";
  $("jobMeta").textContent = [job.company, job.location, job.posted].filter(Boolean).join(" • ");
  $("profileBadge").textContent = profileLabel(job.profile);
  $("skills").innerHTML = (job.detected_skills || []).length
    ? job.detected_skills.map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")
    : '<span class="chip">Title/profile signals only</span>';
  $("signalNote").textContent = job.signal_source === "job-page"
    ? "Skills were derived from the public job page; the full job description is not republished here."
    : "The job page did not expose enough readable text, so this resume uses title/profile signals plus verified core skills for the role. Review the preview before applying.";
}

function renderCandidate(candidate) {
  const expBulletCount = candidate.experience.reduce((n, e) => n + e.selectedBullets.length, 0);
  $("jdSkillCount").textContent = String(candidate.jdSkills.length);
  $("skillCount").textContent = String(candidate.skills.length);
  $("bulletCount").textContent = String(expBulletCount);
  $("fitTitle").textContent = `${profileLabel(candidate.profile)} resume ready`;

  const parts = [];
  parts.push(`<h3>SUMMARY</h3><p>${escapeHtml(candidate.summary)}</p>`);
  parts.push(`<h3>ATS SKILLS</h3><p>${escapeHtml(candidate.skills.join(" • ") || "No verified skills available")}</p>`);
  if (candidate.jdSkills.length) {
    parts.push(`<p class="tiny muted"><strong>Direct JD matches:</strong> ${escapeHtml(candidate.jdSkills.join(" • "))}</p>`);
  }
  if (candidate.coreSkills.length) {
    parts.push(`<p class="tiny muted"><strong>Verified role-core skills added:</strong> ${escapeHtml(candidate.coreSkills.join(" • "))}</p>`);
  }

  parts.push("<h3>EXPERIENCE</h3>");
  for (const exp of candidate.experience) {
    parts.push(`<h4>${escapeHtml(exp.title)} — ${escapeHtml(exp.company)}</h4>`);
    parts.push(`<p class="muted">${escapeHtml([exp.location, exp.start && exp.end ? `${exp.start} – ${exp.end}` : ""].filter(Boolean).join(" • "))}</p>`);
    if (exp.matchedSignals.length) {
      parts.push(`<p class="tiny muted"><strong>JD alignment:</strong> ${escapeHtml(exp.matchedSignals.join(" • "))}</p>`);
    }
    parts.push(`<ul>${exp.selectedBullets.map((b) => `<li>${escapeHtml(b.text)}</li>`).join("")}</ul>`);
  }

  if (candidate.projects.length) {
    parts.push(`<h3>PROJECTS <span class="tiny muted">(${candidate.projects.length} selected)</span></h3>`);
    for (const project of candidate.projects) {
      parts.push(`<h4>${escapeHtml(project.name)}</h4>`);
      if (project.matchedSignals.length) {
        parts.push(`<p class="tiny muted"><strong>JD alignment:</strong> ${escapeHtml(project.matchedSignals.join(" • "))}</p>`);
      }
      parts.push(`<ul>${project.selectedBullets.map((b) => `<li>${escapeHtml(b.text)}</li>`).join("")}</ul>`);
    }
  }
  $("preview").innerHTML = parts.join("");
  $("resultCard").classList.remove("hidden");
}

function textParagraph(text, options = {}) {
  return new Paragraph({
    spacing: { after: options.after ?? 70, line: 235 },
    alignment: options.center ? AlignmentType.CENTER : undefined,
    children: [new TextRun({
      text: clean(text),
      bold: !!options.bold,
      size: options.size || 20,
      font: "Arial",
    })],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    spacing: { before: 125, after: 45 },
    border: { bottom: { color: "AAB2C0", size: 6, style: BorderStyle.SINGLE } },
    children: [new TextRun({ text, bold: true, size: 20, font: "Arial" })],
  });
}

function bulletParagraph(text) {
  return new Paragraph({
    bullet: { level: 0 },
    spacing: { after: 35, line: 220 },
    children: [new TextRun({ text: clean(text), size: 19, font: "Arial" })],
  });
}

function roleParagraph(entry) {
  const left = [entry.title, entry.company].filter(Boolean).join(" — ");
  const right = [entry.location, entry.start && entry.end ? `${entry.start} – ${entry.end}` : ""].filter(Boolean).join(" | ");
  return new Paragraph({
    spacing: { before: 65, after: 28 },
    children: [
      new TextRun({ text: left, bold: true, size: 20, font: "Arial" }),
      new TextRun({ text: right ? `  |  ${right}` : "", size: 18, font: "Arial" }),
    ],
  });
}

function safeFilename(job) {
  const raw = `${job.company || "company"}-${job.title || "role"}`.toLowerCase();
  return raw.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 90) || "tailored-resume";
}

async function candidateBlob(candidate) {
  const children = [];
  children.push(textParagraph(candidate.contact.name, { bold: true, size: 30, center: true, after: 40 }));
  const contactLine = [
    candidate.contact.location,
    candidate.contact.email,
    candidate.contact.phone,
    ...(candidate.contact.links || []),
  ].filter(Boolean).join(" | ");
  children.push(textParagraph(contactLine, { center: true, size: 17, after: 85 }));

  children.push(sectionHeading("SUMMARY"));
  children.push(textParagraph(candidate.summary, { after: 55 }));

  if (candidate.skills.length) {
    children.push(sectionHeading("TECHNICAL SKILLS"));
    children.push(textParagraph(candidate.skills.join(" • "), { after: 55 }));
  }

  children.push(sectionHeading("EXPERIENCE"));
  for (const exp of candidate.experience) {
    children.push(roleParagraph(exp));
    for (const bullet of exp.selectedBullets) children.push(bulletParagraph(bullet.text));
  }

  if (candidate.projects.length) {
    children.push(sectionHeading("PROJECTS"));
    for (const project of candidate.projects) {
      children.push(roleParagraph({
        title: project.name,
        company: project.subtitle || "",
        location: "",
        start: "",
        end: "",
      }));
      for (const bullet of project.selectedBullets) children.push(bulletParagraph(bullet.text));
    }
  }

  if (candidate.education.length) {
    children.push(sectionHeading("EDUCATION"));
    for (const edu of candidate.education) {
      children.push(roleParagraph({
        title: edu.degree,
        company: edu.school,
        location: edu.location,
        start: edu.start,
        end: edu.end,
      }));
      for (const detail of edu.details || []) children.push(textParagraph(detail, { size: 18, after: 25 }));
    }
  }

  if (candidate.certifications.length) {
    children.push(sectionHeading("CERTIFICATIONS"));
    children.push(textParagraph(candidate.certifications.join(" • "), { size: 18 }));
  }

  const doc = new Document({
    creator: "",
    lastModifiedBy: "",
    title: "",
    subject: "",
    description: "",
    keywords: "",
    sections: [{
      properties: {
        page: {
          margin: { top: 620, right: 620, bottom: 620, left: 620 },
        },
      },
      children,
    }],
  });
  return Packer.toBlob(doc);
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2500);
}

async function downloadResume() {
  if (!currentCandidate || !currentJob) throw new Error("Resume is not ready.");
  const blob = await candidateBlob(currentCandidate);
  triggerDownload(blob, `${safeFilename(currentJob)}-resume.docx`);
}

function showError(message) {
  $("errorText").textContent = clean(message);
  $("errorCard").classList.remove("hidden");
}

function setMaster(master) {
  validateMaster(master);
  currentMaster = master;
  localStorage.setItem(MASTER_KEY, JSON.stringify(master));
  $("masterMissing").classList.add("hidden");
  $("masterReady").classList.remove("hidden");
  $("masterName").textContent = `${master.contact.name} master resume loaded`;
  maybeBuild();
}

function maybeBuild() {
  if (!currentJob || !currentMaster) return;
  currentCandidate = buildCandidate(currentMaster, currentJob);
  renderCandidate(currentCandidate);
}

async function loadJob() {
  const jid = new URLSearchParams(location.search).get("job");
  if (!jid) throw new Error("This link does not contain a job id.");
  const response = await fetch("./job_signals.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load the current job feed.");
  const feed = await response.json();
  const job = feed?.jobs?.[jid];
  if (!job) throw new Error("This job is no longer in the current portal feed.");
  currentJob = job;
  renderJob(job);
  maybeBuild();
}

$("masterFile").addEventListener("change", async (event) => {
  try {
    const file = event.target.files?.[0];
    if (!file) return;
    const master = JSON.parse(await file.text());
    setMaster(master);
  } catch (err) {
    showError(`Master resume import failed: ${err.message}`);
  }
});

$("clearMaster").addEventListener("click", () => {
  localStorage.removeItem(MASTER_KEY);
  currentMaster = null;
  currentCandidate = null;
  $("masterReady").classList.add("hidden");
  $("masterMissing").classList.remove("hidden");
  $("resultCard").classList.add("hidden");
});

$("downloadOnly").addEventListener("click", async () => {
  try { await downloadResume(); } catch (err) { showError(err.message); }
});

$("openApply").addEventListener("click", () => {
  if (currentJob?.apply_url) window.open(currentJob.apply_url, "_blank", "noopener,noreferrer");
});

$("downloadApply").addEventListener("click", async () => {
  try {
    const applyWindow = currentJob?.apply_url ? window.open("about:blank", "_blank") : null;
    await downloadResume();
    if (applyWindow && currentJob?.apply_url) {
      applyWindow.opener = null;
      applyWindow.location = currentJob.apply_url;
    }
  } catch (err) {
    showError(err.message);
  }
});

try {
  const saved = localStorage.getItem(MASTER_KEY);
  if (saved) setMaster(JSON.parse(saved));
} catch {
  localStorage.removeItem(MASTER_KEY);
}

loadJob().catch((err) => showError(err.message));
