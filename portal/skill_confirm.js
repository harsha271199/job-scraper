(() => {
  const MASTER_KEY = "jobScraper.privateMaster.v1";
  const CONFIRMED_KEY = "jobScraper.userConfirmedSkills.v1";
  const MANUAL_JD_KEY = "jobScraper.manualJdSkills.v1";
  const TOP_JD_SKILLS = 10;
  // Confirm Top JD skills already in your real skill set.

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

  const JD_SKILL_ALIASES = [
    ["Python", ["python"]], ["JavaScript", ["javascript", "js"]],
    ["TypeScript", ["typescript"]], ["Java", ["java"]], ["C++", ["c++"]],
    ["C#", ["c#"]], ["Go", ["golang", "go language"]], ["Scala", ["scala"]],
    ["R", ["r programming", "r language"]], ["SQL", ["sql"]],
    ["PostgreSQL", ["postgresql", "postgres"]], ["MySQL", ["mysql"]],
    ["MongoDB", ["mongodb"]], ["Redis", ["redis"]], ["NoSQL", ["nosql"]],
    ["REST APIs", ["rest api", "restful api", "rest apis"]], ["GraphQL", ["graphql"]],
    ["Microservices", ["microservices", "microservice architecture"]],
    ["System Design", ["system design", "systems design"]],
    ["React", ["react.js", "reactjs", "react"]], ["Node.js", ["node.js", "nodejs"]],
    ["Angular", ["angular"]], ["Spring Boot", ["spring boot"]],
    ["AWS", ["amazon web services", "aws"]], ["Microsoft Azure", ["microsoft azure", "azure"]],
    ["Google Cloud", ["google cloud", "gcp"]], ["Docker", ["docker"]],
    ["Kubernetes", ["kubernetes", "k8s"]], ["Terraform", ["terraform", "infrastructure as code", "iac"]],
    ["Jenkins", ["jenkins"]], ["Ansible", ["ansible"]], ["Helm", ["helm"]],
    ["GitHub Actions", ["github actions"]], ["CI/CD", ["ci/cd", "continuous integration", "continuous delivery"]],
    ["Linux", ["linux"]], ["PowerShell", ["powershell"]], ["Bash", ["bash"]],
    ["Prometheus", ["prometheus"]], ["Grafana", ["grafana"]],
    ["Observability", ["observability"]], ["Monitoring", ["monitoring"]],
    ["Apache Spark", ["apache spark", "spark"]], ["Kafka", ["apache kafka", "kafka"]],
    ["Apache Airflow", ["apache airflow", "airflow"]], ["dbt", ["dbt"]],
    ["Snowflake", ["snowflake"]], ["Databricks", ["databricks"]],
    ["Redshift", ["redshift"]], ["BigQuery", ["bigquery"]], ["Hadoop", ["hadoop"]],
    ["Hive", ["apache hive", "hive"]], ["Apache Flink", ["apache flink", "flink"]],
    ["ETL/ELT", ["etl", "elt", "data pipeline", "data pipelines"]],
    ["Data Modeling", ["data modeling", "data modelling", "schema design"]],
    ["Data Warehousing", ["data warehouse", "data warehousing"]],
    ["Data Lakes", ["data lake", "data lakes"]], ["Data Quality", ["data quality"]],
    ["Machine Learning", ["machine learning", "ml models", "ml model"]],
    ["Deep Learning", ["deep learning"]], ["PyTorch", ["pytorch"]],
    ["TensorFlow", ["tensorflow"]], ["scikit-learn", ["scikit-learn", "sklearn"]],
    ["NLP", ["natural language processing", "nlp"]],
    ["Large Language Models", ["large language models", "large language model", "llm", "llms"]],
    ["Generative AI", ["generative ai", "genai", "gen ai"]],
    ["MLOps", ["mlops", "ml ops"]], ["MLflow", ["mlflow"]],
    ["Model Deployment", ["model deployment", "deploy models", "productionize models"]],
    ["Feature Engineering", ["feature engineering"]], ["Statistics", ["statistics", "statistical modeling", "statistical analysis"]],
    ["A/B Testing", ["a/b testing", "a/b tests", "ab testing"]],
    ["Pandas", ["pandas"]], ["NumPy", ["numpy"]], ["Tableau", ["tableau"]],
    ["Power BI", ["power bi"]], ["Looker", ["looker"]], ["Excel", ["excel"]],
    ["Data Visualization", ["data visualization", "visualization", "dashboards"]],
    ["Agile", ["agile"]], ["Scrum", ["scrum"]],
    ["Stakeholder Management", ["stakeholder management", "stakeholders"]],
    ["Communication", ["communication skills", "written communication", "verbal communication"]],
    ["Collaboration", ["cross-functional collaboration", "collaboration", "collaborative"]],
    ["Problem Solving", ["problem solving", "problem-solving"]],
  ];

  function evidenceSkills(master) {
    const skills = [...(master.base_skills || []), ...(master.user_confirmed_skills || [])];
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

  function extractSkillsFromText(text) {
    const haystack = String(text || "");
    const low = haystack.toLowerCase();
    const ranked = [];
    for (const [name, aliases] of JD_SKILL_ALIASES) {
      let score = 0;
      let first = Number.MAX_SAFE_INTEGER;
      for (const alias of aliases) {
        const term = alias.toLowerCase();
        let pos = low.indexOf(term);
        while (pos >= 0) {
          score += 10;
          first = Math.min(first, pos);
          const window = low.slice(Math.max(0, pos - 180), Math.min(low.length, pos + term.length + 180));
          if (/required|requirements|qualifications|preferred|must have|experience with|proficiency|knowledge of|familiarity with|skills/.test(window)) score += 6;
          pos = low.indexOf(term, pos + term.length);
        }
      }
      if (score > 0) ranked.push({ name, score, first });
    }
    ranked.sort((a, b) => b.score - a.score || a.first - b.first || a.name.localeCompare(b.name));
    return unique(ranked.map((x) => x.name)).slice(0, TOP_JD_SKILLS);
  }

  function hideOldGapLanguage() {
    const preview = document.getElementById("preview");
    if (!preview) return;
    for (const p of preview.querySelectorAll("p")) {
      if (clean(p.textContent).toLowerCase().startsWith("jd gaps not claimed:")) p.style.display = "none";
    }
  }

  function removePanel() {
    document.getElementById("jdSkillConfirmPanel")?.remove();
  }

  function chip(text, good = false) {
    const span = document.createElement("span");
    span.textContent = text;
    span.style.display = "inline-flex";
    span.style.alignItems = "center";
    span.style.padding = "7px 10px";
    span.style.border = good ? "1px solid rgba(74,222,128,.5)" : "1px solid rgba(148,163,184,.35)";
    span.style.borderRadius = "999px";
    span.style.background = good ? "rgba(22,101,52,.22)" : "transparent";
    return span;
  }

  function appendPasteFallback(panel, jid, topJd) {
    if (topJd.length >= TOP_JD_SKILLS) return;

    const wrap = document.createElement("div");
    wrap.style.marginTop = "16px";
    wrap.style.paddingTop = "14px";
    wrap.style.borderTop = "1px solid rgba(148,163,184,.25)";

    const heading = document.createElement("p");
    heading.innerHTML = `<strong>Need all 10? Paste the full JD here (${topJd.length}/10 extracted automatically)</strong>`;
    wrap.appendChild(heading);

    const help = document.createElement("p");
    help.className = "tiny muted";
    help.textContent = "Some company sites block automated reading. Paste the job description here and the extraction runs only in this browser; the JD text is not saved or uploaded.";
    wrap.appendChild(help);

    const textarea = document.createElement("textarea");
    textarea.rows = 7;
    textarea.placeholder = "Paste the complete job description / qualifications here…";
    textarea.style.width = "100%";
    textarea.style.boxSizing = "border-box";
    textarea.style.margin = "8px 0 10px";
    textarea.style.padding = "10px";
    textarea.style.borderRadius = "10px";
    textarea.style.border = "1px solid rgba(148,163,184,.35)";
    textarea.style.background = "rgba(15,23,42,.45)";
    textarea.style.color = "inherit";
    wrap.appendChild(textarea);

    const extractButton = document.createElement("button");
    extractButton.type = "button";
    extractButton.className = "secondary";
    extractButton.textContent = "Extract Top 10 JD skills";
    extractButton.addEventListener("click", () => {
      const extracted = extractSkillsFromText(textarea.value);
      if (!extracted.length) {
        help.textContent = "I could not identify skill terms in that text. Paste the full qualifications/responsibilities section and try again.";
        return;
      }
      const manualMap = readJsonStorage(MANUAL_JD_KEY, {});
      manualMap[jid] = extracted;
      localStorage.setItem(MANUAL_JD_KEY, JSON.stringify(manualMap));
      location.reload();
    });
    wrap.appendChild(extractButton);
    panel.appendChild(wrap);
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

    const sourceSkills = Array.isArray(job.top_jd_skills) && job.top_jd_skills.length
      ? job.top_jd_skills
      : (job.detected_skills || []);
    const topJd = unique(sourceSkills).slice(0, TOP_JD_SKILLS);

    const panel = document.createElement("section");
    panel.id = "jdSkillConfirmPanel";
    panel.setAttribute("aria-label", "Confirm JD skills you already know");
    panel.style.margin = "18px 0";
    panel.style.padding = "16px";
    panel.style.border = "1px solid rgba(148,163,184,.35)";
    panel.style.borderRadius = "12px";
    panel.style.background = "rgba(15,23,42,.35)";

    const title = document.createElement("h3");
    title.textContent = "Top JD skills: matched + confirm remaining";
    title.style.margin = "0 0 8px";
    panel.appendChild(title);

    if (!topJd.length) {
      const pending = document.createElement("p");
      pending.className = "tiny muted";
      pending.textContent = "This saved job does not yet contain readable JD skills. The scraper will retry the official job page; you can also paste the JD below now.";
      panel.appendChild(pending);
      appendPasteFallback(panel, jid, topJd);
      const metricGrid = resultCard.querySelector(".metricGrid");
      if (metricGrid?.nextSibling) resultCard.insertBefore(panel, metricGrid.nextSibling);
      else resultCard.appendChild(panel);
      return;
    }

    const evidence = evidenceSkills(master);
    const matched = topJd.filter((skill) => evidence.has(key(skill)));
    const missing = topJd.filter((skill) => !evidence.has(key(skill)));

    const note = document.createElement("p");
    note.className = "tiny muted";
    note.textContent = "These are extracted from this job description. Skills already found in your master are shown as matched. Check only skills you genuinely know from the remaining JD skills; confirmed skills are saved in this browser and added to Technical Skills.";
    panel.appendChild(note);

    const matchedTitle = document.createElement("p");
    matchedTitle.innerHTML = `<strong>Already matched from your master (${matched.length}/${topJd.length}):</strong>`;
    panel.appendChild(matchedTitle);

    const matchedWrap = document.createElement("div");
    matchedWrap.style.display = "flex";
    matchedWrap.style.flexWrap = "wrap";
    matchedWrap.style.gap = "8px";
    matchedWrap.style.margin = "8px 0 14px";
    if (matched.length) matched.forEach((skill) => matchedWrap.appendChild(chip(`✓ ${skill}`, true)));
    else matchedWrap.appendChild(chip("No Top-JD skill is in the master yet"));
    panel.appendChild(matchedWrap);

    if (missing.length) {
      const remainingTitle = document.createElement("p");
      remainingTitle.innerHTML = `<strong>Remaining JD skills — tick the ones you already know (${missing.length}):</strong>`;
      panel.appendChild(remainingTitle);

      const options = document.createElement("div");
      options.style.display = "flex";
      options.style.flexWrap = "wrap";
      options.style.gap = "10px";
      options.style.margin = "10px 0 12px";

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
        latestMaster.user_confirmed_skills = unique([...(latestMaster.user_confirmed_skills || []), ...selected]);

        localStorage.setItem(MASTER_KEY, JSON.stringify(latestMaster));
        localStorage.setItem(CONFIRMED_KEY, JSON.stringify([...existing.values()]));
        location.reload();
      });
      panel.appendChild(button);
    } else {
      const done = document.createElement("p");
      done.className = "tiny muted";
      done.textContent = "All extracted Top-JD skills are already confirmed in your master.";
      panel.appendChild(done);
    }

    appendPasteFallback(panel, jid, topJd);

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
      if (mutations.some((mutation) => mutation.type === "attributes" && mutation.attributeName === "class")) schedule();
    });
    observer.observe(resultCard, { attributes: true, attributeFilter: ["class"] });
  }

  window.addEventListener("load", schedule);
  schedule();
})();
