(() => {
  const TOP_JD_SKILLS = 10;
  const MANUAL_JD_KEY = "jobScraper.manualJdSkills.v1";

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

  const SIGNAL_TO_SKILL = {
    "data pipeline": "ETL/ELT",
    "data pipelines": "ETL/ELT",
    "etl": "ETL/ELT",
    "elt": "ETL/ELT",
    "data warehouse": "Data Warehousing",
    "data lake": "Data Lakes",
    "distributed systems": "Distributed Systems",
    "streaming": "Streaming Systems",
    "kafka": "Kafka",
    "api": "REST APIs",
    "rest api": "REST APIs",
    "microservices": "Microservices",
    "cloud": "Cloud Computing",
    "infrastructure as code": "Terraform",
    "iac": "Terraform",
    "ci/cd": "CI/CD",
    "observability": "Observability",
    "monitoring": "Monitoring",
    "incident response": "Incident Response",
    "root cause analysis": "Root Cause Analysis",
    "data quality": "Data Quality",
    "data modeling": "Data Modeling",
    "schema design": "Data Modeling",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "llm": "Large Language Models",
    "analytics": "Analytics",
    "dashboard": "Data Visualization",
    "business intelligence": "Business Intelligence",
    "sql": "SQL",
    "python": "Python"
  };

  function readManualMap() {
    try {
      return JSON.parse(localStorage.getItem(MANUAL_JD_KEY) || "{}") || {};
    } catch {
      return {};
    }
  }

  function buildTop10(job, manualSkills = []) {
    const explicit = unique(job.top_jd_skills || []);
    const detected = unique(job.detected_skills || []);
    const fromSignals = unique((job.signal_terms || []).map((term) => SIGNAL_TO_SKILL[key(term)]).filter(Boolean));
    return unique([...manualSkills, ...explicit, ...detected, ...fromSignals]).slice(0, TOP_JD_SKILLS);
  }

  function augmentFeed(data) {
    if (!data || typeof data !== "object" || !data.jobs || typeof data.jobs !== "object") return data;
    const manual = readManualMap();
    for (const [jid, job] of Object.entries(data.jobs)) {
      if (!job || typeof job !== "object") continue;
      const top = buildTop10(job, manual[jid] || []);
      if (!top.length) continue;
      job.top_jd_skills = top;
      job.detected_skills = unique([...top, ...(job.detected_skills || [])]);
      job.effective_skills = unique([...top, ...(job.effective_skills || [])]);
    }
    return data;
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    try {
      const requestUrl = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (!String(requestUrl).includes("job_signals.json") || !response.ok) return response;
      const data = augmentFeed(await response.clone().json());
      return new Response(JSON.stringify(data), {
        status: response.status,
        statusText: response.statusText,
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    } catch {
      return response;
    }
  };
})();
