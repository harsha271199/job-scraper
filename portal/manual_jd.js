(() => {
  const MANUAL_JOB_ID = "manual-local";
  const MANUAL_JOB_KEY = "jobScraper.manualJob.v1";
  const MANUAL_JD_SKILLS_KEY = "jobScraper.manualJdSkills.v1";
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

  const JD_SKILLS = [
    ["Python", ["python"]], ["JavaScript", ["javascript", "node.js", "nodejs"]],
    ["TypeScript", ["typescript"]], ["Java", ["java"]], ["C++", ["c++"]],
    ["SQL", ["sql"]], ["PostgreSQL", ["postgresql", "postgres"]],
    ["MySQL", ["mysql"]], ["MongoDB", ["mongodb"]], ["NoSQL", ["nosql"]],
    ["REST APIs", ["rest api", "restful api", "rest apis"]], ["GraphQL", ["graphql"]],
    ["Microservices", ["microservices", "microservice architecture"]],
    ["System Design", ["system design", "systems design"]],
    ["AWS", ["amazon web services", "aws"]], ["Microsoft Azure", ["microsoft azure", "azure"]],
    ["Google Cloud", ["google cloud", "gcp"]], ["Docker", ["docker"]],
    ["Kubernetes", ["kubernetes", "k8s"]], ["Terraform", ["terraform", "infrastructure as code"]],
    ["GitHub Actions", ["github actions"]], ["CI/CD", ["ci/cd", "continuous integration", "continuous delivery"]],
    ["Linux", ["linux"]], ["PowerShell", ["powershell"]], ["Bash", ["bash"]],
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
    ["Generative AI", ["generative ai", "genai", "gen ai"]], ["MLOps", ["mlops", "ml ops"]],
    ["Pandas", ["pandas"]], ["NumPy", ["numpy"]], ["Tableau", ["tableau"]],
    ["Power BI", ["power bi"]], ["Looker", ["looker"]], ["Excel", ["excel"]],
    ["Data Visualization", ["data visualization", "visualization", "dashboards"]],
    ["Agile", ["agile"]], ["Scrum", ["scrum"]],
    ["Stakeholder Management", ["stakeholder management", "stakeholders"]],
    ["Communication", ["communication skills", "written communication", "verbal communication"]],
    ["Collaboration", ["cross-functional collaboration", "collaboration", "collaborative"]],
    ["Problem Solving", ["problem solving", "problem-solving"]]
  ];

  function readJsonStorage(storageKey, fallback) {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function readManualJob() {
    return readJsonStorage(MANUAL_JOB_KEY, null);
  }

  function clearManualSkillOverlay() {
    const map = readJsonStorage(MANUAL_JD_SKILLS_KEY, {});
    if (map && typeof map === "object" && MANUAL_JOB_ID in map) {
      delete map[MANUAL_JOB_ID];
      localStorage.setItem(MANUAL_JD_SKILLS_KEY, JSON.stringify(map));
    }
  }

  function extractSkillsFromText(text) {
    const low = String(text || "").toLowerCase();
    const ranked = [];
    for (const [name, aliases] of JD_SKILLS) {
      let score = 0;
      let first = Number.MAX_SAFE_INTEGER;
      for (const alias of aliases) {
        const term = alias.toLowerCase();
        let pos = low.indexOf(term);
        while (pos >= 0) {
          score += 10;
          first = Math.min(first, pos);
          const around = low.slice(Math.max(0, pos - 200), Math.min(low.length, pos + term.length + 200));
          if (/required|requirements|qualification|qualifications|preferred|must have|experience with|proficiency|knowledge of|familiarity with|skills|responsibilities/.test(around)) score += 6;
          pos = low.indexOf(term, pos + term.length);
        }
      }
      if (score > 0) ranked.push({ name, score, first });
    }
    ranked.sort((a, b) => b.score - a.score || a.first - b.first || a.name.localeCompare(b.name));
    return unique(ranked.map((x) => x.name)).slice(0, TOP_JD_SKILLS);
  }

  function classifyProfile(title, jdText) {
    const text = `${title || ""} ${jdText || ""}`.toLowerCase();
    if (/data engineer|data platform|etl|elt|airflow|spark|data warehouse|data lake|data pipeline/.test(text)) return "data-engineering";
    if (/machine learning engineer|ml engineer|data scientist|machine learning|deep learning|pytorch|tensorflow|nlp|large language model|\bllm\b/.test(text)) return "machine-learning";
    if (/site reliability|\bsre\b|devops|cloud engineer|platform engineer|infrastructure engineer|terraform|kubernetes/.test(text)) return "cloud-devops";
    if (/data analyst|business intelligence|analytics engineer|reporting analyst|tableau|power bi|looker/.test(text)) return "data-analytics";
    if (/software engineer|software developer|backend|front[- ]?end|full[- ]?stack|web developer|microservices|system design/.test(text)) return "software-engineering";
    return "general-technical";
  }

  function guessTitle(text) {
    const lines = String(text || "").split(/\r?\n/).map(clean).filter(Boolean).slice(0, 12);
    const role = lines.find((line) => line.length <= 120 && /engineer|developer|scientist|analyst|architect|specialist|administrator|consultant/.test(line.toLowerCase()));
    return role || "Custom Job Description";
  }

  function companyFromUrl(url) {
    try {
      const host = new URL(url).hostname.replace(/^www\./, "");
      const generic = ["jobs.lever.co", "boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.ashbyhq.com", "myworkdayjobs.com"];
      if (generic.some((x) => host.endsWith(x))) return "Custom Job";
      const first = host.split(".")[0];
      return first ? first.charAt(0).toUpperCase() + first.slice(1) : "Custom Job";
    } catch {
      return "Custom Job";
    }
  }

  function normalizeJobUrl(raw) {
    const text = clean(raw);
    if (!text) return "";
    const url = new URL(text);
    if (!/^https?:$/.test(url.protocol)) throw new Error("Use an http:// or https:// job link.");
    return url.href;
  }

  function makeManualJob({ jdText, jobUrl = "", title = "", company = "", source = "manual-paste" }) {
    const skills = extractSkillsFromText(jdText);
    const resolvedTitle = clean(title) || guessTitle(jdText);
    const resolvedCompany = clean(company) || companyFromUrl(jobUrl);
    const profile = classifyProfile(resolvedTitle, jdText);
    return {
      id: MANUAL_JOB_ID,
      company: resolvedCompany,
      title: resolvedTitle,
      location: "Manual JD",
      apply_url: jobUrl,
      official_url: jobUrl,
      posted: "Manual input",
      profile,
      detected_skills: skills,
      verified_skills: [],
      unverified_skills: skills,
      signal_terms: skills,
      signal_source: source,
      captured_at: new Date().toISOString(),
      manual_input: true
    };
  }

  function placeholderJob() {
    return {
      id: MANUAL_JOB_ID,
      company: "Custom Job",
      title: "Paste a JD or job link below",
      location: "Private browser mode",
      apply_url: "",
      official_url: "",
      posted: "Manual input",
      profile: "general-technical",
      detected_skills: [],
      verified_skills: [],
      unverified_skills: [],
      signal_terms: [],
      signal_source: "manual-empty",
      manual_input: true
    };
  }

  function activateManualJob(job) {
    localStorage.setItem(MANUAL_JOB_KEY, JSON.stringify(job));
    clearManualSkillOverlay();
    const target = new URL(location.href);
    target.searchParams.set("job", MANUAL_JOB_ID);
    location.href = target.href;
  }

  const initialUrl = new URL(location.href);
  if (!initialUrl.searchParams.get("job")) {
    initialUrl.searchParams.set("job", MANUAL_JOB_ID);
    history.replaceState(null, "", initialUrl.href);
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const requestUrl = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
    const activeJobId = new URLSearchParams(location.search).get("job");
    if (!String(requestUrl).includes("job_signals.json") || activeJobId !== MANUAL_JOB_ID) {
      return originalFetch(...args);
    }

    let data = { version: 1, jobs: {} };
    let status = 200;
    let statusText = "OK";
    try {
      const response = await originalFetch(...args);
      status = response.status;
      statusText = response.statusText;
      if (response.ok) data = await response.clone().json();
    } catch {
      // Manual mode can still work if the public feed request itself is unavailable.
    }
    if (!data || typeof data !== "object") data = { version: 1, jobs: {} };
    if (!data.jobs || typeof data.jobs !== "object") data.jobs = {};
    data.jobs[MANUAL_JOB_ID] = readManualJob() || placeholderJob();
    return new Response(JSON.stringify(data), {
      status: status >= 200 && status < 400 ? status : 200,
      statusText: status >= 200 && status < 400 ? statusText : "OK",
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  };

  async function readJobLink(jobUrl) {
    const response = await originalFetch(jobUrl, { cache: "no-store", mode: "cors" });
    if (!response.ok) throw new Error(`Job page returned HTTP ${response.status}.`);
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    for (const node of doc.querySelectorAll("script,style,noscript,svg")) node.remove();
    const text = clean(doc.body?.innerText || doc.body?.textContent || "");
    if (text.length < 250) throw new Error("The job page did not expose enough readable description text.");
    const title = clean(
      doc.querySelector('meta[property="og:title"]')?.content ||
      doc.querySelector("h1")?.textContent ||
      doc.title ||
      ""
    );
    return { text, title };
  }

  function setStatus(message, isError = false) {
    const el = document.getElementById("manualJdStatus");
    if (!el) return;
    el.textContent = message;
    el.className = isError ? "tiny manualStatus errorText" : "tiny muted manualStatus";
  }

  function setupManualUi() {
    const jd = document.getElementById("manualJdText");
    const link = document.getElementById("manualJobLink");
    const title = document.getElementById("manualJobTitle");
    const company = document.getElementById("manualJobCompany");
    const pasteButton = document.getElementById("manualTailorPaste");
    const linkButton = document.getElementById("manualTailorLink");
    const clearButton = document.getElementById("manualClear");
    if (!jd || !link || !pasteButton || !linkButton) return;

    const saved = readManualJob();
    if (saved) {
      link.value = saved.apply_url || "";
      title.value = saved.title === "Custom Job Description" ? "" : (saved.title || "");
      company.value = saved.company === "Custom Job" ? "" : (saved.company || "");
    }

    pasteButton.addEventListener("click", () => {
      try {
        const text = jd.value.trim();
        if (text.length < 80) throw new Error("Paste the full JD or at least the responsibilities/qualifications section.");
        const jobUrl = link.value.trim() ? normalizeJobUrl(link.value) : "";
        const job = makeManualJob({
          jdText: text,
          jobUrl,
          title: title.value,
          company: company.value,
          source: "manual-paste"
        });
        setStatus(`Found ${job.detected_skills.length} top JD skills. Tailoring your resume now…`);
        activateManualJob(job);
      } catch (err) {
        setStatus(err.message, true);
      }
    });

    linkButton.addEventListener("click", async () => {
      try {
        const jobUrl = normalizeJobUrl(link.value);
        setStatus("Reading the job page in your browser…");
        const fetched = await readJobLink(jobUrl);
        const job = makeManualJob({
          jdText: fetched.text,
          jobUrl,
          title: title.value || fetched.title,
          company: company.value,
          source: "manual-link"
        });
        setStatus(`Found ${job.detected_skills.length} top JD skills. Tailoring your resume now…`);
        activateManualJob(job);
      } catch (err) {
        setStatus(`That site blocked browser reading or did not expose the JD. Paste the JD below instead. ${err.message}`, true);
      }
    });

    clearButton?.addEventListener("click", () => {
      localStorage.removeItem(MANUAL_JOB_KEY);
      clearManualSkillOverlay();
      jd.value = "";
      link.value = "";
      title.value = "";
      company.value = "";
      setStatus("Manual JD cleared from this browser.");
      if (new URLSearchParams(location.search).get("job") === MANUAL_JOB_ID) location.reload();
    });

    const activeManual = new URLSearchParams(location.search).get("job") === MANUAL_JOB_ID;
    if (activeManual && saved) {
      setStatus(`Manual job active: ${saved.detected_skills?.length || 0} JD skills extracted. The resume below uses the same verified-facts tailoring flow as GitHub job links.`);
    } else if (activeManual && !saved) {
      setStatus("Paste a JD or try a job link to generate a tailored resume for a role that is not in the GitHub feed.");
      setTimeout(() => document.getElementById("resultCard")?.classList.add("hidden"), 0);
    }

    if (activeManual) {
      setTimeout(() => {
        const hasApply = !!readManualJob()?.apply_url;
        const open = document.getElementById("openApply");
        const combo = document.getElementById("downloadApply");
        if (open) open.classList.toggle("hidden", !hasApply);
        if (combo) combo.classList.toggle("hidden", !hasApply);
      }, 0);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setupManualUi);
  else setupManualUi();
})();
