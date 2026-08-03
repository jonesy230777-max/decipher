"""Static per-trait / per-band content library for the Decipher DNA Audit report.

Design rationale (see accompanying notes to Steve): every section on the trait
pages of the target sample report (strength, gap, "what the band above does",
"where you sit", commercial cost, conversation example, next action) varies
only by (trait, band) -- 4 traits x 4 bands = 16 combinations -- not by the
individual respondent beyond their name and score number. That makes a
hand-authored static library the right architecture: consistent voice,
consistent length (per Steve's "95% character consistency" instruction),
no per-report AI latency/cost/failure risk, full editorial control.

The ONE place real personalisation happens is the opening synthesis paragraph
on each trait page and the page-1 profile paragraph, both still written fresh
per audit by Claude (see dna_report_v2.py), because that's where blending the
person's actual four scores into one coherent read genuinely benefits from
generation rather than a fixed template.

Traits use the canonical keys already live in app/dna_scoring.py:
    cognitive_empathy, eq, pressure_composure, storytelling
Bands: developing, practising, performing, elite

NOTE ON BAND THRESHOLDS: the sample report Steve supplied labels its legend
as Developing 0-49 / Practising 50-69 / Performing 70-84 / Elite 85-100.
The LIVE scoring code (app/dna_scoring.py BAND_THRESHOLDS) currently uses
Developing 0-39 / Practising 40-64 / Performing 65-84 / Elite 85-100.
This module does not change scoring; it uses whatever band the live engine
assigns. The legend text below is deliberately built from a constant so it
stays truthful to whichever thresholds are actually live -- flag this
discrepancy to Steve before shipping; it's a scoring-methodology decision,
not a report-design one.
"""
from __future__ import annotations

# Mirrors app/dna_scoring.py BAND_THRESHOLDS. Keep in sync if that changes.
BAND_THRESHOLDS = [("elite", 85), ("performing", 65), ("practising", 40), ("developing", 0)]
BAND_RANGE_LABEL = {
    "developing": "0-39",
    "practising": "40-64",
    "performing": "65-84",
    "elite": "85-100",
}

DIM_LABEL = {
    "cognitive_empathy": "Cognitive Empathy",
    "eq": "Emotional Intelligence",
    "pressure_composure": "Pressure Composure",
    "storytelling": "Narrative Persuasion",
}
DIM_ORDER = ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]
BAND_ORDER = ["developing", "practising", "performing", "elite"]
BAND_LABEL = {"developing": "Developing", "practising": "Practising", "performing": "Performing", "elite": "Elite"}

# ---------------------------------------------------------------------------
# Performance ladder: one line per band, per trait. Shown in full (all 4
# rows) on every trait page regardless of the respondent's own band; their
# own row is highlighted with a "YOU ARE HERE" marker.
# ---------------------------------------------------------------------------
LADDER = {
    "cognitive_empathy": {
        "developing": "Talks through the silence. Reads a one-word answer as agreement and moves on, missing the hesitation entirely.",
        "practising": "Notices the buyer has gone quiet but isn't sure what to do with it, so fills the gap with another feature or question.",
        "performing": "Reads hesitation instinctively and holds the silence. You know something is unsaid; you just don't always name what.",
        "elite": "Reads the hesitation, then diagnoses its source out loud: “It sounds like the timeline is sitting uncomfortably.” A felt signal becomes a spoken one.",
    },
    "eq": {
        "developing": "Manages their own nerves, but the buyer's emotional state is largely invisible to them.",
        "practising": "Picks up the obvious signals, frustration, enthusiasm, but only the loud ones.",
        "performing": "Reads the room accurately and adjusts their own approach in response.",
        "elite": "Doesn't just read the room; changes its temperature. Names the unspoken tension early and shifts what happens next.",
    },
    "pressure_composure": {
        "developing": "Drops the rate the moment it's questioned. Reads pressure as rejection and moves to make the discomfort stop.",
        "practising": "Holds composure in low-stakes calls and is starting to pause. But when the stakes rise, the old reflex returns: justify first, question later.",
        "performing": "Meets every challenge with a question before an answer, consistently, not because they're calmer, but because they've decided in advance what they'll say.",
        "elite": "Reframes the pressure itself, handing it back: “What is it about how they've priced it that works for what you're trying to achieve?” The challenge becomes discovery.",
    },
    "storytelling": {
        "developing": "Recites features and figures. The “story” is a list of what the product does.",
        "practising": "Tells a case study, but the product is the hero: “we delivered X, we achieved Y.”",
        "performing": "Makes the client the hero. Stories are built around what they feared, what they achieved, and what it meant for them.",
        "elite": "Engineers one unforgettable line per story, the sentence the buyer repeats the next day. Nothing is left to emerge on its own.",
    },
}

# ---------------------------------------------------------------------------
# Main content block: strength, gap, what_above (or where_gap for elite),
# where_you_sit, commercial_cost, conversation_example, next_action.
# ---------------------------------------------------------------------------
CONTENT: dict[tuple[str, str], dict[str, str]] = {

    # ---------------- COGNITIVE EMPATHY ----------------
    ("cognitive_empathy", "developing"): {
        "strength": "Willing to keep talking and fill gaps rather than freeze, which keeps calls moving even when unsure what a buyer's silence means.",
        "gap": "Misses hesitation almost entirely, reading a pause or a one-word answer as agreement rather than a signal to slow down.",
        "what_above": "The Practising rep has started to notice when a buyer goes quiet, even without knowing what to do with it. Where you talk through the silence and move on, they feel the gap and instinctively add another feature or question to fill it. The difference isn't skill yet, it's registering that something changed in the room at all.",
        "where_you_sit": "Developing is the starting band for the large majority of new sellers, and the fastest single lift in this audit comes from crossing into Practising. Most of the improvement here is not about learning something new; it is about noticing what is already happening in the room.",
        "commercial_cost": "Missing hesitation entirely means objections surface late, usually after the buyer has already mentally exited the deal. What looks like a slow pipeline is often a string of calls where a real concern was never heard.",
        "conversation_example": "Buyer: “Let me think about it.” Developing rep: “Sure, I'll follow up next week.” A Practising rep hears the same line and pauses half a second longer before responding, giving the buyer room to say more.",
        "next_action": "For your next five calls, say nothing for a full three seconds after a buyer gives a short answer. Notice what happens in that silence. This one habit is the fastest route out of Developing on this trait.",
    },
    ("cognitive_empathy", "practising"): {
        "strength": "Notices when a buyer has gone quiet or given a short answer, the first real step toward reading a room rather than just running through a script.",
        "gap": "Once the silence is noticed, the instinct is to fill it, with another feature, another question, another point, rather than sitting inside it.",
        "what_above": "The Performing rep has learned to do nothing with the silence except hold it. Where you notice the gap and reach to fill it, they let it sit, often for several uncomfortable seconds, because they've learned the next thing the buyer says is usually the truth. The skill isn't reading the room faster. It's resisting the urge to rescue it.",
        "where_you_sit": "Practising is the most crowded band on this trait; most sellers plateau here because holding silence runs directly against everything early sales training rewards. Crossing into Performing is less about learning a new skill and more about unlearning the instinct to speak.",
        "commercial_cost": "Filling every silence with more information trains buyers to expect a pitch instead of a conversation, so the real objection never surfaces on the call, it surfaces after, in an email that says the deal has gone quiet.",
        "conversation_example": "Buyer goes quiet after a price mention. Practising rep: “I can also throw in onboarding support if that helps.” Performing rep says nothing, and waits for the buyer to explain what the pause was actually about.",
        "next_action": "In your next three calls, when a buyer pauses or answers in one word, count to five in your head before speaking again. Notice how often they fill that space themselves with the real concern.",
    },
    ("cognitive_empathy", "performing"): {
        "strength": "Reads buyer hesitation instinctively and resists the urge to fill silence, a behaviour most sellers never develop.",
        "gap": "Identifies that a buyer is hesitant but struggles to consistently diagnose the source: fear, politics, or personal risk.",
        "what_above": "The Elite rep doesn't stop at sensing hesitation; they convert it into a question that names the likely cause. Where you register “something's off” and wait, they register it and immediately test a hypothesis out loud: is this budget, politics, or personal risk? They are comfortable being wrong, because a buyer correcting you, “no, it's that my CMO killed the last one”, hands you the real objection in a single sentence. The gap isn't perception. It's the willingness to voice the diagnosis before you're certain.",
        "where_you_sit": "Cognitive Empathy is where the median seller stalls, most never leave Practising, because resisting the urge to fill silence runs against everything traditional sales training rewards. Sitting in Performing already places you ahead of the majority of the field.",
        "commercial_cost": "Reading hesitation but not naming its source means you answer the wrong objection, the budget concern the buyer never had, while their real worry quietly kills the deal weeks later. The cost isn't one awkward conversation; it's a pipeline of opportunities that stall for reasons you sensed but never opened.",
        "conversation_example": "A Performing rep notices a buyer go quiet and waits. A Performing-to-Elite rep notices the silence and asks: “It sounds like something about the timeline is sitting uncomfortably, what is it?” One reads the signal. The other names it and opens the door.",
        "next_action": "Begin mapping the source of emotion in every discovery conversation, not just the surface signal. When a buyer expresses hesitation, ask one internal question before you respond: is this fear of their leadership team, fear for their own reputation, or fear of the unknown? Track one insight per call this week.",
    },
    ("cognitive_empathy", "elite"): {
        "strength": "Doesn't just read hesitation, names its likely source out loud in the moment, converting a felt signal into a spoken diagnosis the buyer can confirm or correct.",
        "gap": "The ceiling at this level isn't perception, it's consistency: making the diagnostic leap out loud every time, not just when the stakes are obviously high.",
        "where_gap": "There is no higher band to climb to on this trait; you are already reading and naming what most sellers never notice at all. The development question changes shape at Elite: it stops being about your own skill and becomes about whether the rest of your team can do what you do without you in the room.",
        "where_you_sit": "Elite Cognitive Empathy is rare. The overwhelming majority of sellers never reliably name the source of a buyer's hesitation, they either miss it or guess wrong. You are in a small minority who diagnose it correctly in the moment.",
        "commercial_cost": "The cost at this level isn't in the deals you read correctly, it's in the ones only you can read. Every deal that depends on your presence in the room is a deal capped by your calendar, not your capability.",
        "conversation_example": "An Elite rep hears a buyer go quiet after a timeline question and says: “It sounds like the timeline is sitting uncomfortably, is that budget or is that internal politics?” The buyer corrects the guess, and the real objection is on the table inside ten seconds.",
        "next_action": "Shadow one teammate this month and narrate, out loud, the moment you diagnose a buyer's hesitation and why. The skill is fully formed; the next lift is making it transferable.",
    },

    # ---------------- EMOTIONAL INTELLIGENCE ----------------
    ("eq", "developing"): {
        "strength": "Keeps their own composure in the room, which gives them a steady base to build emotional awareness of others on top of.",
        "gap": "The buyer's emotional state is largely invisible; frustration, hesitation or enthusiasm register only when they become impossible to miss.",
        "what_above": "The Practising rep has started to pick up the loud signals, obvious frustration, obvious enthusiasm, even if the quieter ones still pass them by. Where you notice your own state, they've started noticing the buyer's too, at least when it's unmissable. That's the first shift: from managing yourself to watching the room.",
        "where_you_sit": "Developing is the entry band for this trait, and most sellers move through it quickly once they start deliberately watching the buyer rather than just managing their own nerves.",
        "commercial_cost": "When a buyer's frustration or hesitation goes unnoticed, it doesn't disappear, it just moves the objection to a channel you can't see: an internal conversation, a quiet withdrawal, a deal that goes cold without explanation.",
        "conversation_example": "A buyer's tone flattens mid-call after a pricing question. A Developing rep continues the pitch as planned. A Practising rep notices the shift in energy and asks what changed.",
        "next_action": "In your next five calls, pause once per call to silently ask: what is this person feeling right now, not what are they saying. Write it down afterwards and check it against what actually happened.",
    },
    ("eq", "practising"): {
        "strength": "Picks up the obvious emotional signals in a room, frustration, enthusiasm, urgency, and can usually name what's happening once it's clear.",
        "gap": "The quieter signals still pass unnoticed: the subtle hesitation, the polite tone masking disengagement, the enthusiasm that's really relief.",
        "what_above": "The Performing rep reads the room accurately in real time and adjusts their approach in response, not after the call, during it. Where you catch the obvious signals, they catch the subtle ones too, and they change tack mid-conversation instead of noting it for next time.",
        "where_you_sit": "Practising is where most sellers plateau on this trait, reading the loud signals is common, reading the quiet ones consistently is not. Crossing into Performing is one of the highest-leverage moves in this audit.",
        "commercial_cost": "Catching only the obvious signals means you react to problems once they're already visible, which is usually too late to change the outcome of that specific call.",
        "conversation_example": "A buyer says “sounds good” in a flat tone. A Practising rep hears agreement. A Performing rep hears the gap between the words and the tone, and asks a follow-up before moving on.",
        "next_action": "In your next three calls, listen for one moment where tone and words don't match. Name it gently in the moment: “You said that sounds good, but I want to check that's a genuine yes.” Watch what it reveals.",
    },
    ("eq", "performing"): {
        "strength": "Reads the emotional temperature of a room accurately and adjusts approach in real time, not after the fact, a genuine and reliable capability.",
        "gap": "Adjustment is usually reactive, responding well once the emotional shift is visible, rather than shaping the room's temperature before it shifts.",
        "what_above": "The Elite rep doesn't just read the room accurately, they change its temperature. Where you adjust well to what's already happening, they name the unspoken tension early enough to redirect it before it sets the tone for the rest of the call. The gap is initiative: reading versus shaping.",
        "where_you_sit": "Performing is a strong, uncommon band on this trait; most sellers never reliably adjust to the room in real time. The step to Elite is rare enough that it's worth deliberate practice rather than expecting it to happen naturally.",
        "commercial_cost": "Reacting well to emotional shifts still means the room set its own tone first. In the meetings that matter most, the rep who shapes the temperature early wins more of the room than the rep who only adjusts to it.",
        "conversation_example": "A meeting opens with a slightly guarded energy. A Performing rep adjusts their pace once they sense it. An Elite rep names it in the first two minutes: “I sense a bit of caution in the room, is that fair?” and resets the tone before it hardens.",
        "next_action": "In your next high-stakes meeting, name the room's emotional tone out loud in the first five minutes, even if you're not certain you've read it right. Being correctable in public builds more trust than being silently accurate.",
    },
    ("eq", "elite"): {
        "strength": "Reads the emotional subtext of a room, distinguishing between what a buyer says and what they actually fear, a rare Elite-level capability.",
        "gap": "The ceiling at this level is not personal improvement but replication, building this capability in the people around you rather than carrying it alone.",
        "where_gap": "There is no higher band to climb to on this trait, you are already at the ceiling we measure, which makes the development question a different one. At Elite, the constraint is no longer your own capability; it's that you are the only person in the room who has it. The rare Elite EQ rep stops being the team's best reader of buyers and becomes the reason the whole team reads buyers better. That is the shift: from carrying the capability to replicating it.",
        "where_you_sit": "Elite EQ is genuinely rare. The overwhelming majority of sellers never reach this band, and many of the most senior never do either, because seniority rewards confidence, not perception. You are in a small minority.",
        "commercial_cost": "The cost at this level isn't in the deals you run, those are your strongest. It's in the deals you don't. Every pitch where you're not in the room runs without the one capability that wins the hard ones, and your ceiling becomes a scheduling problem: revenue capped by how many meetings you can physically attend.",
        "conversation_example": "An Elite EQ rep does not just manage their own state; they shift the emotional climate of a room. When a meeting starts with tension, they name it early: “I get the sense there are a few competing priorities here, is it worth naming them before we start?” That one move changes everything that follows.",
        "next_action": "After your next team pitch, run a structured debrief with whoever was in the room. Ask three questions: what emotional signals did the room send, who noticed them, and what would have changed if the tension had been named earlier? Do this consistently and you will build a team that reads buyers the way you do.",
    },

    # ---------------- PRESSURE COMPOSURE ----------------
    ("pressure_composure", "developing"): {
        "strength": "Stays engaged in the conversation even when pressure lands, rather than disengaging or going silent, which keeps the door open to recover the call.",
        "gap": "Reads pressure as rejection and moves immediately to relieve the discomfort, usually by dropping the rate or conceding ground before asking a single question.",
        "what_above": "The Practising rep has started to hold their composure, at least in low-stakes moments, and is beginning to pause before reacting. Where you feel pressure and move straight to concession, they've started to notice the urge to concede and occasionally resist it. It isn't consistent yet, but the instinct to pause has started to form.",
        "where_you_sit": "Developing is where sellers land before they've built any deliberate response to pressure, and it's the most common starting point on this trait, the lowest-scoring trait in the whole audit. Small, consistent practice here moves faster than on any other trait.",
        "commercial_cost": "Conceding at the first sign of pressure doesn't just cost margin on one deal, it teaches every buyer who does it that pressure works, which means the next negotiation starts from a weaker position before a word is said.",
        "conversation_example": "Buyer: “That's too expensive.” Developing rep: “I can probably get you 15% off.” Practising rep, hearing the same line, pauses and asks what the number is being compared against before offering anything.",
        "next_action": "Before your next price conversation, write down one question you will ask before you offer any concession. Use it even if it feels awkward. The goal this week isn't a better answer, it's a pause where there used to be none.",
    },
    ("pressure_composure", "practising"): {
        "strength": "Demonstrates composure in low-stakes conversations and is beginning to pause before responding, the foundation of Performing-level pressure management.",
        "gap": "Under real rate or competitive pressure, defaults to justifying rather than questioning, effectively rewarding the buyer's pressure tactic.",
        "what_above": "The Performing rep doesn't improvise composure under fire; they've removed the need to. They walk into every rate conversation with one rehearsed question pre-loaded, so when the pressure lands there's no decision to make in the moment. Your composure is currently reactive, summoned when you remember it, which is why it holds when it's low stakes and slips when the temperature rises. Theirs is structural, built into how they prepare. The gap isn't temperament. It's a decision you haven't yet made in advance.",
        "where_you_sit": "Pressure Composure is the trait where sellers score lowest, and the median sits squarely in Practising, the moment of pressure is the moment most reps revert to instinct. Crossing into Performing would put you ahead of roughly two-thirds of the field, and it is the single trait most likely to move your overall band.",
        "commercial_cost": "Every time you justify a rate before asking a question, you leave margin on the table on that deal, and you train the buyer to push again, because the pressure worked. Across a year of negotiations, a defend-first reflex doesn't cost one discount; it compounds a pattern the buyer learns to exploit.",
        "conversation_example": "Buyer: “Your competitor is $15k cheaper.” Practising rep: “Well, if you look at our reach figures...” Performing rep: “That's worth understanding, what is it about the way they've priced it that makes sense for what you're trying to achieve?” One defends. The other diagnoses.",
        "next_action": "Set one personal rule for your next rate challenge: one question before one answer. Write it somewhere visible before your next high-stakes call. When the pressure lands, breathe, pause, and ask something genuinely curious. Track one outcome per week: how many times did you ask a question before an answer when a buyer pushed back?",
    },
    ("pressure_composure", "performing"): {
        "strength": "Meets pressure with a pre-decided question rather than an in-the-moment reaction, which means composure holds consistently, not just when the stakes are low.",
        "gap": "The response, while consistent, is still built around one prepared move rather than genuine curiosity in the moment, which can read as practised rather than present.",
        "what_above": "The Elite rep doesn't just hold the line with a rehearsed question, they reframe the pressure itself and hand it back as a discovery question the buyer has to answer. Where your prepared question defends your position, theirs relocates the conversation entirely, turning “you're too expensive” into a question about what the buyer actually values. The gap is between defending well and redirecting completely.",
        "where_you_sit": "Performing puts you ahead of roughly two-thirds of the field on the trait where most sellers score lowest, a genuinely strong position. Elite is rare here because it requires reframing pressure as information in real time, not just resisting the urge to concede.",
        "commercial_cost": "A consistently defended position still leaves the buyer in control of the frame, they set the challenge, you respond to it. The deals that get away are the ones where a sharper reframe would have shifted who was actually driving the negotiation.",
        "conversation_example": "Buyer: “Your competitor is $15k cheaper.” Performing rep: “What is it about their pricing that makes sense for what you need?” Elite rep: “What would need to be true for the extra $15k to be the easy decision?” One asks about them. The other makes the buyer build the case for you.",
        "next_action": "Take your one pre-loaded pressure question and add a second layer: after they answer, ask what would need to be true for price to stop being the blocker. Practise this reframe in your next two rate conversations.",
    },
    ("pressure_composure", "elite"): {
        "strength": "Reframes pressure itself in real time, turning a rate challenge or competitor comparison into a question the buyer has to answer, so the challenge becomes discovery rather than defence.",
        "gap": "The ceiling here isn't composure, that's already structural, it's making the reframe feel natural rather than practised, so it lands as curiosity, not a technique.",
        "where_gap": "There is no higher band to climb to on this trait, the reframe is already instinctive under real pressure. The development question shifts from your own composure to whether you can teach the reframe to reps who still feel pressure as an attack rather than information.",
        "where_you_sit": "Elite Pressure Composure is the rarest band on the lowest-scoring trait in the whole audit. Very few sellers ever turn a price objection back into a question the buyer has to answer in the moment.",
        "commercial_cost": "The cost at this level isn't in your own negotiations, it's in every deal run by someone on your team without this instinct, where the old defend-first reflex is still quietly training buyers to push harder.",
        "conversation_example": "Buyer: “Your competitor is $15k cheaper.” Elite rep: “What would need to be true for the extra $15k to be the easy decision?” The buyer, not the rep, ends up building the commercial case.",
        "next_action": "Record, or ask a teammate to note, your next three pressure moments verbatim. Turn one into a coaching example this month so the reframe becomes something the team can learn, not just something you do.",
    },

    # ---------------- NARRATIVE PERSUASION (Storytelling) ----------------
    ("storytelling", "developing"): {
        "strength": "Comes prepared with real numbers and features, which gives every pitch a factual foundation to build a story on top of.",
        "gap": "The pitch is a list, not a story, features and figures recited in order with no character, no stakes, and nothing for the buyer to picture.",
        "what_above": "The Practising rep has started telling case studies rather than reciting features, even if the product is still the hero of the story rather than the client. Where you list what the product does, they've started to say what it did, “we delivered X, we achieved Y.” It's a story shape, even if the wrong character is at the centre of it.",
        "where_you_sit": "Developing is the most common starting point on this trait; most sellers begin here because product training teaches features long before it teaches narrative. The first lift is simple: swap the feature list for a single before-and-after case.",
        "commercial_cost": "A list of features gives the buyer nothing to repeat to their own stakeholders, so the pitch dies in the room it was delivered in, however accurate the numbers were.",
        "conversation_example": "Developing rep: “It integrates with your CRM, has real-time reporting, and a mobile app.” Practising rep: “One client used the reporting to catch a stalled campaign three weeks earlier than they would have otherwise.”",
        "next_action": "Pick your single strongest client result and rewrite it as a two-sentence before-and-after: what was true before, what changed. Use it in your next three pitches instead of a feature list.",
    },
    ("storytelling", "practising"): {
        "strength": "Tells case studies with real before-and-after structure, giving buyers a concrete result to hold onto rather than a list of features.",
        "gap": "The product, not the client, is still the hero of the story: “we delivered X, we achieved Y” centres the seller's work rather than the buyer's experience.",
        "what_above": "The Performing rep tells the same kind of result-based story, but builds it around what the client feared, what they achieved, and what it meant for them personally, not what the seller delivered. Where your story is “we achieved Y,” theirs is “they were worried about X, and here's what changed for them when Y happened.” The shift is one of perspective, not effort.",
        "where_you_sit": "Practising is where most sellers land and stay on this trait; the product-as-hero habit is rarely corrected because it's rarely named. Moving the client to the centre of the story is a small structural change with an outsized effect on memorability.",
        "commercial_cost": "A story where the product is the hero is easy for a buyer to file away as marketing. A story where a client like them is the hero is much harder to dismiss, and much easier to repeat internally.",
        "conversation_example": "Practising rep: “We delivered a 30% lift in reach for that campaign.” Performing rep: “They were nervous the campaign wouldn't cut through before launch. Three weeks in, their CMO was fielding calls asking how they'd done it.”",
        "next_action": "Take your best case study and rewrite it from the client's point of view: what were they afraid of before, and what changed for them, not for you, afterward. Use the rewritten version in your next pitch.",
    },
    ("storytelling", "performing"): {
        "strength": "Makes the client the hero of every story, a structural instinct that most sellers have to be taught explicitly and never fully internalise.",
        "gap": "Relies on strong stories emerging naturally rather than engineering them deliberately, leaving quality inconsistent across pitches.",
        "what_above": "The Elite storyteller designs for the retell. They know a story's job isn't to land in the room, it's to survive the room and get repeated in the boardroom afterwards by someone who wasn't even there. So they build one portable line into every story: a specific image, a number made vivid, a direct quote. “We cut their processing time by 40%” becomes “what used to take a full week now happens before lunch on Monday.” You already make the client the hero. What you don't yet do is engineer the one line that travels. Your best moments arrive by luck. Theirs arrive by design.",
        "where_you_sit": "Storytelling separates cleanly. Most sellers sit in Practising, where the product is the hero and the pitch is a feature tour. Making the client the hero, which you do instinctively, already places you in the minority that buyers remember. What's left is craft, not instinct.",
        "commercial_cost": "A good story that isn't built to travel dies in the room. You win the meeting you're in, but the decision often gets made later, in a room you're not in, by people you never pitched to. If your story can't be repeated accurately by the one champion who was there, your best work never reaches that second room.",
        "conversation_example": "Performing rep: “We cut their processing time by 40%.” Elite rep: “What used to take a full week now happens before lunch on Monday. Their operations director told the board it was the fastest change they'd made all year.” Same data. Completely different impact.",
        "next_action": "Audit your top three client stories this week. For each, ask: what is the one line a buyer would repeat to someone else the next day? If you cannot identify that line, the story is not finished. Then rebuild your strongest case study around a repeatable structure you apply the same way every time.",
    },
    ("storytelling", "elite"): {
        "strength": "Engineers one unforgettable, portable line into every story, the sentence a buyer repeats to someone else the next day, rather than hoping a strong moment emerges naturally.",
        "gap": "The craft is consistent; the remaining edge is applying it under time pressure, in the unplanned moments of a call, not just in prepared pitches.",
        "where_gap": "There is no higher band to climb to on this trait, you already design stories to survive the room and travel beyond it. The development question becomes whether that instinct can be taught, so the standout line isn't something only you can produce.",
        "where_you_sit": "Elite storytelling is uncommon precisely because it requires deliberate engineering, not talent. Most sellers who tell good stories do so by instinct and can't repeat it reliably; you've made repeatable what for most people is accidental.",
        "commercial_cost": "The cost at this level shows up on the deals someone else pitches. Every story your team tells without an engineered line is a story that dies in the room it was told in, a gap only you can currently see and close.",
        "conversation_example": "A teammate says “we cut their processing time by 40%” and the room nods politely. You reframe it live: “that's a full week's work now finished before lunch on Monday,” and the same room starts repeating the line to each other.",
        "next_action": "Write down the framework you use to engineer a portable line as a repeatable structure. Teach it to one teammate this month using their weakest current story as the example.",
    },
}

# ---------------------------------------------------------------------------
# EQ identity: description + 3 short tag chips, per identity type.
# Canonical keys match app/dna_report.py EQ_IDENTITY_LABEL.
# ---------------------------------------------------------------------------
EQ_IDENTITY_LABEL = {
    "regulator": "The Regulator",
    "edge_builder": "The Edge Builder",
    "observer": "The Observer",
    "namer": "The Namer",
}

EQ_IDENTITY_CONTENT = {
    "regulator": {
        "strength": (
            "Your EQ signature is the Regulator. Under pressure you stay logical, "
            "your judgement does not get cloudy when the room heats up, and "
            "buyers trust the steadiness you bring. You are the rep clients call "
            "first when something has gone wrong elsewhere."
        ),
        "action": (
            "Practise one deliberate emotional acknowledgement per difficult call "
            "this week. Your composure is an asset; pair it with one labelled "
            "feeling and the buyer feels both safe and seen."
        ),
        "chips": ["STAYS LOGICAL UNDER FIRE", "STEADY UNDER PRESSURE", "HIGH RELIABILITY"],
    },
    "edge_builder": {
        "strength": (
            "Your EQ signature is the Edge Builder. You treat the buyer's "
            "emotion as commercial information, not noise. The signal you pick "
            "up about hesitation, irritation, or quiet excitement is the lever "
            "that informs your next move."
        ),
        "action": (
            "Audit the last five deals you lost. For each, write one emotional "
            "lever the buyer telegraphed that you did not use. Take one of "
            "those levers into your next live call."
        ),
        "chips": ["USES EMOTION AS LEVERAGE", "STRATEGICALLY RESPONSIVE", "DEAL MOMENTUM BUILDER"],
    },
    "observer": {
        "strength": (
            "Your EQ signature is the Observer. You notice the emotional "
            "temperature before anyone names it: the slight pause, the change "
            "of pace, the buyer who has gone polite when they were warm two "
            "minutes ago. You see the shift first."
        ),
        "action": (
            "Translate one observation into a spoken acknowledgement per call. "
            "Seeing it is half the work; the other half is letting the buyer "
            "hear that you saw it, so they do not have to perform."
        ),
        "chips": ["SEES SIGNALS FIRST", "READS THE ROOM EARLY", "QUIET PRECISION"],
    },
    "namer": {
        "strength": (
            "Your EQ signature is the Namer. You will say the awkward thing "
            "out loud when others rush past it. Buyers find this disarming, "
            "and it shortens the distance from objection to honest answer."
        ),
        "action": (
            "Pace yourself: name the emotion early, then hold. Resist the urge "
            "to immediately solve. The 8-second silence after a well-placed "
            "label is where the buyer's real concern emerges."
        ),
        "chips": ["NAMES UNSPOKEN TENSION", "HIGH TRUST BUILDER", "C-SUITE EFFECTIVE"],
    },
}

# ---------------------------------------------------------------------------
# Archetype "strategic objective" tag chip -- one line per archetype code.
# Codes match app/dna_scoring.py ARCHETYPE_BY_PAIR values / archetypes.code.
# ---------------------------------------------------------------------------
ARCHETYPE_OBJECTIVE = {
    "trust_architect": "RELATIONSHIP FOUNDATION",
    "story_listener": "NARRATIVE ALIGNMENT",
    "calm_diagnostician": "HIGH-STAKES STABILISER",
    "strategic_empath": "C-SUITE MULTIPLIER",
    "composed_reader": "STEADY DEAL CLOSER",
    "confident_storyteller": "ROOM COMMANDER",
    "elite_operator": "FULL-RANGE OPERATOR",
    "raw_material": "FOUNDATION BUILDER",
}

# ---------------------------------------------------------------------------
# Static "this report contains" bullets (page 1) -- identical across reports.
# ---------------------------------------------------------------------------
REPORT_CONTAINS = [
    "Trait-by-trait diagnostic with behavioural insight",
    "Strength and gap analysis for each trait",
    "A four-band performance ladder showing where you sit versus peers",
    "Real conversation examples and the commercial cost of each gap",
    "A specific Next Action and your 30-Day Development Roadmap",
]


def band_for(score_100: float) -> str:
    for band, lower in BAND_THRESHOLDS:
        if score_100 >= lower:
            return band
    return "developing"


def get_trait_content(trait: str, band: str) -> dict:
    """Fetch the static content block for a trait/band, with elite's
    'where_gap' aliased to 'what_above' for uniform template access."""
    block = dict(CONTENT[(trait, band)])
    if band == "elite":
        block["what_above_heading"] = "Where the gap is at this level"
        block["what_above"] = block.pop("where_gap")
    else:
        block["what_above_heading"] = "What the band above does that you don't yet"
    return block
