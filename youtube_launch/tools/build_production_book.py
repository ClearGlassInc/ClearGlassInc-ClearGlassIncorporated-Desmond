#!/usr/bin/env python3
"""Validate the canonical YouTube catalog and render its production book."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'content_catalog.json'
OUTPUT=ROOT/'generated'/'PRODUCTION_BOOK.md'
REQUIRED={"long_form":24,"shorts":60,"community_posts":12,"livestreams":13}

def load():
    data=json.loads(CATALOG.read_text())
    errors=[]
    for key,count in REQUIRED.items():
        if len(data.get(key,[]))!=count:
            errors.append(f"{key}: expected {count}, got {len(data.get(key,[]))}")
    ids=[]
    for key in REQUIRED:
        for item in data[key]:
            ids.append(item.get('id'))
    if len(ids)!=len(set(ids)):
        errors.append('IDs must be unique')
    required_long={'id','week','pillar','title','title_alternatives','thumbnail','hook','search_query','viewer_intent','related_service','lead_magnet','steps','case','cta'}
    for v in data.get('long_form',[]):
        missing=required_long-set(v)
        if missing:
            errors.append(f"{v.get('id')}: missing {sorted(missing)}")
        if len(v.get('title_alternatives',[]))!=2:
            errors.append(f"{v.get('id')}: requires exactly two alternative titles")
        if len(v.get('thumbnail','').split())>4:
            errors.append(f"{v.get('id')}: thumbnail exceeds four words")
        if len(v.get('steps',[]))!=5:
            errors.append(f"{v.get('id')}: requires five outline steps")
    for s in data.get('shorts',[]):
        if len(s.get('title_alternatives',[]))!=2:
            errors.append(f"{s.get('id')}: requires exactly two alternative titles")
        if len(s.get('thumbnail','').split())>4:
            errors.append(f"{s.get('id')}: thumbnail exceeds four words")
    if errors:
        raise SystemExit('\n'.join(errors))
    return data

def slug(s):
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def utm(item,placement):
    pillar=slug(item.get('pillar','short'))
    asset=item.get('lead_magnet','resources')
    return f"https://www.clearglassinc.com/resources/{asset}?utm_source=youtube&utm_medium=organic_video&utm_campaign=yt_launch_90d&utm_content={item['id'].lower()}_{placement}&utm_term={pillar}"

def long_script(v):
    steps=v['steps']
    case=v['case']
    paragraphs=[
      f"[COLD OPEN — DIRECT TO CAMERA] {v['hook']} On screen: ‘{v['thumbnail']}’. [Hold one beat.] By the end of this field guide, you will have five controls, one worked example, and a next action you can document.",
      f"[SOURCE CARD] Search intent: {v['viewer_intent']} This episode is educational, not legal, investment, or individualized security advice. The evidence links and correction path are in the description. I’m Desmond Otieno Odhiambo, founder of ClearGlassInc. Our method is claim, evidence, decision, control.",
      f"[CLAIM] The operating problem is not a lack of tools. It is a lack of a visible decision boundary. We are going to examine ‘{v['search_query']}’ without hype and separate what we can verify from what still needs an owner or evidence.",
      f"[CONTROL 1 — DIAGRAM] {steps[0]}. Start here because an incomplete inventory creates false confidence. Put the owner, system, evidence source, and review date beside the item. If the answer is unknown, write ‘unknown’; do not turn uncertainty into a pass.",
      f"[CONTROL 2 — SCREEN CAPTURE] {steps[1]}. Apply this at the boundary, before information or authority moves. Use a fictional record on screen. The audience should see the allowed path, the denied path, and the escalation path.",
      f"[CONTROL 3 — WHITEBOARD] {steps[2]}. This is where convenience often becomes uncontrolled authority. Write who can propose, who can approve, what can execute, the maximum scope, and how the action is reversed.",
      f"[MIDPOINT RESET] Here is the worked example. {case} Pause on each transition and label the scene DEMO or SIMULATION. No real secrets, targets, balances, customer records, or privileged screens may appear.",
      f"[CONTROL 4 — EVIDENCE PANEL] {steps[3]}. A verbal assurance is not equivalent to current evidence. Capture the source, version, date, scope, and reviewer. If the source changes, expire the decision and review it again.",
      f"[CONTROL 5 — CHECKLIST] {steps[4]}. A control without an owner, alert, recovery path, and test cadence will decay. Set the smallest useful review interval and define the condition that stops or rolls back the process.",
      "[OBJECTION] You may be thinking this is too much process for a small team. The answer is not a larger committee. Use one page, one accountable owner, and a risk-based approval boundary. Keep low-risk work fast; make consequential work explicit and auditable.",
      f"[RECAP — FIVE CARDS] One: {steps[0]}. Two: {steps[1]}. Three: {steps[2]}. Four: {steps[3]}. Five: {steps[4]}. Screenshot this only after checking the linked, maintained version in the description.",
      f"[CTA — DIRECT TO CAMERA] {v['cta']} The primary link is trackable so we can measure whether the resource helps; it contains no personal data. Watch the related field guide on screen next. Subscribe only if evidence-led AI, cybersecurity, and infrastructure decisions are useful to your work. See through everything.",
    ]
    return '\n\n'.join(paragraphs)

def render(data):
    out=["# ClearGlassInc 90-Day Production Book","","> Generated from `content_catalog.json`. Do not edit manually. All examples are fictional unless an evidence register and written release establish otherwise.","","## 90-day master calendar","","**Launch window:** Monday, 2026-08-03 through Saturday, 2026-10-31 (America/Toronto). Sundays are backlog/rest days. Week 13 closes with a livestream on day 89 and review on day 90.","","| Week | Monday–Friday Shorts | Tuesday long-form | Wednesday community | Thursday long-form | Friday livestream |","|---:|---|---|---|---|---|"]
    for w in range(1,14):
        shorts=', '.join(x['id'] for x in data['shorts'] if x['week']==w) or '—'
        lfs=[x for x in data['long_form'] if x['week']==w]
        tue=next((f"{x['id']} — {x['title']}" for x in lfs if x['publish_day']=='Tuesday'),'—')
        thu=next((f"{x['id']} — {x['title']}" for x in lfs if x['publish_day']=='Thursday'),'—')
        cp=next((f"{x['id']} — {x['copy']}" for x in data['community_posts'] if x['week']==w),'—')
        lv=next((f"{x['id']} — {x['title']}" for x in data['livestreams'] if x['week']==w),'—')
        out.append(f"| {w} | {shorts} | {tue} | {cp} | {thu} | {lv} |")
    out += ["","**Daily operating blocks:** 09:00 Short; 12:00 long-form; 15:00 community; 13:00 Friday live. A Short assigned to a long-form publication day moves to 09:00. Dates/times are hypotheses until four-release analytics justify a change.","","# Part I — 24 long-form production packages",""]
    for v in data['long_form']:
        desc=f"{v['hook']}\n\nDownload the {v['lead_magnet'].replace('-',' ').title()}: {utm(v,'description_top')}\n\nIn this evidence-led ClearGlassInc field guide, Desmond Otieno Odhiambo explains {v['search_query']} through five practical controls and a labeled example. Sources and corrections are listed below before publication.\n\nDisclosure: Educational content—not legal, investment, or individualized security advice. Affiliate or paid relationships, if any, will be stated here and in the video."
        tags=[v['search_query'],v['pillar'],'ClearGlassInc','business cybersecurity','AI governance','digital transparency','Canada technology']
        chapters=["00:00 The hidden risk","00:25 Claim and evidence","01:05 Control 1","02:00 Control 2","02:55 Control 3","03:50 Worked example","05:05 Controls 4 and 5","06:35 Action plan","07:10 Next step"]
        out += [f"## {v['id']} — {v['title']}","",f"**Week/day:** {v['week']} / {v['publish_day']}  ",f"**Pillar:** {v['pillar']}  ",f"**Search-informed topic:** `{v['search_query']}`  ",f"**Viewer intent:** {v['viewer_intent']}  ",f"**Primary title:** {v['title']}  ",f"**Alternatives:** (A) {v['title_alternatives'][0]} · (B) {v['title_alternatives'][1]}  ",f"**Thumbnail (≤4 words):** `{v['thumbnail']}`  ",f"**Opening five seconds:** “{v['hook']}”  ",f"**Related service/product:** {v['related_service']} / {v['lead_magnet'].replace('-',' ').title()}  ","", "### Retention outline","","1. **0:00 proof-first hook:** show the risk/result before logo or biography.",f"2. **0:25 contract:** promise five controls and the worked example: {v['case']}","3. **1:05 escalating controls:** alternate direct-to-camera, diagram, and safe screen demonstration.","4. **3:50 pattern interrupt:** worked example plus a specific objection at 5:45.","5. **6:35 compression:** five-card recap, primary CTA, and exact watch-next bridge.","","### Full production-ready script","",long_script(v),"","### Visual and B-roll instructions","",f"- Cold open: founder medium close-up; full-screen `{v['thumbnail']}` for 12 frames; no strobing.","- Evidence cards: source title, publisher, publication/update date, URL host, and retrieval date. Never show a claim before its source card is ready.",f"- Worked example: {v['case']}","- Capture at 4K/30 or 1080p/30; edit a 1080p timeline. Use owned/licensed assets only; retain licence IDs in the evidence register.","- Add human-edited captions, audio description in narration, ≥4.5:1 text contrast, and explicit DEMO/SIMULATION labels.","","### Description","",desc,"","### Chapters","",*chapters,"","### Tags and hashtags","",f"**Tags:** {', '.join(tags)}  ",f"**Hashtags:** #ClearGlassInc #{v['pillar'].replace(' ','').replace('With','')} #DigitalTransparency","","### Pinned comment","",f"What is the first control you can verify this week? Download the maintained checklist: {utm(v,'pinned_comment')} Please do not post secrets, private incidents, wallet details, or customer data. Corrections with primary sources are welcome.","",f"**CTA:** {v['cta']}","","### Pre-record evidence register (must be completed)","","| Claim | Primary/authoritative source | Retrieved (UTC) | Scope/version | Rights/status | Reviewer |","|---|---|---|---|---|---|","| Episode-specific factual claim 1 | BLOCKED until sourced | — | — | — | — |","| Episode-specific factual claim 2 | BLOCKED until sourced | — | — | — | — |","| Visual/music/B-roll licences | Asset licence receipts | — | Exact asset IDs | BLOCKED until verified | — |","","---",""]
    out += ["# Part II — 60 Shorts","","Each Short is 30–45 seconds, uses edited burned-in captions plus an uploaded caption file, and points to one related long-form video. Scripts intentionally avoid unsupported statistics.",""]
    for s in data['shorts']:
        script=f"[0:00] {s['hook']} [0:03] {s['beats'][0]} [0:12] {s['beats'][1]} [0:24] {s['beats'][2]} [0:34] {s['cta']}"
        out += [f"## {s['id']} — {s['title']}","",f"**Week:** {s['week']} · **Intent:** {s['viewer_intent']}  ",f"**Titles:** {s['title']} · Alt A: {s['title_alternatives'][0]} · Alt B: {s['title_alternatives'][1]}  ",f"**Thumbnail:** `{s['thumbnail']}` · **Hook:** “{s['hook']}”  ",f"**Script/retention beats:** {script}  ","**Visuals:** founder vertical 9:16; object/diagram at 0:03; large control phrase at 0:12; checklist at 0:24; related-video sticker at 0:34. No unsafe live demo.  ",f"**Description:** {s['viewer_intent']} Watch the complete evidence-led guide: https://www.youtube.com/@ClearGlassInc  ",f"**Tags/hashtags:** ClearGlassInc, {s['topic']}, {s['related_longform']} {' '.join(s['hashtags'])} #Shorts  ",f"**Pinned comment:** What will you verify first? Watch {s['related_longform']}; never share private operational details here.  ",f"**CTA/product:** {s['cta']} Related free resource is linked on {s['related_longform']}.","","---",""]
    out += ["# Part III — Community posts","","| ID | Week | Format | Production-ready copy | Moderation and CTA |","|---|---:|---|---|---|"]
    for p in data['community_posts']:
        out.append(f"| {p['id']} | {p['week']} | {p['format']} | {p['copy']} | {p['moderation']} {p['cta']} |")
    out += ["","# Part IV — Weekly livestreams",""]
    for stream in data['livestreams']:
        out += [f"## {stream['id']} — {stream['title']}","",f"**Week:** {stream['week']}  ","**Run of show:** "+" → ".join(stream['run_of_show'])+"  ",f"**Safety:** {stream['safety']}  ",f"**CTA:** {stream['cta']}",""]
    return '\n'.join(line.rstrip() for line in out).rstrip()+'\n'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    data=load()
    rendered=render(data)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text()!=rendered:
            raise SystemExit('generated/PRODUCTION_BOOK.md is stale; run builder')
        print(f"OK: {sum(REQUIRED.values())} records validated; production book is current")
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(rendered)
        print(f"wrote {OUTPUT}")

if __name__=='__main__':
    main()
