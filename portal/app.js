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
const MAX_PROJECTS = 2;

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
    "Data Reconciliation", "Python", "Pandas", "NumPy", "Supabase",
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
  "data-analytics": "SQL, Reporting & Data Quality",
  "general-technical": "Technical Engineering"
};

const DEFAULT_FOCUS = {
  "aramark-data-ops": {
    "data-engineering": "Data Engineering & Operational Platforms",
    "software-engineering": "Software & Data Platform Development",
    "cloud-devops": "Platform Operations & Automation",
    "machine-learning": "Data & ML Analytics",
    "data-analytics": "Data Analytics & Reporting",
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
  "data-engineering": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1},
  "software-engineering": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 2},
  "cloud-devops": {"aramark-data-ops": 2, "ltimindtree-cloud": 4, "infra-developers-web": 1},
  "machine-learning": {"aramark-data-ops": 2, "ltimindtree-cloud": 2, "infra-developers-web": 1},
  "data-analytics": {"aramark-data-ops": 4, "ltimindtree-cloud": 2, "infra-developers-web": 1},
  "general-technical": {"aramark-data-ops": 3, "ltimindtree-cloud": 3, "infra-developers-web": 1}
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
    "data-engineering": "Data engineer with 3+ years across Azure cloud engineering and operational data platforms. Built BigQuery ELT and PostgreSQL/Supabase systems handling 5,000+ records per event, plus Kafka, Redshift, dbt, and Airflow projects.",
    "software-engineering": "Software engineer with full-stack JavaScript/PostgreSQL/Supabase experience and 2+ years in Azure production engineering. Built a role-based platform for a 45,000+ seat venue, real-estate websites for two clients, and cloud automation used in production support.",
    "cloud-devops": "Cloud/DevOps engineer with 2+ years on a Microsoft Azure VM vendor team, progressing from Junior Engineer to SME. Guided 40–50 investigations a week and automated Azure work with PowerShell, Terraform, Docker, and Kubernetes.",
    "machine-learning": "Data/ML engineer and M.S. Data Science candidate with PyTorch, NLP, streaming pipelines, and GPU/HPC experience. Fine-tuned Qwen2.5-Coder-7B on a 624K+ row dataset and brings 2+ years of Azure engineering experience.",
    "data-analytics": "Data analyst with hands-on SQL, Excel, BigQuery, and PostgreSQL experience across workforce and cloud operations. Reconciles 5,000+ records per event and built validation/reporting workflows that improved discrepancy detection by 30%.",
    "general-technical": "Engineer with 3+ years across Azure cloud infrastructure, operational data platforms, full-stack web development, and technical projects. Currently completing an M.S. in Data Science, Analytics & Engineering at Arizona State University."
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

function scoreBullet(bullet, job, profile, projectId = "") {
  if (!bullet || bullet.verified !== true) return -9999;
  const effective = skillSet(scoringSkills(job));
  const directJd = skillSet(job.top_jd_skills || job.detected_skills || job.verified_skills || []);
  let score = 0;

  for (const skill of bullet.skills || []) {
    const k = key(skill);
    if (directJd.has(k)) score += 16;
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
      experienceLimit(profile, entry.id)
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

function skillCategory(skill) {
  const k = key(skill);
  const languages = ["python", "javascript", "java", "bash", "powershell", "sql"];
  const data = ["postgresql", "supabase", "bigquery", "redshift", "dbt", "apache airflow", "kafka", "apache spark", "pandas", "numpy", "neo4j", "streamlit", "excel", "data validation", "data reconciliation", "etl/elt"];
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
  children.push(textParagraph(candidate.contact.name, { bold: true, size: 30, center: true, after: 20 }));
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
  children.push(textParagraph(candidate.summary, { after: 55 }));

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

function candidatePdfBlob(candidate) {
  const doc = new jsPDF({ orientation: "portrait", unit: "pt", format: "letter", compress: true });
  doc.setProperties({ title: "", subject: "", author: "", keywords: "", creator: "" });
  const pageW = 612, pageH = 792, left = 32, right = 32, contentW = 548, bottom = 32;
  let y = 35;
  const ensure = (needed = 28) => { if (y + needed > pageH - bottom) { doc.addPage(); y = 34; } };
  const section = (title) => {
    ensure(24); y += 5; doc.setFont("helvetica", "bold"); doc.setFontSize(8.6); doc.text(title.toUpperCase(), left, y);
    doc.setDrawColor(80); doc.setLineWidth(0.55); doc.line(left, y + 3, pageW - right, y + 3); y += 12;
  };
  const bullet = (text) => {
    ensure(22); doc.setFont("helvetica", "normal"); doc.setFontSize(7.9);
    const lines = doc.splitTextToSize(clean(text), contentW - 13); doc.text("-", left + 2, y); doc.text(lines, left + 11, y);
    y += Math.max(1, lines.length) * 9.3 + 2.4;
  };
  doc.setFont("helvetica", "bold"); doc.setFontSize(16); doc.text(clean(candidate.contact.name).toUpperCase(), pageW / 2, y, { align: "center" });
  y += 16; doc.setFontSize(9); doc.text(clean(candidate.headline), pageW / 2, y, { align: "center" });
  y += 11; doc.setFont("helvetica", "normal"); doc.setFontSize(7.5); doc.text(clean(candidate.descriptor), pageW / 2, y, { align: "center" });
  y += 10;
  const contact = [candidate.contact.location, candidate.contact.phone, candidate.contact.email, ...(candidate.contact.links || [])].filter(Boolean).join(" | ");
  const contactLines = doc.splitTextToSize(contact, contentW); doc.text(contactLines, pageW / 2, y, { align: "center" }); y += contactLines.length * 8.2 + 3;
  section("Summary"); y = pdfText(doc, candidate.summary, left, y, contentW, 8.1, "normal", 9.8) + 2;
  if (candidate.skills.length) {
    section("Technical Skills");
    for (const [label, values] of groupedSkills(candidate.skills)) {
      ensure(16); doc.setFont("helvetica", "bold"); doc.setFontSize(7.75); doc.text(label + ":", left, y);
      const labelW = doc.getTextWidth(label + ": "); doc.setFont("helvetica", "normal");
      const lines = doc.splitTextToSize(values.join(", "), contentW - labelW); doc.text(lines, left + labelW, y); y += Math.max(1, lines.length) * 9.1 + 1.8;
    }
  }
  section("Experience");
  for (const exp of candidate.experience) {
    ensure(36); doc.setFont("helvetica", "bold"); doc.setFontSize(8.35);
    const leftText = [clean(exp.title), clean(exp.company)].filter(Boolean).join(" | "); doc.text(leftText, left, y);
    const dateText = exp.start && exp.end ? `${exp.start} - ${exp.end}` : ""; if (dateText) doc.text(dateText, pageW - right, y, { align: "right" });
    y += 10; for (const item of exp.selectedBullets) bullet(item.text); y += 1;
  }
  if (candidate.projects.length) {
    section("Projects");
    for (const project of candidate.projects) {
      ensure(29); doc.setFont("helvetica", "bold"); doc.setFontSize(8.25);
      const projectLine = [clean(project.name), clean(project.subtitle)].filter(Boolean).join(" | "); doc.text(doc.splitTextToSize(projectLine, contentW), left, y);
      y += 10; for (const item of project.selectedBullets) bullet(item.text); y += 1;
    }
  }
  if (candidate.education.length) {
    section("Education");
    for (const edu of candidate.education) {
      ensure(20); doc.setFont("helvetica", "bold"); doc.setFontSize(8.0);
      const schoolLine = [clean(edu.school), clean(edu.degree)].filter(Boolean).join(" | "); doc.text(schoolLine, left, y);
      const dates = edu.start && edu.end ? `${edu.start} - ${edu.end}` : clean(edu.end); if (dates) doc.text(dates, pageW - right, y, { align: "right" });
      y += 9.5; for (const detail of edu.details || []) y = pdfText(doc, detail, left + 5, y, contentW - 5, 7.6, "normal", 8.8);
    }
  }
  if (candidate.certifications.length) { section("Certifications"); y = pdfText(doc, candidate.certifications.join(" | "), left, y, contentW, 7.6, "normal", 8.8); }
  return doc.output("blob");
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
