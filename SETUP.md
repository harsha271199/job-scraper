# Setup Guide — Get Running in 30 Minutes

## Step 1: Fork or create GitHub repo
1. Go to github.com → New Repository
2. Name it: JobScraper (make it PRIVATE)
3. Upload all these files

## Step 2: Set up Telegram Bot (free, 5 min)
1. Open Telegram → search for @BotFather
2. Send: /newbot
3. Follow prompts → you get a BOT_TOKEN like: 7234567890:AAF...
4. Search for @userinfobot → send it /start → it gives your CHAT_ID

## Step 3: Add secrets to GitHub
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add secret: TELEGRAM_BOT_TOKEN = (your token from step 2)
3. Add secret: TELEGRAM_CHAT_ID = (your chat id from step 2)

## Step 4: Enable GitHub Actions
1. Go to Actions tab in your repo
2. Click "I understand my workflows, go ahead and enable them"
3. Click "Job Scraper — Every Hour" → Run workflow (test it now)

## Step 5: Watch Telegram
Within 2-3 minutes you'll get your first batch of jobs on your phone.

## Adding more companies
Edit companies.csv and add rows like:
  CompanyName,greenhouse,https://boards.greenhouse.io/companyname
  CompanyName,lever,https://jobs.lever.co/companyname
  CompanyName,ashby,https://jobs.ashbyhq.com/companyname
  CompanyName,workday,https://company.wd5.myworkdayjobs.com/en-US/SiteName

## How to find a company's ATS URL
1. Go to company careers page
2. Click any job → look at the URL
3. If it has "greenhouse.io" → use greenhouse platform
4. If it has "lever.co" → use lever platform
5. If it has "myworkdayjobs.com" → use workday platform
6. If it has "ashbyhq.com" → use ashby platform

## Costs
- GitHub: FREE (2,000 Actions minutes/month free = plenty for hourly runs)
- Telegram: FREE
- Total: $0
