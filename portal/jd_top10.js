(() => {
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

  const PROFILE_CANDIDATES = {
    "machine-learning": [
      "Python", "SQL", "Machine Learning", "PyTorch", "Deep Learning",
      "scikit-learn", "Pandas", "NumPy", "NLP", "Large Language Models",
      "MLOps", "Model Deployment", "Statistics", "Experimentation",
      "AWS", "Microsoft Azure", "Docker", "Kubernetes", "Apache Spark"
    ],
    "data-engineering": [
      "Python", "SQL", "ETL/ELT", "Apache Spark", "Kafka", "Apache Airflow",
      "dbt", "Data Modeling", "Data Warehousing", "AWS", "Microsoft Azure",
      "Snowflake", "Databricks", "PostgreSQL", "Redshift", "BigQuery",
      "Docker", "Kubernetes", "Terraform", "REST APIs"
    ],
    "cloud-devops": [
      "Microsoft Azure", "AWS", "Terraform", "Docker", "Kubernetes",
      "PowerShell", "Bash", "Linux", "CI/CD", "GitHub Actions", "Jenkins",
      "Ansible", "Helm", "Prometheus", "Grafana", "Monitoring",
      "Observability", "Networking", "Incident Response", "Python"
    ],
    "software-engineering": [
      "Python", "JavaScript", "TypeScript", "Java", "SQL", "REST APIs",
      "PostgreSQL", "Microservices", "System Design", "Testing", "Docker",
      "Kubernetes", "AWS", "Microsoft Azure", "GitHub Actions", "CI/CD",
      "Node.js", "React", "Git", "Linux"
    ],
    "data-analytics": [
      "SQL", "Excel", "Python", "Tableau", "Power BI", "BigQuery",
      "PostgreSQL", "Pandas", "NumPy", "Statistics", "Data Visualization",
      "Business Intelligence", "Data Modeling", "ETL/ELT", "A/B Testing",
      "Data Quality", "Dashboarding", "Analytics"
    ],
    "general-technical": [
      "Python", "SQL", "AWS", "Microsoft Azure", "Docker", "Kubernetes",
      "Terraform", "GitHub Actions", "REST APIs", "PostgreSQL", "Linux",
      "CI/CD", "Git", "JSON", "Bash"
    ]
  };

  function buildTop10(job) {
    const explicit = unique(job.top_jd_skills || job.detected_skills || []);
    const fromSignals = unique((job.signal_terms || []).map((term) => SIGNAL_TO_SKILL[key(term)]).filter(Boolean));
    const profile = job.profile || "general-technical";
    const role = PROFILE_CANDIDATES[profile] || PROFILE_CANDIDATES["general-technical"];
    const top = unique([...explicit, ...fromSignals, ...role]).slice(0, TOP_JD_SKILLS);
    return top;
  }

  function augmentFeed(data) {
    if (!data || typeof data !== "object" || !data.jobs || typeof data.jobs !== "object") return data;
    for (const job of Object.values(data.jobs)) {
      if (!job || typeof job !== "object") continue;
      const top = buildTop10(job);
      if (!top.length) continue;
      job.top_jd_skills = top;
      job.detected_skills = unique([...(job.detected_skills || []), ...top]);
      job.effective_skills = unique([...(job.effective_skills || []), ...top]);
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
