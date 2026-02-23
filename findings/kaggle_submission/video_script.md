# Video Script — MedGemma Impact Challenge

**Total Duration:** 3:00 | **Speakers:** Radu, Ayush, Aman

---

## RADU (0:00–1:00) — The Problem & Clinical Foundation

**[0:00–0:15] Self-Introduction**

> Hi, I'm Radu Alexa, a board-certified uro-oncologist working in Germany.

**[0:15–0:35] The Problem**

> Besides the day-to-day workload — operations, consulting patients, ward visits — we have to organise and present around 30 to 50 cases in our tumor board on a weekly basis. This is a lot of work for us: from correcting typos, to ensuring text fluidity, to searching for and selecting the most appropriate guideline-based recommendation for each case. To reduce the amount of time for this task, we thought as a team about introducing LLMs into the workflow.

**[0:35–0:50] The Dataset**

> In order to see if LLMs are suitable for our problem, we developed a database of 69 renal cell carcinoma cases. The cases cover all disease and therapy stages based on the German guidelines. Each case is fully structured: patient demographics, ECOG performance status, TNM staging, IMDC risk, imaging findings, and prior therapies. We then transformed the text into a structured JSON format. Here is an example of what a case looks like.

*[Screen: show case detail page on the website or JSON structure]*

**[0:50–1:00] Evaluation**

> I personally reviewed every AI output — 414 model predictions and 828 judge evaluations. That's 1,242 expert reviews, 100% coverage. Let me hand over to Ayush to explain the technical details.

*[Screen: briefly show the review interface on medical-review-site.vercel.app]*

---

## AYUSH (1:00–1:50) — Models & Technical Pipeline

**[1:00–1:15] Introduction**

> Hi, I'm Ayush Nangia, an AI researcher currently working from India. I built the end-to-end inference and evaluation pipeline for this project.

**[1:15–1:35] Pipeline & Infrastructure**

> Each clinical case in structured JSON gets embedded into a German-language prompt along with the complete IMDC-stratified therapy flowchart from the guidelines. We run 6 models through Modal's vLLM on H100 GPUs, using Pydantic schemas for structured output and a fixed seed for full reproducibility. I also built the production web application in Next.js with Supabase, deployed on Vercel — this is where Radu conducted all his reviews.

*[Screen: show pipeline architecture diagram]*

**[1:35–1:50] Model Results**

> We tested 6 models: MedGemma 27B, Gemma 3 27B and 4B, OLMo 32B Instruct and Think, and Meditron3 7B. MedGemma 27B was the clear winner — 75.4% of its recommendations were judged clinically acceptable by Radu, with a quality score of 6.1 out of 9. Now Aman will explain the judge system and our key findings.

*[Screen: show model comparison chart]*

---

## AMAN (1:50–3:00) — Judge System & Future

**[1:50–2:05] Introduction**

> Hi, I am Aman Gokrani, currently working as an AI researcher and consultant at various organizations. Previously, I worked at Microsoft Health AI.

**[2:05–2:25] Judge Architecture**

> My key contribution is the novel use of MedGemma as a structured medical judge — a task it was never trained for. Using the same German prompt framework, the judge evaluates each model's prediction across four scoring dimensions: semantic match and clinical appropriateness at 40% weight each, and reasoning quality at 20%. This is all enforced through structured JSON output.

*[Screen: show judge scoring formula and example output]*

**[2:25–2:45] Judge Results & Bias Discovery**

> MedGemma as judge achieved substantial agreement with Radu — Cohen's kappa of 0.675, with 84.5% concordance. But here's our most important finding: MedGemma exhibits statistically significant self-judging bias. When evaluating its own predictions, it scores them higher by 0.082 points on average, confirmed at p equals 0.017. This is a critical insight for responsible AI deployment.

*[Screen: show bias chart and agreement metrics]*

**[2:45–3:00] Future Development**

> Going forward, we plan to add more physician reviewers for inter-rater reliability, expand to prostate, urothelial, and testicular cancers, and potentially fine-tune MedGemma on our validated German oncology dataset. Our goal is a reliable AI co-pilot for tumor board preparation. Thank you.

*[Screen: show website with URL and team]*

---

**End of Script**

- **Radu:** ~230 words (~60 seconds)
- **Ayush:** ~190 words (~50 seconds)
- **Aman:** ~210 words (~55 seconds)
- **Total:** ~630 words (well within 3-minute limit at natural speaking pace)
