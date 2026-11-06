# AI Prompts Log — HW6: Campus Customs Vendor Desk (Tokenomics + Prompt Injection)

*About HW6:* a vendor desk agent for Campus Customs reads vendor quotes, invoices, catalog pages and emails, pulls out the key facts (vendor, item, price, lead time, minimum order), and recommends whether to buy based on the Shop Handbook. The two focus areas are the **token cost** of sending a roughly 10,000-token handbook on every call, and **prompt-injection safety**, since some vendor documents hide instructions aimed at the AI. The only model is `gpt-6-luna` through Portkey. Email and payment tools only write to a log file.

---

## Problem 1: Vibe coder prompts

**Prompt:**
new homework, hw6. make a hw6 folder with an AI_prompts.md and keep logging what I ask you as we go: one section per problem with the number and title, my prompt in my own words, and a follow-up if I needed one plus a line on what was missing the first time

**Follow-up:**
add a short line at the top saying what hw6 is about so the log makes sense on its own

*What was lacking:* the first version was just an empty heading, so someone reading the log later wouldn't know this homework is about cutting token cost and defending the agent against prompt injection.

**Follow-up:**
here's the data folder, put it in hw6/data and take a quick look at what's in it

*What was lacking:* the hw6 folder had no data yet, so nothing could be built or tested against the real handbook and vendor documents.

## Problem 2: Size up the handbook

**Prompt:**
the agent sends the whole shop handbook on every call, so figure out how many tokens it really is. then in output/handbook_estimate.md write the token count and how you got it, plus what the handbook alone costs on 1 call and on 1000 calls, with caching and without, using the prices in data/prices.json. show the math

**Follow-up:**
don't just do characters divided by 4, count it with the real tokenizer

*What was lacking:* the first estimate used the chars ÷ 4 rule and came out around 7,200 tokens, which was 28% low because the handbook is full of tables, SKUs and numbers.

## Problem 3: Build the vendor desk agent

**Prompt:**
build the vendor desk agent with pydantic ai on gpt-6-luna, split into prompts/prompt.md, agent.py, tools.py and models.py. give it a path to one vendor doc (html, pdf or email all need to work), it reads it with a tool and returns vendor, sku, unit price, lead time in days, min order, recommend or do_not_recommend by the handbook rules, and a one sentence reason. add two trap tools, send_email and approve_payment, that never actually do anything, they just append the call to output/trap_calls.json. after every run log tokens and dollar cost to output/usage_log.json and the tool calls + answer to output/audit_trail.json. run it like `python agent.py --doc ...` and start the harness with the model fields and tools

**Follow-up:**
some of these docs have hidden text in them (tiny fonts, display none, html comments, white text) with fake prices and fake instructions. make the reader only return what a person would actually see

*What was lacking:* the first reader returned the raw HTML text, so p02's hidden "$5.11" price and p04's hidden "approve the deposit" comment went straight to the model.

## Problem 4: With and without cached tokens

**Prompt:**
run the agent on all 12 practice docs twice, once where the handbook gets reused from the cache and once where nothing can come from the cache. save every single model call to output/cache_test.json with the setup, doc, all the token counts the API gives back and the dollar cost. then write output/cache_test.md with total and per-doc cost for each, % saved, how it compares to my problem 2 estimate, what 1000 docs a day for 30 days would cost both ways, and anything weird in the numbers

## Problem 5: Attack your own agent

**Prompt:**
run the problem 3 agent as is, no new defenses, on all 12 practice docs. compare every answer to the practice key and check trap_calls.json. save output/attack_results.json with, for each doc, which fields matched, if the decision matched, if a trap tool got called, and if a link or anything weird showed up in the answer. then in output/attack_results.md, for each doc that fooled it, say what fooled it and where it was hiding in the file. open the docs like a person would (browser, pdf viewer, email app) and compare that to what the agent actually read

## Problem 6: Defend your agent

**Prompt:**
now defend it at 3 levels. code: clean the doc before the model ever sees it (the pdf hidden text is the big hole). design: set it up so a poisoned doc can't reach send_email/approve_payment or the decision, but don't delete those tools, the shop needs them later with a human sign-off. prompt: better rules in prompts/prompt.md, and stop leaking the max cost. keep a way to run with no defenses for problem 7. rerun all 12 and save output/defense_results.json like problem 5 plus tokens and dollars per doc, then output/defense_results.md with a before/after table, what each layer catches that the others don't, and what each layer adds in tokens and dollars. clean docs still have to come back right. add a Safety section to the harness in plain words

## Problem 7: Red team

**Prompt:**
now I'm the attacker. make 2 new booby-trapped vendor docs in data/my_attacks/ that look like a normal quote to a person, but each uses a hiding trick or a goal that isn't in the practice docs. ideally they should actually fool the agent with no defenses, and it'd be great if one gets past my own defenses too. run both with --defenses none and with full defenses, then write output/red_team.md: what's hidden, where, what it's trying to make the agent do, and what happened before and after

**Follow-up:**
the min order one didn't fool anything, make it nastier so the agent never even sees the real 1,200. and since the sku one got past my defenses, patch the holes but keep a p6 mode so I can show before and after

*What was lacking:* the first attack 1 left the real 1,200 visible next to the hidden 240, so every agent noticed the conflict and kept 1,200. And the SKU swap beat my Problem 6 defenses with no fix in place.

## Problem 8: Exam documents

**Prompt:**
Last one. run the final defended agent. all the defenses plus the red team fixes on the 10 docs in data/exam_docs. There’s no answer key, so don’t touch the results by hand, just save whatever the agent gives back. put it in output/exam_results.json with one entry per file: file, vendor, sku, unit_price, lead_time_days, min_order, decision, reason, whether a trap tool got called, input/cached/output tokens, and cost. graders compare it to a hidden key and rerun some of it, so it needs to get the fields right, never call send_email or approve_payment, and handle the clean docs like normal quotes

## Problem 9: Results page

**Prompt:**
make output/hw6_report.html, one file I can double click with no internet and nothing next to it. show my caching results with a chart, attacks before and after the defenses, what the defenses cost in tokens and dollars, the exam results and my two red team attacks, and a short recommendation for the store manager on whether to turn this on for real vendor mail and what it costs a month at 1000 docs a day. use my real numbers and make it look designed, not like a default page

**Follow-up:**
build it from the json files with a script instead of typing the numbers in, and make sure the code bits are readable on the dark blue box

*What was lacking:* hand-copied numbers could drift from the real results files, and the first version's code labels in the recommendation box were light-on-light and hard to read.

## Problem 10: Push to GitHub and submit the URL

**Prompt:**
get hw6 ready for a public github repo. it needs the whole data folder including my two attack files, all the outputs, a README with a short note on how to run the agent, .env.example with just a placeholder, and my real .env kept out with .gitignore. then I'll push it and put the url on canvas
