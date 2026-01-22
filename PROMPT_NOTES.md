# Prompt Engineering Notes for UGC Realism

## Experiment Summary

We tested 6 prompt variations to achieve realistic UGC-style video output from Sora 2.

**Winner: v6_maximum_real**

---

## What Worked

### 1. Structured Prompt Format

Using clear sections with headers helped Sora prioritize instructions:

```
CRITICAL - MUST LOOK REAL NOT AI:
- instruction 1
- instruction 2

CAMERA FEEL:
- instruction 1
- instruction 2
```

This structure > long paragraph of comma-separated descriptors.

### 2. Negative Framing

Explicitly stating what NOT to do was effective:

- "NOT AI generated looking"
- "NOT cinematic"
- "NOT smooth"
- "not a model"
- "NO stabilization"
- "not cleaned up for video"

### 3. Specific Device Reference

Naming the exact device helped establish the aesthetic:

- ✅ "iPhone 13 front facing camera video"
- ❌ "smartphone video" (too generic)

### 4. Imperfection Details

Specific imperfections made it believable:

**Skin:**
- "visible pores especially on nose"
- "natural sebum shine on t-zone"
- "slight dark circles under eyes"
- "natural asymmetrical face"

**Camera:**
- "handheld shake from her arm getting tired"
- "slight focus hunting occasionally"
- "that iPhone front camera slight distortion"

**Environment:**
- "her actual bedroom, not cleaned up for video"
- "can see edge of unmade bed, maybe some clothes"
- "not aesthetically arranged, real life mess"

### 5. Behavioral Authenticity

Describing natural human behavior helped:

- "looking at the phone screen not the lens"
- "talking like she's FaceTiming her best friend"
- "natural umms and pauses, not scripted delivery"
- "real smile that reaches her eyes"

---

## What Didn't Work (or had less impact)

### 1. Generic UGC Descriptors

These were too vague:
- "authentic TikTok style"
- "relatable everyday person vibe"
- "morning routine aesthetic"

### 2. Over-Technical Camera Terms

Sora seemed to ignore these:
- "micro-expressions"
- "natural blink rate"
- "peach fuzz in light"

### 3. Cinematic-Sounding Words

Even when describing amateur footage, these backfired:
- "documentary-style authenticity" (made it MORE cinematic)
- "photorealistic" (triggered AI polish)

---

## The Winning Prompt (v6_maximum_real)

```
iPhone 13 front facing camera video, filmed vertically for TikTok,
a real young woman not a model, mid-20s, average everyday appearance,
holding a green supplement bottle up to show the camera while talking excitedly,

CRITICAL - MUST LOOK REAL NOT AI:
- skin has visible pores especially on nose, natural sebum shine on t-zone
- slight dark circles under eyes, normal human imperfections
- eyes looking at the phone screen not the lens, that typical selfie video eye line
- natural asymmetrical face, one eye slightly different than other
- real hair with flyaways, not perfectly styled

CAMERA FEEL:
- handheld shake from her arm getting tired holding phone up
- slight focus hunting occasionally
- that iPhone front camera slight distortion
- NO stabilization, raw footage feel

ENVIRONMENT:
- her actual bedroom, not cleaned up for video
- can see edge of unmade bed, maybe some clothes
- mixed lighting: ceiling light on plus some window light
- not aesthetically arranged, real life mess

ENERGY:
- genuinely likes the product, not acting
- talking like she's FaceTiming her best friend
- natural umms and pauses, not scripted delivery
- real smile that reaches her eyes
```

---

## Prompt Template for Future Use

```
[DEVICE] front facing camera video, filmed vertically for TikTok,
[PERSON DESCRIPTION], [AGE], [APPEARANCE NOTE],
[ACTION WITH PRODUCT],

CRITICAL - MUST LOOK REAL NOT AI:
- [skin imperfection 1]
- [skin imperfection 2]
- [eye contact detail]
- [facial asymmetry note]
- [hair detail]

CAMERA FEEL:
- [handheld movement reason]
- [focus behavior]
- [lens characteristic]
- NO stabilization, raw footage feel

ENVIRONMENT:
- [specific location with mess]
- [visible items that add authenticity]
- [lighting description - mixed/uneven]
- not aesthetically arranged, real life mess

ENERGY:
- [genuine emotion about product]
- [conversational comparison]
- [speech pattern note]
- [authentic expression detail]
```

---

## Next Steps

1. Test this template with different products
2. Test with different creator demographics (age, gender, setting)
3. Test longer durations (8s, 12s) to see if realism holds
4. Integrate with blueprint system to auto-generate prompts from analysis

---

## Cost Notes

- Sora 2 via Fal.ai: ~$0.10/second
- 4-second test clip: ~$0.40
- Generation time: ~100-120 seconds

---

*Last updated: After v6_maximum_real success*