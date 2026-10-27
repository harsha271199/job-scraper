import {
  AlignmentType,
  BorderStyle,
  Document,
  Packer,
  Paragraph,
  TextRun,
} from "docx";
import { jsPDF } from "jspdf";

const MASTER_KEY = "jobScraper.privateMaster.v1";
const TOP_JD_SKILLS = 10;
const MAX_RELATED_SKILLS = 9;
const MAX_SKILLS = TOP_JD_SKILLS + MAX_RELATED_SKILLS;
const MAX_PROJECTS = 3;

const ROLE_CORE_SKILLS = {
  "data-engineering": [
    "Python", "SQL", "PostgreSQL", "BigQuery", "Apache Spark", "Kafka",
    "Apache Airflow", "dbt", "AWS", "Microsoft Azure", "Redshift",
    "Data Validation", "Data Reconciliation", "Terraform", "Docker"
  ],
  "software-engineering": [
    "JavaScript", "Python", "SQL", "PostgreSQL", "Supabase", "REST APIs",
    "GitHub Actions", "Docker", "Microsoft Azure", "AWS", "HTML5", "CSS",
    "WordPress", "Terraform", "Kubernetes"
  ],
  "cloud-devops": [
    "Microsoft Azure", "Terraform", "Docker", "Kubernetes", "PowerShell",
    "Azure CLI", "Azure Monitor", "Log Analytics", "GitHub Actions", "Linux",
    "Bash", "AWS", "Python", "Networking", "Security"
  ],
  "machine-learning": [
    "Python", "PyTorch", "Machine Learning", "Pandas", "NumPy", "NLP",
    "LLM Fine-Tuning", "Apache Spark", "Kafka", "AWS", "Microsoft Azure",
    "Docker", "HPC", "SQL", "Data Validation"
  ],
  "data-analytics": [
    "SQL", "Excel", "BigQuery", "PostgreSQL", "Data Validation",
    "Data Reconciliation", "Sales Analysis", "KPI Reporting", "Operational Analytics",
    "Variance Analysis", "Python", "Pandas", "NumPy", "Supabase",
    "Azure Monitor", "Log Analytics", "Microsoft Azure", "Streamlit", "dbt"
  ],
  "general-technical": [
    "Python", "SQL", "JavaScript", "PostgreSQL", "Microsoft Azure", "AWS",
    "Docker", "GitHub Actions", "REST APIs", "Excel", "Terraform",
    "Data Validation", "PowerShell", "Linux", "Pandas"
  ]
};

const PROFILE_DESCRIPTORS = {
  "data-engineering": "Data Platforms, ETL/ELT & Cloud",
  "software-engineering": "Backend, Full-Stack & Cloud",
  "cloud-devops": "Azure Infrastructure, Automation & Reliability",
  "machine-learning": "Applied ML, Data Pipelines & Cloud",
  "data-analytics": "Sales, KPI Reporting & Operational Analytics",
  "general-technical": "Technical Engineering"
};

const DEFAULT_FOCUS = {
  "aramark-data-ops": {
    "data-engineering": "Data Engineering & Operational Platforms",
    "software-engineering": "Software & Data Platform Development",
    "cloud-devops": "Platform Operations & Automation",
    "machine-learning": "Data & ML Analytics",
    "data-analytics": "Sales, Operations & Data Analytics",
    "general-technical": "Data Platforms & Operations"
  },
  "ltimindtree-cloud": {
    "data-engineering": "Data Engineering & Platform Automation",
    "software-engineering": "Platform & Infrastructure Engineering",
    "cloud-devops": "Azure Infrastructure & DevOps",
    "machine-learning": "Data & ML Infrastructure",
    "data-analytics": "Cloud Operations & Data Analytics",
    "general-technical": "Azure Infrastructure & Automation"
  },
  "infra-developers-web": {
    "data-engineering": "Web Data Capture & Lead Workflows",
    "software-engineering": "Full-Stack Web Development",
    "cloud-devops": "Web Deployment & Operations",
    "machine-learning": "Web Data Capture & Analytics",
    "data-analytics": "Lead Analytics & Web Measurement",
    "general-technical": "Full-Stack Web Development"
  }
};

const EXPERIENCE_LIMITS = {
  "data-engineering": {"aramark-data-ops": 4, "ltimindtree-cloud": 4, "infra-developers-web": 1},
  "software-engineering": {"aramark-data-ops": 4, "ltimindtree-cloud": 4, "infra-developers-web": 2},
  "cloud-devops": {"aramark-data-ops": 3, "ltimindtree-cloud": 5, "infra-developers-web": 1},
  "machine-learning": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1},
  "data-analytics": {"aramark-data-ops": 5, "ltimindtree-cloud": 3, "infra-developers-web": 1},
  "general-technical": {"aramark-data-ops": 4, "ltimindtree-cloud": 4, "infra-developers-web": 1}
};

const EXPERIENCE_MINIMUMS = {
  "data-engineering": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1},
  "software-engineering": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1},
  "cloud-devops": {"aramark-data-ops": 2, "ltimindtree-cloud": 4, "infra-developers-web": 1},
  "machine-learning": {"aramark-data-ops": 2, "ltimindtree-cloud": 2, "infra-developers-web": 1},
  "data-analytics": {"aramark-data-ops": 4, "ltimindtree-cloud": 2, "infra-developers-web": 1},
  "general-technical": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1}
};

const PROFILE_BULLET_TERMS = {
  "data-engineering": [
    "etl", "elt", "data pipeline", "data pipelines", "sql", "postgresql", "bigquery",
    "redshift", "spark", "kafka", "airflow", "dbt", "data model", "schema",
    "data quality", "validation", "reconciliation", "warehouse", "streaming"
  ],
  "software-engineering": [
    "javascript", "python", "api", "rest", "backend", "full-stack", "postgresql",
    "supabase", "application", "testing", "debugging", "scalability", "concurrent",
    "automation", "git", "docker", "kubernetes", "system design"
  ],
  "cloud-devops": [
    "azure", "terraform", "arm", "infrastructure as code", "powershell", "azure cli",
    "docker", "kubernetes", "vm", "vmss", "networking", "vnet", "vpn", "load balanc",
    "storage", "security", "encryption", "monitor", "log analytics", "telemetry",
    "incident", "root cause", "outage", "backup", "recovery", "image builder",
    "compute gallery", "provision", "automation", "runbook"
  ],
  "machine-learning": [
    "python", "pytorch", "machine learning", "deep learning", "nlp", "llm",
    "fine-tun", "training", "model", "gpu", "hpc", "feature", "evaluation",
    "data pipeline", "streaming", "inference"
  ],
  "data-analytics": [
    "sql", "excel", "bigquery", "postgresql", "report", "dashboard", "analytics",
    "reconciliation", "validation", "data quality", "trend", "metric", "insight",
    "sales", "revenue", "tip", "kpi", "variance", "financial", "business", "operation",
    "workforce", "payroll", "telemetry", "log analytics"
  ],
  "general-technical": [
    "python", "sql", "javascript", "azure", "aws", "automation", "api",
    "postgresql", "docker", "terraform", "data", "cloud"
  ]
};

const PROFILE_ENTRY_BOOSTS = {
  "data-engineering": {"aramark-data-ops": 8, "ltimindtree-cloud": 5},
  "software-engineering": {"aramark-data-ops": 8, "infra-developers-web": 8, "ltimindtree-cloud": 4},
  "cloud-devops": {"ltimindtree-cloud": 18, "aramark-data-ops": 2},
  "machine-learning": {"aramark-data-ops": 3, "ltimindtree-cloud": 3},
  "data-analytics": {"aramark-data-ops": 18, "ltimindtree-cloud": 4},
  "general-technical": {}
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

function targetHeadline(job, profile) {
  return clean(job?.title) || profileLabel(profile);
}

function profileDescriptor(profile) {
  return PROFILE_DESCRIPTORS[profile] || PROFILE_DESCRIPTORS["general-technical"];
}

function profileSummary(profile) {
  const summaries = {
    "data-engineering": "Data engineer with 4+ years of total experience across Azure cloud engineering, operational data platforms, and web development. Built BigQuery ELT and PostgreSQL/Supabase systems handling 5,000+ records per event, plus Kafka, Redshift, dbt, and Airflow projects.",
    "software-engineering": "Software engineer with 4+ years of total experience across full-stack development, operational platforms, and Azure production engineering. Built a JavaScript/PostgreSQL/Supabase platform for a 45,000+ seat venue, real-estate websites for two clients, and cloud automation used in production support.",
    "cloud-devops": "Cloud/DevOps engineer with 4+ years of total experience, including 2+ years on a Microsoft Azure VM vendor team where I progressed from Junior Engineer to SME. Guided 40–50 investigations a week and automated Azure work with PowerShell, Terraform, Docker, and Kubernetes.",
    "machine-learning": "Data/ML engineer with 4+ years of total experience across cloud engineering, operational data, and applied ML. Fine-tuned Qwen2.5-Coder-7B on a 624K+ row dataset and brings hands-on PyTorch, NLP, streaming-pipeline, and GPU/HPC experience.",
    "data-analytics": "Data analyst with 4+ years of total experience across operational analytics, cloud engineering, and reporting. Uses SQL, Excel, BigQuery, and PostgreSQL to analyze high-volume event operations, including $200K+ football sales per game, 5,000+ records per event, and validation workflows that improved discrepancy detection by 30%.",
    "general-technical": "Engineer with 4+ years of total experience across Azure cloud infrastructure, operational data platforms, full-stack web development, and technical projects. Currently completing an M.S. in Data Science, Analytics & Engineering at Arizona State University with a 4.0 GPA."
  };
  return summaries[profile] || summaries["general-technical"];
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
  return pos < 0 ? 0 : (8 - pos * 2);
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
  const detected = unique(job.detected_skills || []);
  const topJd = detected.slice(0, TOP_JD_SKILLS);

  const verifiedTopJd = [];
  const jdGaps = [];
  for (const skill of topJd) {
    const hit = evidence.get(key(skill)) || base.get(key(skill));
    if (hit) verifiedTopJd.push(hit);
    else jdGaps.push(skill);
  }

  const extraJdVerified = [];
  for (const skill of detected.slice(TOP_JD_SKILLS)) {
    const hit = evidence.get(key(skill)) || base.get(key(skill));
    if (hit) extraJdVerified.push(hit);
  }

  const roleCore = [];
  for (const desired of ROLE_CORE_SKILLS[profile] || ROLE_CORE_SKILLS["general-technical"]) {
    const hit = evidence.get(key(desired)) || base.get(key(desired));
    if (hit) roleCore.push(hit);
  }

  const topSet = skillSet(verifiedTopJd);
  const related = unique([...extraJdVerified, ...roleCore])
    .filter((s) => !topSet.has(key(s)))
    .slice(0, MAX_RELATED_SKILLS);
  const all = unique([...verifiedTopJd, ...related]).slice(0, MAX_SKILLS);

  return {
    all,
    topJd,
    jd: unique(verifiedTopJd),
    gaps: unique(jdGaps),
    related,
  };
}

function scoringSkills(job) {
  return job.effective_skills || job.detected_skills || job.verified_skills || [];
}

function scoreBullet(bullet, job, profile, projectId = "", sourceId = "") {
  if (!bullet || bullet.verified !== true) return -9999;
  const effective = skillSet(scoringSkills(job));
  const directJd = skillSet(job.top_jd_skills || job.detected_skills || job.verified_skills || []);
  let score = 0;

  for (const skill of bullet.skills || []) {
    const k = key(skill);
    if (directJd.has(k)) score += 16;
    else if (effective.has(k)) score += 7;
  }

  const body = key(`${bullet.text || ""} ${(bullet.keywords || []).join(" ")} ${(bullet.skills || []).join(" ")}`);
  for (const term of job.signal_terms || []) {
    if (body.includes(key(term))) score += 4;
  }

  for (const term of PROFILE_BULLET_TERMS[profile] || PROFILE_BULLET_TERMS["general-technical"]) {
    if (body.includes(key(term))) score += 3;
  }

  const titleWords = key(job.title).split(/\s+/).filter((x) => x.length >= 4);
  for (const word of titleWords) {
    if (body.includes(word)) score += 1;
  }

  score += PROFILE_ENTRY_BOOSTS[profile]?.[sourceId] || 0;
  if (projectId) score += profileBoost(profile, projectId);
  return score;
}

function selectBullets(entry, job, profile, maxBullets, projectId = "", minBullets = 1) {
  const verified = (entry.bullets || [])
    .filter((b) => b.verified === true)
    .map((b, index) => ({ ...b, _score: scoreBullet(b, job, profile, projectId, entry.id), _index: index }))
    .sort((a, b) => b._score - a._score || a._index - b._index);

  if (!verified.length) return [];
  const positive = verified.filter((b) => b._score > 0);
  const chosen = [...positive];
  const seen = new Set(chosen.map((b) => b._index));
  for (const bullet of verified) {
    if (chosen.length >= Math.min(maxBullets, Math.max(minBullets, positive.length))) break;
    if (!seen.has(bullet._index)) {
      chosen.push(bullet);
      seen.add(bullet._index);
    }
  }
  return chosen.slice(0, maxBullets);
}

function experienceLimit(profile, entryId) {
  return EXPERIENCE_LIMITS[profile]?.[entryId]
    ?? EXPERIENCE_LIMITS["general-technical"]?.[entryId]
    ?? 3;
}

function experienceMinimum(profile, entryId) {
  return EXPERIENCE_MINIMUMS[profile]?.[entryId]
    ?? EXPERIENCE_MINIMUMS["general-technical"]?.[entryId]
    ?? 1;
}

function resolveFocus(entry, profile) {
  const fromMaster = entry?.functional_focus;
  if (fromMaster && typeof fromMaster === "object") {
    const hit = clean(fromMaster[profile] || fromMaster["general-technical"]);
    if (hit) return hit;
  }
  return clean(DEFAULT_FOCUS[entry?.id]?.[profile] || DEFAULT_FOCUS[entry?.id]?.["general-technical"] || "");
}

function selectedEntryMatches(entry, job) {
  const jd = skillSet(job.top_jd_skills || job.detected_skills || job.verified_skills || []);
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
  return projects.filter((p) => p.selectedBullets.length && p._score > 0).slice(0, MAX_PROJECTS);
}

function normalizeMetrics(values) {
  return (Array.isArray(values) ? values : [])
    .map((item) => ({
      value: clean(item?.value),
      label: clean(item?.label),
    }))
    .filter((item) => item.value && item.label)
    .slice(0, 4);
}

function candidateMetrics(master, job, profile) {
  const titleKey = key(job?.title);
  for (const [title, values] of Object.entries(master?.role_metrics || {})) {
    if (key(title) === titleKey) {
      const exact = normalizeMetrics(values);
      if (exact.length) return exact;
    }
  }

  const catalog = Array.isArray(master?.metric_catalog) ? master.metric_catalog : [];
  if (catalog.length) {
    const jdText = key([
      job?.title,
      ...(job?.top_jd_skills || []),
      ...(job?.detected_skills || []),
      ...(job?.signal_terms || []),
    ].join(" "));
    const ranked = catalog
      .filter((m) => clean(m?.value) && clean(m?.label))
      .map((m, index) => {
        let score = 0;
        const profiles = Array.isArray(m.profiles) ? m.profiles.map(key) : [];
        if (profiles.includes(key(profile))) score += 10;
        for (const term of m.keywords || []) {
          if (jdText.includes(key(term))) score += 8;
        }
        return { ...m, _score: score, _index: index };
      })
      .filter((m) => m._score > 0)
      .sort((a, b) => b._score - a._score || a._index - b._index);

    const selected = [];
    const seen = new Set();
    for (const item of ranked) {
      const metricKey = key(item.value + " " + item.label);
      if (seen.has(metricKey)) continue;
      selected.push({ value: clean(item.value), label: clean(item.label) });
      seen.add(metricKey);
      if (selected.length >= 4) break;
    }
    if (selected.length >= 3) return selected;
  }

  return normalizeMetrics(master?.profile_metrics?.[profile] || master?.profile_metrics?.["general-technical"] || []);
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
  const scoringJob = {
    ...job,
    effective_skills: skillBundle.all,
    top_jd_skills: skillBundle.topJd,
  };

  const experience = (master.experience || []).map((entry) => {
    const selectedBullets = selectBullets(
      entry,
      scoringJob,
      profile,
      experienceLimit(profile, entry.id),
      "",
      experienceMinimum(profile, entry.id)
    );
    return {
      ...entry,
      functionalFocus: resolveFocus(entry, profile),
      selectedBullets,
      matchedSignals: selectedEntryMatches({ selectedBullets }, scoringJob),
    };
  });

  const projects = selectProjects(master, scoringJob, profile);
  return {
    contact: master.contact,
    headline: targetHeadline(job, profile),
    descriptor: profileDescriptor(profile),
    summary: profileSummary(profile),
    metrics: candidateMetrics(master, job, profile),
    skills: skillBundle.all,
    topJdSkills: skillBundle.topJd,
    jdSkills: skillBundle.jd,
    jdGaps: skillBundle.gaps,
    relatedSkills: skillBundle.related,
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
  const topJd = unique(job.detected_skills || []).slice(0, TOP_JD_SKILLS);
  $("skills").innerHTML = topJd.length
    ? topJd.map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join("")
    : '<span class="chip">Title/profile signals only</span>';
  $("signalNote").textContent = job.signal_source === "job-page"
    ? `Showing the top ${topJd.length || TOP_JD_SKILLS} detected JD skills. The full job description is not republished here.`
    : "The job page did not expose enough readable text, so this resume uses title/profile signals plus verified core skills for the role. Review the preview before applying.";
}

function renderCandidate(candidate) {
  const expBulletCount = candidate.experience.reduce((n, e) => n + e.selectedBullets.length, 0);
  const jdDenominator = candidate.topJdSkills.length || TOP_JD_SKILLS;
  $("jdSkillCount").textContent = `${candidate.jdSkills.length}/${jdDenominator}`;
  $("skillCount").textContent = String(candidate.skills.length);
  $("bulletCount").textContent = String(expBulletCount);
  $("fitTitle").textContent = `${candidate.headline} resume ready`;

  const parts = [];
  parts.push(`<h3>TARGET POSITION</h3><p><strong>${escapeHtml(candidate.headline)}</strong> <span class="tiny muted">• ${escapeHtml(candidate.descriptor)}</span></p>`);
  parts.push(`<h3>SUMMARY</h3><p>${escapeHtml(candidate.summary)}</p>`);
  if (candidate.metrics.length) {
    parts.push(`<div class="resumeMetricStrip">${candidate.metrics.map((m) => `<div><strong>${escapeHtml(m.value)}</strong><span>${escapeHtml(m.label)}</span></div>`).join("")}</div>`);
  }
  parts.push(`<h3>RELEVANT VERIFIED SKILLS</h3><p>${escapeHtml(candidate.skills.join(" • ") || "No verified skills available")}</p>`);
  if (candidate.topJdSkills.length) {
    parts.push(`<p class="tiny muted"><strong>Top JD skills detected:</strong> ${escapeHtml(candidate.topJdSkills.join(" • "))}</p>`);
  }
  if (candidate.jdSkills.length) {
    parts.push(`<p class="tiny muted"><strong>Top JD skills verified:</strong> ${escapeHtml(candidate.jdSkills.join(" • "))}</p>`);
  }
  if (candidate.jdGaps.length) {
    parts.push(`<p class="tiny muted"><strong>JD gaps not claimed:</strong> ${escapeHtml(candidate.jdGaps.join(" • "))}</p>`);
  }
  if (candidate.relatedSkills.length) {
    parts.push(`<p class="tiny muted"><strong>Additional verified JD/role strengths:</strong> ${escapeHtml(candidate.relatedSkills.join(" • "))}</p>`);
  }

  parts.push("<h3>EXPERIENCE</h3>");
  for (const exp of candidate.experience) {
    if (!exp.selectedBullets.length) continue;
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
      italics: !!options.italics,
      size: options.size || 20,
      font: "Arial",
      color: options.color || undefined,
    })],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    spacing: { before: 125, after: 45 },
    border: { bottom: { color: "CBD5E1", size: 8, style: BorderStyle.SINGLE } },
    children: [new TextRun({ text, bold: true, size: 20, font: "Arial", color: "1F4E79" })],
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

function skillCategory(skill) {
  const k = key(skill);
  const languages = ["python", "javascript", "java", "bash", "powershell", "sql"];
  const data = ["postgresql", "supabase", "bigquery", "redshift", "dbt", "apache airflow", "kafka", "apache spark", "pandas", "numpy", "neo4j", "streamlit", "excel", "data validation", "data reconciliation", "etl/elt", "sales analysis", "kpi reporting", "operational analytics", "variance analysis"];
  const cloud = ["microsoft azure", "azure cli", "azure monitor", "log analytics", "aws", "terraform", "docker", "kubernetes", "github actions", "linux", "networking", "security"];
  const ml = ["machine learning", "pytorch", "nlp", "llm fine-tuning", "hpc"];
  const web = ["html5", "css", "wordpress", "responsive web design", "dns & hosting", "seo", "google analytics", "google search console", "rest apis"];
  if (languages.includes(k)) return "Languages";
  if (data.includes(k)) return "Data & Analytics";
  if (cloud.includes(k)) return "Cloud & DevOps";
  if (ml.includes(k)) return "ML";
  if (web.includes(k)) return "Web & APIs";
  return "Other";
}

function groupedSkills(skills) {
  const order = ["Languages", "Data & Analytics", "Cloud & DevOps", "ML", "Web & APIs", "Other"];
  const groups = new Map(order.map((name) => [name, []]));
  for (const skill of unique(skills || [])) groups.get(skillCategory(skill)).push(skill);
  return order.map((name) => [name, groups.get(name)]).filter(([, values]) => values.length);
}

async function candidateBlob(candidate) {
  const children = [];
  children.push(textParagraph(candidate.contact.name, { bold: true, size: 30, center: true, after: 20, color: "1F4E79" }));
  children.push(textParagraph(candidate.headline, { bold: true, size: 19, center: true, after: 18 }));
  children.push(textParagraph(candidate.descriptor, { size: 16, center: true, after: 30 }));

  const contactLine = [
    candidate.contact.location,
    candidate.contact.email,
    candidate.contact.phone,
    ...(candidate.contact.links || []),
  ].filter(Boolean).join(" | ");
  children.push(textParagraph(contactLine, { center: true, size: 17, after: 75 }));

  children.push(sectionHeading("SUMMARY"));
  children.push(textParagraph(candidate.summary, { after: 45 }));
  if (candidate.metrics.length) {
    const metricLine = candidate.metrics.map((m) => `${m.value} — ${m.label}`).join("   |   ");
    children.push(textParagraph(metricLine, { bold: true, size: 16, center: true, after: 48, color: "1F4E79" }));
  }

  if (candidate.skills.length) {
    children.push(sectionHeading("TECHNICAL SKILLS"));
    for (const [label, values] of groupedSkills(candidate.skills)) {
      children.push(new Paragraph({
        spacing: { after: 24, line: 205 },
        children: [
          new TextRun({ text: `${label}: `, bold: true, size: 17, font: "Arial" }),
          new TextRun({ text: values.join(", "), size: 17, font: "Arial" }),
        ],
      }));
    }
  }

  children.push(sectionHeading("EXPERIENCE"));
  for (const exp of candidate.experience) {
    if (!exp.selectedBullets.length) continue;
    children.push(roleParagraph(exp));
    for (const bullet of exp.selectedBullets) children.push(bulletParagraph(bullet.text));
  }

  if (candidate.projects.length) {
    children.push(sectionHeading("SELECTED PROJECTS"));
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
          margin: { top: 430, right: 500, bottom: 430, left: 500 },
        },
      },
      children,
    }],
  });
  return Packer.toBlob(doc);
}

function pdfText(doc, text, x, y, width, size = 8, style = "normal", lineHeight = 9.4) {
  doc.setFont("helvetica", style);
  doc.setFontSize(size);
  const lines = doc.splitTextToSize(clean(text), width);
  doc.text(lines, x, y);
  return y + Math.max(1, lines.length) * lineHeight;
}

function candidatePdfVariant(candidate, options = {}) {
  const clone = {
    ...candidate,
    experience: (candidate.experience || []).map((exp) => ({
      ...exp,
      selectedBullets: [...(exp.selectedBullets || [])].slice(0, options.expCapPerEntry || 99),
    })),
    projects: [...(candidate.projects || [])].slice(0, options.projectCap ?? 99).map((p) => ({
      ...p,
      selectedBullets: [...(p.selectedBullets || [])].slice(0, options.projectBulletCap || 2),
    })),
  };
  return clone;
}

const PDF_LAYOUTS = [
  { name: "spacious", body: 8.25, bodyLine: 9.85, bullet: 8.0, bulletLine: 9.55, section: 9.0, sectionGap: 12.4, role: 8.3, skill: 7.65, skillLine: 8.95, metricValue: 10.5, metricLabel: 6.0, metricH: 36.5, gapScale: 1.08 },
  { name: "standard", body: 8.0, bodyLine: 9.45, bullet: 7.75, bulletLine: 9.1, section: 8.8, sectionGap: 11.7, role: 8.15, skill: 7.45, skillLine: 8.65, metricValue: 10.1, metricLabel: 5.8, metricH: 35, gapScale: 1.0 },
  { name: "compact", body: 7.7, bodyLine: 9.0, bullet: 7.45, bulletLine: 8.65, section: 8.55, sectionGap: 11.0, role: 7.95, skill: 7.2, skillLine: 8.35, metricValue: 9.7, metricLabel: 5.6, metricH: 33.5, gapScale: 0.92 },
];

function renderCandidatePdf(candidate, spec) {
  const doc = new jsPDF({ orientation: "portrait", unit: "pt", format: "letter", compress: true });
  doc.setProperties({ title: "", subject: "", author: "", keywords: "", creator: "" });

  const pageW = 612, pageH = 792, left = 30, right = 30, contentW = 552, bottom = 24;
  const NAVY = [31, 78, 121], TEXT = [31, 41, 55], MUTED = [71, 85, 105], LINE = [203, 213, 225], PALE = [248, 250, 252];
  let y = 29;
  let overflowed = false;

  const textColor = (rgb) => doc.setTextColor(rgb[0], rgb[1], rgb[2]);
  const need = (height = 20) => {
    if (y + height > pageH - bottom) overflowed = true;
    return !overflowed;
  };
  const section = (title) => {
    if (!need(20)) return;
    y += 3.7 * spec.gapScale;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(spec.section);
    textColor(NAVY);
    doc.text(title.toUpperCase(), left, y);
    doc.setDrawColor(LINE[0], LINE[1], LINE[2]);
    doc.setLineWidth(0.8);
    doc.line(left, y + 3.1, pageW - right, y + 3.1);
    y += spec.sectionGap;
    textColor(TEXT);
  };
  const blockText = (text, x, width, size, lineHeight, style = "normal") => {
    doc.setFont("helvetica", style);
    doc.setFontSize(size);
    const lines = doc.splitTextToSize(clean(text), width);
    if (!need(Math.max(1, lines.length) * lineHeight + 1)) return;
    doc.text(lines, x, y);
    y += Math.max(1, lines.length) * lineHeight;
  };
  const bullet = (text) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(spec.bullet);
    textColor(TEXT);
    const lines = doc.splitTextToSize(clean(text), contentW - 13);
    const h = Math.max(1, lines.length) * spec.bulletLine + 2.0 * spec.gapScale;
    if (!need(h)) return;
    doc.text("-", left + 2, y);
    doc.text(lines, left + 11, y);
    y += h;
  };
  const metrics = () => {
    if (!candidate.metrics?.length || !need(spec.metricH + 4)) return;
    const boxH = spec.metricH, boxW = contentW / candidate.metrics.length;
    doc.setFillColor(PALE[0], PALE[1], PALE[2]);
    doc.setDrawColor(LINE[0], LINE[1], LINE[2]);
    doc.setLineWidth(0.55);
    doc.rect(left, y, contentW, boxH, "FD");
    candidate.metrics.forEach((m, i) => {
      const x = left + i * boxW;
      if (i > 0) {
        doc.setDrawColor(LINE[0], LINE[1], LINE[2]);
        doc.line(x, y, x, y + boxH);
      }
      doc.setFont("helvetica", "bold");
      doc.setFontSize(spec.metricValue);
      textColor(NAVY);
      doc.text(clean(m.value), x + boxW / 2, y + 12, { align: "center" });
      doc.setFont("helvetica", "normal");
      doc.setFontSize(spec.metricLabel);
      textColor(MUTED);
      const label = doc.splitTextToSize(clean(m.label), boxW - 10).slice(0, 2);
      doc.text(label, x + boxW / 2, y + 21, { align: "center" });
    });
    y += boxH + 3.5 * spec.gapScale;
    textColor(TEXT);
  };

  doc.setFont("helvetica", "bold");
  doc.setFontSize(17.2);
  textColor(NAVY);
  doc.text(clean(candidate.contact.name).toUpperCase(), pageW / 2, y, { align: "center" });
  y += 15.2 * spec.gapScale;

  doc.setFontSize(9.25);
  textColor(TEXT);
  doc.text(clean(candidate.headline), pageW / 2, y, { align: "center" });
  y += 9.8 * spec.gapScale;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.05);
  textColor(MUTED);
  doc.text(clean(candidate.descriptor), pageW / 2, y, { align: "center" });
  y += 8.7 * spec.gapScale;

  const contact = [candidate.contact.location, candidate.contact.phone, candidate.contact.email, ...(candidate.contact.links || [])].filter(Boolean).join(" | ");
  const contactLines = doc.splitTextToSize(contact, contentW);
  doc.setFontSize(7.05);
  if (need(contactLines.length * 7.8 + 5)) {
    doc.text(contactLines, pageW / 2, y, { align: "center" });
    y += contactLines.length * 7.8 + 4;
  }

  doc.setDrawColor(NAVY[0], NAVY[1], NAVY[2]);
  doc.setLineWidth(1.15);
  doc.line(left, y, pageW - right, y);
  y += 3.5 * spec.gapScale;

  section("Summary");
  textColor(TEXT);
  blockText(candidate.summary, left, contentW, spec.body, spec.bodyLine, "normal");
  y += 1.2 * spec.gapScale;
  metrics();

  if (candidate.skills.length && !overflowed) {
    section("Technical Skills");
    for (const [label, values] of groupedSkills(candidate.skills)) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(spec.skill);
      textColor(TEXT);
      const prefix = label + ":";
      const labelW = doc.getTextWidth(prefix + " ");
      const lines = doc.splitTextToSize(values.join(", "), contentW - labelW);
      const h = Math.max(1, lines.length) * spec.skillLine + 1.2 * spec.gapScale;
      if (!need(h)) break;
      doc.text(prefix, left, y);
      doc.setFont("helvetica", "normal");
      doc.text(lines, left + labelW, y);
      y += h;
    }
  }

  if (!overflowed) section("Experience");
  for (const exp of candidate.experience || []) {
    if (overflowed || !exp.selectedBullets?.length) break;
    const dateText = exp.start && exp.end ? `${exp.start} - ${exp.end}` : "";
    doc.setFont("helvetica", "bold");
    doc.setFontSize(spec.role);
    textColor(TEXT);
    const leftText = [clean(exp.title), clean(exp.company)].filter(Boolean).join(" | ");
    const roleLines = doc.splitTextToSize(leftText, dateText ? contentW - 120 : contentW);
    const roleH = Math.max(1, roleLines.length) * 8.8 + 1.5;
    if (!need(roleH + 12)) break;
    doc.text(roleLines, left, y);
    if (dateText) {
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.0);
      textColor(MUTED);
      doc.text(dateText, pageW - right, y, { align: "right" });
    }
    y += roleH;
    for (const item of exp.selectedBullets) {
      if (overflowed) break;
      bullet(item.text);
    }
    y += 0.5 * spec.gapScale;
  }

  if (candidate.projects.length && !overflowed) {
    section("Selected Projects");
    for (const project of candidate.projects) {
      if (overflowed) break;
      doc.setFont("helvetica", "bold");
      doc.setFontSize(spec.role - 0.1);
      textColor(TEXT);
      const projectLine = [clean(project.name), clean(project.subtitle)].filter(Boolean).join(" | ");
      const projectLines = doc.splitTextToSize(projectLine, contentW);
      const ph = Math.max(1, projectLines.length) * 8.7 + 1;
      if (!need(ph + 10)) break;
      doc.text(projectLines, left, y);
      y += ph;
      for (const item of project.selectedBullets) {
        if (overflowed) break;
        bullet(item.text);
      }
    }
  }

  if (candidate.education.length && !overflowed) {
    section("Education");
    for (const edu of candidate.education) {
      if (overflowed) break;
      doc.setFont("helvetica", "bold");
      doc.setFontSize(7.7);
      textColor(TEXT);
      const schoolLine = [clean(edu.school), clean(edu.degree)].filter(Boolean).join(" | ");
      const dates = edu.start && edu.end ? `${edu.start} - ${edu.end}` : clean(edu.end);
      if (!need(18)) break;
      doc.text(doc.splitTextToSize(schoolLine, dates ? contentW - 110 : contentW), left, y);
      if (dates) {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(6.9);
        textColor(MUTED);
        doc.text(dates, pageW - right, y, { align: "right" });
      }
      y += 8.6;
      for (const detail of edu.details || []) {
        if (overflowed) break;
        blockText(detail, left + 5, contentW - 5, 7.15, 8.15, "normal");
      }
    }
  }

  if (candidate.certifications.length && !overflowed) {
    section("Certifications");
    blockText(candidate.certifications.join(" | "), left, contentW, 7.1, 8.1, "normal");
  }

  return { doc, y, overflowed };
}

function chooseOnePagePdf(candidate) {
  const variants = [
    candidatePdfVariant(candidate, { projectCap: 3, projectBulletCap: 2, expCapPerEntry: 99 }),
    candidatePdfVariant(candidate, { projectCap: 2, projectBulletCap: 2, expCapPerEntry: 99 }),
    candidatePdfVariant(candidate, { projectCap: 2, projectBulletCap: 1, expCapPerEntry: 4 }),
    candidatePdfVariant(candidate, { projectCap: 1, projectBulletCap: 1, expCapPerEntry: 4 }),
  ];

  const successful = [];
  for (const variant of variants) {
    for (const spec of PDF_LAYOUTS) {
      const rendered = renderCandidatePdf(variant, spec);
      if (!rendered.overflowed && rendered.y <= 768) {
        successful.push({ ...rendered, spec, variant, distance: Math.abs(744 - rendered.y) });
      }
    }
    if (successful.length) break;
  }

  if (!successful.length) {
    const fallback = renderCandidatePdf(
      candidatePdfVariant(candidate, { projectCap: 1, projectBulletCap: 1, expCapPerEntry: 3 }),
      PDF_LAYOUTS[2]
    );
    return fallback.doc;
  }

  successful.sort((a, b) => a.distance - b.distance);
  return successful[0].doc;
}

function candidatePdfBlob(candidate) {
  return chooseOnePagePdf(candidate).output("blob");
}

async function downloadPdfResume() {
  if (!currentCandidate || !currentJob) throw new Error("Resume is not ready.");
  triggerDownload(candidatePdfBlob(currentCandidate), `${safeFilename(currentJob)}-resume.pdf`);
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

$("downloadDocx").addEventListener("click", async () => {
  try { await downloadResume(); } catch (err) { showError(err.message); }
});

$("downloadPdf").addEventListener("click", async () => {
  try { await downloadPdfResume(); } catch (err) { showError(err.message); }
});

$("downloadPdfApply").addEventListener("click", async () => {
  try {
    const applyWindow = currentJob?.apply_url ? window.open("about:blank", "_blank") : null;
    await downloadPdfResume();
    if (applyWindow && currentJob?.apply_url) {
      applyWindow.opener = null;
      applyWindow.location = currentJob.apply_url;
    }
  } catch (err) { showError(err.message); }
});

$("openApply").addEventListener("click", () => {
  if (currentJob?.apply_url) window.open(currentJob.apply_url, "_blank", "noopener,noreferrer");
});

const legacyDownloadApply = $("downloadApply");
if (legacyDownloadApply) {
  legacyDownloadApply.addEventListener("click", async () => {
    try {
      const applyWindow = currentJob?.apply_url ? window.open("about:blank", "_blank") : null;
      await downloadResume();
      if (applyWindow && currentJob?.apply_url) {
        applyWindow.opener = null;
        applyWindow.location = currentJob.apply_url;
      }
    } catch (err) { showError(err.message); }
  });
}

try {
  const saved = localStorage.getItem(MASTER_KEY);
  if (saved) setMaster(JSON.parse(saved));
} catch {
  localStorage.removeItem(MASTER_KEY);
}

loadJob().catch((err) => showError(err.message));
