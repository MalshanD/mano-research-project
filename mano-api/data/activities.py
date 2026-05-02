# data/activities.py
# Database of all activities that can be recommended

"""
Activity Database
=================
Contains all activities that can be recommended to users.

Supports 3 main conditions:
- Stress
- Anxiety
- Depression

Each activity has:
- id: Unique identifier
- name: Short name
- description: What it is
- category: Type of activity
- target_conditions: Which conditions it helps (stress, anxiety, depression)
- target_problems: What specific problems it helps with
- difficulty: easy, medium, hard
- duration_minutes: How long it takes
- instructions: Step-by-step guide
- benefits: What user gains
- tags: Keywords for matching
"""

ACTIVITIES_DATABASE = [
    # ============================================
    # STRESS RELIEF ACTIVITIES
    # ============================================
    {
        "id": "stress_001",
        "name": "Deep Breathing Exercise",
        "description": "A simple 4-7-8 breathing technique to calm your nervous system",
        "category": "stress_relief",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["high_stress", "anxiety", "emotional_wellbeing"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Find a comfortable seated position",
            "Close your eyes and relax your shoulders",
            "Breathe in through your nose for 4 seconds",
            "Hold your breath for 7 seconds",
            "Exhale slowly through your mouth for 8 seconds",
            "Repeat 4-6 times"
        ],
        "benefits": [
            "Reduces stress hormones",
            "Lowers heart rate",
            "Promotes relaxation",
            "Can be done anywhere"
        ],
        "tags": ["breathing", "relaxation", "quick", "beginner", "stress", "anxiety"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "stress_002",
        "name": "Progressive Muscle Relaxation",
        "description": "Systematically tense and relax muscle groups to release physical tension",
        "category": "stress_relief",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["high_stress", "physical_tension", "sleep_issues"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Lie down or sit comfortably",
            "Start with your feet - tense muscles for 5 seconds",
            "Release and notice the relaxation for 10 seconds",
            "Move to calves, thighs, stomach, chest, arms, hands, face",
            "End with a full body scan"
        ],
        "benefits": [
            "Releases physical tension",
            "Improves body awareness",
            "Helps with sleep",
            "Reduces anxiety"
        ],
        "tags": ["relaxation", "body", "tension", "sleep", "anxiety", "stress"],
        "effectiveness_score": 80,
        "scientific_backing": True
    },
    {
        "id": "stress_003",
        "name": "Journaling for Stress",
        "description": "Write about your stressors to process and release them",
        "category": "stress_relief",
        "target_conditions": ["stress"],
        "target_problems": ["high_stress", "overwhelm", "racing_thoughts"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Get a notebook or open a notes app",
            "Set a timer for 15 minutes",
            "Write freely about what is stressing you",
            "Don't worry about grammar or spelling",
            "After writing, read it back and identify action items",
            "Close the notebook - symbolically putting stress away"
        ],
        "benefits": [
            "Externalizes worries",
            "Helps identify root causes",
            "Reduces mental load",
            "Creates clarity"
        ],
        "tags": ["journaling", "writing", "stress", "processing", "clarity"],
        "effectiveness_score": 78,
        "scientific_backing": True
    },

    # ============================================
    # ANXIETY RELIEF ACTIVITIES
    # ============================================
    {
        "id": "anxiety_001",
        "name": "5-4-3-2-1 Grounding Technique",
        "description": "Use your senses to ground yourself in the present moment",
        "category": "anxiety_relief",
        "target_conditions": ["anxiety"],
        "target_problems": ["anxiety", "panic", "overwhelm", "racing_thoughts"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Name 5 things you can SEE around you",
            "Name 4 things you can TOUCH/FEEL",
            "Name 3 things you can HEAR",
            "Name 2 things you can SMELL",
            "Name 1 thing you can TASTE",
            "Take a deep breath and notice how you feel"
        ],
        "benefits": [
            "Stops anxiety spirals",
            "Brings you to present moment",
            "Works quickly",
            "No equipment needed"
        ],
        "tags": ["grounding", "anxiety", "panic", "quick", "mindfulness"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "anxiety_002",
        "name": "Worry Time Scheduling",
        "description": "Designate a specific time to process worries instead of all day",
        "category": "anxiety_relief",
        "target_conditions": ["anxiety"],
        "target_problems": ["anxiety", "racing_thoughts", "constant_worry", "overwhelm"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Choose a 15-minute window each day as 'worry time'",
            "When a worry comes up outside this time, write it down",
            "Tell yourself: 'I'll think about this during worry time'",
            "During worry time, review your worry list",
            "For each worry, ask: Can I do something about it?",
            "If yes, write an action step. If no, practice letting go"
        ],
        "benefits": [
            "Contains anxiety to specific time",
            "Reduces all-day worrying",
            "Builds sense of control",
            "Evidence-based CBT technique"
        ],
        "tags": ["anxiety", "worry", "CBT", "scheduling", "control", "thoughts"],
        "effectiveness_score": 82,
        "scientific_backing": True
    },
    {
        "id": "anxiety_003",
        "name": "Box Breathing for Anxiety",
        "description": "A structured breathing pattern used by Navy SEALs to manage anxiety",
        "category": "anxiety_relief",
        "target_conditions": ["anxiety", "stress"],
        "target_problems": ["anxiety", "panic", "high_stress", "racing_thoughts"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Sit upright in a comfortable position",
            "Breathe in slowly for 4 seconds",
            "Hold your breath for 4 seconds",
            "Exhale slowly for 4 seconds",
            "Hold empty lungs for 4 seconds",
            "Repeat for 4-5 cycles",
            "Notice the calm feeling spreading"
        ],
        "benefits": [
            "Activates parasympathetic nervous system",
            "Reduces panic symptoms quickly",
            "Improves focus and clarity",
            "Used by military and first responders"
        ],
        "tags": ["breathing", "anxiety", "panic", "quick", "calming", "focus"],
        "effectiveness_score": 84,
        "scientific_backing": True
    },
    {
        "id": "anxiety_004",
        "name": "Thought Challenging Worksheet",
        "description": "Identify and challenge anxious thoughts using CBT techniques",
        "category": "anxiety_relief",
        "target_conditions": ["anxiety"],
        "target_problems": ["anxiety", "negative_thinking", "catastrophizing", "worry"],
        "difficulty": "medium",
        "duration_minutes": 20,
        "instructions": [
            "Write down the anxious thought exactly",
            "Rate how much you believe it (0-100%)",
            "List evidence FOR the thought",
            "List evidence AGAINST the thought",
            "Write a more balanced alternative thought",
            "Rate how much you believe the new thought",
            "Notice if anxiety has decreased"
        ],
        "benefits": [
            "Core CBT technique for anxiety",
            "Breaks anxious thought patterns",
            "Builds rational thinking skills",
            "Long-term anxiety reduction"
        ],
        "tags": ["CBT", "anxiety", "thoughts", "challenging", "rational", "therapy"],
        "effectiveness_score": 88,
        "scientific_backing": True
    },
    {
        "id": "anxiety_005",
        "name": "Progressive Exposure Practice",
        "description": "Gradually face anxiety-triggering situations in small steps",
        "category": "anxiety_relief",
        "target_conditions": ["anxiety"],
        "target_problems": ["anxiety", "avoidance", "fear", "social_anxiety"],
        "difficulty": "hard",
        "duration_minutes": 30,
        "instructions": [
            "Identify something you avoid due to anxiety",
            "Rate your fear on a scale of 1-10",
            "Break it into small steps (easiest to hardest)",
            "Start with the easiest step today",
            "Stay in the situation until anxiety drops by half",
            "Celebrate completing each step",
            "Move to next step when comfortable"
        ],
        "benefits": [
            "Gold standard treatment for anxiety",
            "Builds confidence over time",
            "Reduces avoidance behaviors",
            "Creates lasting change"
        ],
        "tags": ["exposure", "anxiety", "fear", "avoidance", "therapy", "courage"],
        "effectiveness_score": 90,
        "scientific_backing": True
    },

    # ============================================
    # DEPRESSION RELIEF ACTIVITIES
    # ============================================
    {
        "id": "depression_001",
        "name": "Behavioral Activation - Small Steps",
        "description": "Do one small meaningful activity to break the cycle of withdrawal",
        "category": "depression_relief",
        "target_conditions": ["depression"],
        "target_problems": ["depression", "low_energy", "withdrawal", "low_motivation"],
        "difficulty": "easy",
        "duration_minutes": 10,
        "instructions": [
            "Choose ONE small activity from this list:",
            "- Take a 5-minute walk outside",
            "- Make your bed",
            "- Wash your face with cold water",
            "- Open the curtains and let light in",
            "- Text one person 'good morning'",
            "Do it now, even if you don't feel like it",
            "Notice how you feel after (usually a bit better)"
        ],
        "benefits": [
            "Breaks depression withdrawal cycle",
            "Core evidence-based treatment",
            "Builds momentum for more activity",
            "Small wins boost mood"
        ],
        "tags": ["depression", "activation", "motivation", "small_steps", "mood", "energy"],
        "effectiveness_score": 88,
        "scientific_backing": True
    },
    {
        "id": "depression_002",
        "name": "Pleasant Activity Scheduling",
        "description": "Schedule enjoyable activities into your day to improve mood",
        "category": "depression_relief",
        "target_conditions": ["depression"],
        "target_problems": ["depression", "low_motivation", "anhedonia", "withdrawal"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "List 5 things you used to enjoy (even small things)",
            "Pick 1 activity for today",
            "Schedule it at a specific time",
            "Do it even if motivation is low",
            "Rate your mood before and after (1-10)",
            "Tomorrow, schedule another pleasant activity",
            "Gradually increase to 1-2 per day"
        ],
        "benefits": [
            "Directly counters depression withdrawal",
            "Rebuilds connection to enjoyment",
            "Evidence-based behavioral activation",
            "Creates positive routine"
        ],
        "tags": ["depression", "pleasure", "scheduling", "activation", "mood", "enjoyment"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "depression_003",
        "name": "Cognitive Reframing for Depression",
        "description": "Challenge depressive thought patterns using CBT techniques",
        "category": "depression_relief",
        "target_conditions": ["depression", "anxiety"],
        "target_problems": ["depression", "negative_thinking", "hopelessness", "self_criticism"],
        "difficulty": "medium",
        "duration_minutes": 15,
        "instructions": [
            "Identify a negative thought (e.g., 'I'm worthless')",
            "Write it down exactly as you think it",
            "Ask: Is this thought 100% true? What's the evidence?",
            "Ask: What would I tell a friend with this thought?",
            "Write a more balanced alternative thought",
            "Example: 'I always fail' → 'I've struggled recently but I've also succeeded before'"
        ],
        "benefits": [
            "Breaks negative thought cycles",
            "Core technique from CBT therapy",
            "Builds mental resilience",
            "Changes perspective over time"
        ],
        "tags": ["CBT", "thoughts", "reframing", "depression", "negative_thinking", "therapy"],
        "effectiveness_score": 88,
        "scientific_backing": True
    },
    {
        "id": "depression_004",
        "name": "Social Connection Challenge",
        "description": "Reach out to one person today to combat isolation",
        "category": "depression_relief",
        "target_conditions": ["depression"],
        "target_problems": ["depression", "isolation", "loneliness", "withdrawal"],
        "difficulty": "easy",
        "duration_minutes": 10,
        "instructions": [
            "Think of someone you trust (friend, family, colleague)",
            "Send a simple message: 'Hey, how are you?'",
            "Or make a short phone call",
            "You don't have to talk about how you feel",
            "Just connecting is enough",
            "If that feels too hard, go to a public place (cafe, park)"
        ],
        "benefits": [
            "Breaks isolation cycle",
            "Human connection improves mood",
            "Low effort, high impact",
            "Reminds you people care"
        ],
        "tags": ["depression", "social", "connection", "isolation", "loneliness", "support"],
        "effectiveness_score": 82,
        "scientific_backing": True
    },
    {
        "id": "depression_005",
        "name": "Morning Light Exposure",
        "description": "Get natural sunlight within 30 minutes of waking to boost mood",
        "category": "depression_relief",
        "target_conditions": ["depression"],
        "target_problems": ["depression", "low_energy", "sleep_issues", "fatigue"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Within 30 minutes of waking, go outside",
            "Spend 10-15 minutes in natural daylight",
            "You can walk, sit, or have coffee outside",
            "Don't wear sunglasses (let light reach your eyes)",
            "If cloudy, still go outside - daylight is still bright",
            "Do this daily for best results"
        ],
        "benefits": [
            "Regulates circadian rhythm",
            "Boosts serotonin production",
            "Improves sleep quality",
            "Proven to help depression"
        ],
        "tags": ["depression", "light", "morning", "serotonin", "energy", "sleep"],
        "effectiveness_score": 83,
        "scientific_backing": True
    },
    {
        "id": "depression_006",
        "name": "Exercise for Depression",
        "description": "30 minutes of moderate exercise - as effective as antidepressants for mild depression",
        "category": "depression_relief",
        "target_conditions": ["depression", "stress"],
        "target_problems": ["depression", "low_energy", "low_motivation", "bad_mood"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "Choose an activity: walking, jogging, cycling, swimming",
            "Aim for moderate intensity (can talk but not sing)",
            "Start with just 10 minutes if 30 feels too much",
            "Put on music or a podcast to make it easier",
            "Exercise outdoors if possible for extra benefit",
            "Do this 3-5 times per week for best results"
        ],
        "benefits": [
            "Releases endorphins naturally",
            "Comparable to medication for mild depression",
            "Improves sleep and energy",
            "Builds routine and achievement"
        ],
        "tags": ["depression", "exercise", "endorphins", "physical", "mood", "energy"],
        "effectiveness_score": 90,
        "scientific_backing": True
    },

    # ============================================
    # SLEEP ACTIVITIES
    # ============================================
    {
        "id": "sleep_001",
        "name": "Sleep Hygiene Checklist",
        "description": "Optimize your bedroom and evening routine for better sleep",
        "category": "sleep",
        "target_conditions": ["stress", "anxiety", "depression"],
        "target_problems": ["sleep_issues", "physical_health", "fatigue"],
        "difficulty": "easy",
        "duration_minutes": 30,
        "instructions": [
            "Set bedroom temperature to 65-68°F (18-20°C)",
            "Remove or cover all light sources",
            "Put phone on silent and away from bed",
            "Stop screens 1 hour before bed",
            "Avoid caffeine after 2pm",
            "Go to bed at the same time each night"
        ],
        "benefits": [
            "Improves sleep quality",
            "Reduces time to fall asleep",
            "Increases energy next day",
            "Builds healthy habits"
        ],
        "tags": ["sleep", "routine", "habits", "bedroom", "rest"],
        "effectiveness_score": 88,
        "scientific_backing": True
    },
    {
        "id": "sleep_002",
        "name": "Body Scan Meditation for Sleep",
        "description": "A guided relaxation to help you fall asleep",
        "category": "sleep",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["sleep_issues", "racing_thoughts", "stress", "anxiety"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Lie in bed in a comfortable position",
            "Close your eyes and take 3 deep breaths",
            "Focus attention on your toes - notice any sensations",
            "Slowly move attention up through your body",
            "Spend 30 seconds on each body part",
            "If mind wanders, gently return to body sensations"
        ],
        "benefits": [
            "Quiets racing mind",
            "Relaxes body for sleep",
            "Reduces sleep onset time",
            "No equipment needed"
        ],
        "tags": ["sleep", "meditation", "relaxation", "bedtime", "mindfulness"],
        "effectiveness_score": 78,
        "scientific_backing": True
    },
    {
        "id": "sleep_003",
        "name": "Evening Wind-Down Routine",
        "description": "A 30-minute routine to prepare your mind and body for sleep",
        "category": "sleep",
        "target_conditions": ["stress", "anxiety", "depression"],
        "target_problems": ["sleep_issues", "stress", "poor_routine"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "30 min before bed: Dim lights, no screens",
            "25 min: Light stretching or gentle yoga",
            "20 min: Warm shower or bath",
            "15 min: Prepare clothes for tomorrow",
            "10 min: Read a book (not on screen)",
            "5 min: Write 3 things you're grateful for",
            "Get into bed at your set bedtime"
        ],
        "benefits": [
            "Signals brain it's time to sleep",
            "Reduces stress before bed",
            "Creates predictable routine",
            "Improves sleep quality"
        ],
        "tags": ["sleep", "routine", "evening", "habits", "relaxation"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },

    # ============================================
    # PHYSICAL ACTIVITIES
    # ============================================
    {
        "id": "physical_001",
        "name": "10-Minute Morning Stretch",
        "description": "Gentle stretching routine to start your day with energy",
        "category": "physical",
        "target_conditions": ["stress", "depression"],
        "target_problems": ["low_energy", "physical_health", "stiffness"],
        "difficulty": "easy",
        "duration_minutes": 10,
        "instructions": [
            "Stand and reach arms overhead, stretch tall",
            "Neck rolls - 5 each direction",
            "Shoulder rolls - 10 each direction",
            "Side bends - 5 each side",
            "Forward fold - hang for 30 seconds",
            "Cat-cow stretches - 10 times",
            "Child's pose - 30 seconds"
        ],
        "benefits": [
            "Increases blood flow",
            "Reduces stiffness",
            "Boosts morning energy",
            "Improves flexibility"
        ],
        "tags": ["exercise", "morning", "stretching", "energy", "beginner"],
        "effectiveness_score": 75,
        "scientific_backing": True
    },
    {
        "id": "physical_002",
        "name": "15-Minute Walk Outside",
        "description": "A short walk to boost mood and energy",
        "category": "physical",
        "target_conditions": ["stress", "anxiety", "depression"],
        "target_problems": ["low_energy", "bad_mood", "stress", "physical_health", "depression"],
        "difficulty": "easy",
        "duration_minutes": 15,
        "instructions": [
            "Put on comfortable shoes",
            "Step outside - no destination needed",
            "Walk at a comfortable pace",
            "Notice your surroundings - trees, sky, sounds",
            "Take deep breaths as you walk",
            "If possible, walk in nature or a park"
        ],
        "benefits": [
            "Boosts mood naturally",
            "Increases vitamin D",
            "Burns calories",
            "Clears mind"
        ],
        "tags": ["walking", "outdoor", "nature", "mood", "exercise", "easy", "depression"],
        "effectiveness_score": 82,
        "scientific_backing": True
    },
    {
        "id": "physical_003",
        "name": "Desk Stretches",
        "description": "Quick stretches you can do at your desk",
        "category": "physical",
        "target_conditions": ["stress"],
        "target_problems": ["physical_health", "work_stress", "stiffness"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Seated spinal twist - hold 15 sec each side",
            "Neck stretches - ear to shoulder, hold 15 sec",
            "Wrist circles - 10 each direction",
            "Shoulder shrugs - 10 times",
            "Stand and shake out your body"
        ],
        "benefits": [
            "Relieves desk tension",
            "Can do without leaving desk",
            "Prevents repetitive strain",
            "Quick energy boost"
        ],
        "tags": ["stretching", "work", "desk", "quick", "office"],
        "effectiveness_score": 70,
        "scientific_backing": True
    },

    # ============================================
    # SOCIAL ACTIVITIES
    # ============================================
    {
        "id": "social_001",
        "name": "Reach Out to a Friend",
        "description": "Send a message or call someone you haven't talked to recently",
        "category": "social",
        "target_conditions": ["depression", "anxiety"],
        "target_problems": ["loneliness", "social_connections", "isolation", "depression"],
        "difficulty": "easy",
        "duration_minutes": 10,
        "instructions": [
            "Think of a friend you haven't talked to in a while",
            "Send them a simple message: 'Hey, thinking of you!'",
            "Or call them for a quick chat",
            "Don't overthink it - keep it simple",
            "Ask how they're doing and really listen"
        ],
        "benefits": [
            "Strengthens friendships",
            "Reduces loneliness",
            "Often makes both people feel good",
            "Low effort, high reward"
        ],
        "tags": ["social", "friends", "connection", "communication", "easy", "depression"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "social_002",
        "name": "Join an Online Support Group",
        "description": "Find a community of people with similar experiences",
        "category": "social",
        "target_conditions": ["depression", "anxiety", "stress"],
        "target_problems": ["loneliness", "social_connections", "need_support"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "Search for support groups related to your situation",
            "Options: Reddit communities, Facebook groups, Discord servers",
            "Join 1-2 groups that feel welcoming",
            "Introduce yourself with a brief post",
            "Read others' posts and offer support when you can",
            "Participate at your own comfort level"
        ],
        "benefits": [
            "Connect with people who understand",
            "Available 24/7",
            "Anonymous if preferred",
            "Learn from others' experiences"
        ],
        "tags": ["social", "support", "community", "online", "group"],
        "effectiveness_score": 78,
        "scientific_backing": True
    },
    {
        "id": "social_003",
        "name": "Family Check-In Call",
        "description": "Have a meaningful conversation with a family member",
        "category": "social",
        "target_conditions": ["depression", "stress"],
        "target_problems": ["social_connections", "family_issues", "loneliness"],
        "difficulty": "easy",
        "duration_minutes": 20,
        "instructions": [
            "Choose a family member to call",
            "Schedule a time that works for both",
            "Prepare a few things to share about your life",
            "Ask open-ended questions about their life",
            "Listen actively without trying to fix everything",
            "End by expressing appreciation"
        ],
        "benefits": [
            "Strengthens family bonds",
            "Provides sense of belonging",
            "Can get advice from experience",
            "Mutual support"
        ],
        "tags": ["family", "social", "connection", "support", "call"],
        "effectiveness_score": 80,
        "scientific_backing": True
    },

    # ============================================
    # EMOTIONAL/MOOD ACTIVITIES
    # ============================================
    {
        "id": "emotional_001",
        "name": "Gratitude Journaling",
        "description": "Write down things you're grateful for to shift perspective",
        "category": "emotional",
        "target_conditions": ["depression", "stress"],
        "target_problems": ["bad_mood", "negative_thinking", "emotional_wellbeing", "depression"],
        "difficulty": "easy",
        "duration_minutes": 10,
        "instructions": [
            "Get a notebook or open a notes app",
            "Write today's date",
            "List 3-5 things you're grateful for today",
            "They can be small: 'good coffee', 'sunny weather'",
            "For each one, write WHY you're grateful",
            "Do this daily, ideally at same time"
        ],
        "benefits": [
            "Shifts focus to positive",
            "Scientifically proven to boost mood",
            "Takes only minutes",
            "Builds positive habit"
        ],
        "tags": ["gratitude", "journaling", "mood", "positive", "writing", "depression"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "emotional_002",
        "name": "Mood Tracking",
        "description": "Track your mood patterns to understand yourself better",
        "category": "emotional",
        "target_conditions": ["depression", "anxiety", "stress"],
        "target_problems": ["emotional_wellbeing", "self_awareness", "mood_swings"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Choose a method: app, notebook, or spreadsheet",
            "Check in 2-3 times per day",
            "Rate your mood on a scale of 1-10",
            "Note what you were doing and who you were with",
            "After a week, look for patterns",
            "Identify what improves or worsens your mood"
        ],
        "benefits": [
            "Increases self-awareness",
            "Identifies mood triggers",
            "Helps predict and prepare",
            "Useful for professional help"
        ],
        "tags": ["mood", "tracking", "awareness", "patterns", "emotions"],
        "effectiveness_score": 75,
        "scientific_backing": True
    },

    # ============================================
    # MINDFULNESS ACTIVITIES
    # ============================================
    {
        "id": "mindful_001",
        "name": "5-Minute Mindful Breathing",
        "description": "Simple meditation focusing only on your breath",
        "category": "mindfulness",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["stress", "racing_thoughts", "anxiety", "overwhelm"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "Set a timer for 5 minutes",
            "Sit comfortably with eyes closed",
            "Focus attention on your breath",
            "Notice the inhale... and the exhale...",
            "When mind wanders (it will!), gently return to breath",
            "No judgment - wandering is normal"
        ],
        "benefits": [
            "Calms nervous system",
            "Builds focus over time",
            "Can be done anywhere",
            "Gateway to longer meditation"
        ],
        "tags": ["meditation", "breathing", "mindfulness", "beginner", "calm"],
        "effectiveness_score": 82,
        "scientific_backing": True
    },
    {
        "id": "mindful_002",
        "name": "Mindful Eating Practice",
        "description": "Eat one meal with full attention and presence",
        "category": "mindfulness",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["stress", "rushing", "poor_routine", "mindless_habits"],
        "difficulty": "easy",
        "duration_minutes": 20,
        "instructions": [
            "Choose one meal to eat mindfully",
            "Turn off TV and put away phone",
            "Before eating, look at your food and appreciate it",
            "Take small bites and chew slowly",
            "Notice flavors, textures, temperatures",
            "Put down fork between bites",
            "Stop when you feel satisfied, not stuffed"
        ],
        "benefits": [
            "Reduces overeating",
            "Increases meal enjoyment",
            "Practices presence",
            "Improves digestion"
        ],
        "tags": ["mindfulness", "eating", "presence", "habits", "food"],
        "effectiveness_score": 72,
        "scientific_backing": True
    },
    {
        "id": "mindful_003",
        "name": "Loving-Kindness Meditation",
        "description": "Send wishes of wellbeing to yourself and others",
        "category": "mindfulness",
        "target_conditions": ["depression", "anxiety", "stress"],
        "target_problems": ["self_criticism", "loneliness", "anger", "emotional_wellbeing", "depression"],
        "difficulty": "medium",
        "duration_minutes": 10,
        "instructions": [
            "Sit comfortably and close eyes",
            "Start with yourself: 'May I be happy, may I be healthy'",
            "Think of someone you love: send them the same wishes",
            "Think of a neutral person: send them wishes",
            "Think of someone difficult: try to send wishes",
            "End with all beings: 'May all beings be happy'"
        ],
        "benefits": [
            "Increases self-compassion",
            "Reduces anger and resentment",
            "Builds empathy",
            "Proven to increase positive emotions"
        ],
        "tags": ["meditation", "compassion", "kindness", "self-love", "emotional", "depression"],
        "effectiveness_score": 80,
        "scientific_backing": True
    },

    # ============================================
    # ROUTINE/HABIT ACTIVITIES
    # ============================================
    {
        "id": "routine_001",
        "name": "Morning Routine Starter",
        "description": "Create a simple morning routine to start days better",
        "category": "routine",
        "target_conditions": ["depression", "stress"],
        "target_problems": ["poor_routine", "chaos", "low_energy", "daily_habits", "depression"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "Wake up at the same time each day",
            "Don't check phone for first 30 minutes",
            "Drink a glass of water immediately",
            "Do 5 minutes of stretching",
            "Eat a healthy breakfast",
            "Write 3 priorities for the day",
            "Start with easiest priority first"
        ],
        "benefits": [
            "Sets positive tone for day",
            "Reduces decision fatigue",
            "Increases productivity",
            "Builds discipline"
        ],
        "tags": ["routine", "morning", "habits", "productivity", "discipline", "depression"],
        "effectiveness_score": 85,
        "scientific_backing": True
    },
    {
        "id": "routine_002",
        "name": "Digital Detox Hour",
        "description": "Take one hour completely free from screens",
        "category": "routine",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["screen_addiction", "stress", "poor_sleep", "daily_habits", "anxiety"],
        "difficulty": "medium",
        "duration_minutes": 60,
        "instructions": [
            "Choose one hour (ideally before bed)",
            "Turn off or put away all devices",
            "Tell others you'll be unavailable",
            "Do offline activities: read, craft, walk, talk",
            "Notice how you feel without screens",
            "Gradually increase to 2 hours if comfortable"
        ],
        "benefits": [
            "Reduces digital stress",
            "Improves sleep quality",
            "Increases presence",
            "Breaks phone addiction"
        ],
        "tags": ["digital", "detox", "screens", "habits", "phone", "sleep", "anxiety"],
        "effectiveness_score": 78,
        "scientific_backing": True
    },
    {
        "id": "routine_003",
        "name": "Weekly Planning Session",
        "description": "Plan your week ahead for less stress and more control",
        "category": "routine",
        "target_conditions": ["stress", "anxiety"],
        "target_problems": ["overwhelm", "poor_routine", "stress", "chaos"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "Set aside 30 min on Sunday (or preferred day)",
            "Review last week: what went well? What didn't?",
            "Check calendar for upcoming commitments",
            "Write down top 3 priorities for the week",
            "Schedule time blocks for important tasks",
            "Plan meals for the week",
            "Schedule self-care activities"
        ],
        "benefits": [
            "Reduces weekly stress",
            "Prevents forgetting commitments",
            "Creates sense of control",
            "Improves time management"
        ],
        "tags": ["planning", "routine", "weekly", "organization", "productivity", "stress"],
        "effectiveness_score": 83,
        "scientific_backing": True
    },

    # ============================================
    # PROFESSIONAL HELP
    # ============================================
    {
        "id": "professional_001",
        "name": "Consider Professional Support",
        "description": "Explore options for professional mental health support",
        "category": "professional",
        "target_conditions": ["stress", "anxiety", "depression"],
        "target_problems": ["severe_stress", "depression", "anxiety", "crisis"],
        "difficulty": "medium",
        "duration_minutes": 30,
        "instructions": [
            "Recognize that seeking help is a sign of strength",
            "Research options: therapist, counselor, psychiatrist",
            "Check if your insurance covers mental health",
            "Look for online therapy options (often more affordable)",
            "Ask your doctor for a referral",
            "Many employers offer free counseling (EAP)",
            "Start by booking just one session to try"
        ],
        "benefits": [
            "Professional guidance",
            "Evidence-based treatment",
            "Safe space to talk",
            "Personalized support"
        ],
        "tags": ["therapy", "professional", "help", "counseling", "mental health"],
        "effectiveness_score": 95,
        "scientific_backing": True
    },
    {
        "id": "professional_002",
        "name": "Crisis Resources",
        "description": "Important resources if you're in crisis",
        "category": "professional",
        "target_conditions": ["stress", "anxiety", "depression"],
        "target_problems": ["crisis", "emergency", "severe_depression", "suicidal_thoughts"],
        "difficulty": "easy",
        "duration_minutes": 5,
        "instructions": [
            "If in immediate danger, call emergency services",
            "Crisis hotlines are free and available 24/7",
            "Text HOME to 741741 (Crisis Text Line)",
            "Call 988 (Suicide & Crisis Lifeline)",
            "Go to nearest emergency room if needed",
            "Tell someone you trust how you're feeling",
            "You are not alone and help is available"
        ],
        "benefits": [
            "Immediate support",
            "Free and confidential",
            "Available 24/7",
            "Trained professionals"
        ],
        "tags": ["crisis", "emergency", "help", "hotline", "urgent"],
        "effectiveness_score": 100,
        "scientific_backing": True
    }
]


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_activities():
    """Return all activities."""
    return ACTIVITIES_DATABASE


def get_activities_by_category(category: str):
    """Get activities filtered by category."""
    return [a for a in ACTIVITIES_DATABASE if a['category'] == category]


def get_activity_by_id(activity_id: str):
    """Get a specific activity by its ID."""
    for activity in ACTIVITIES_DATABASE:
        if activity['id'] == activity_id:
            return activity
    return None


def search_activities_by_tags(tags: list):
    """Find activities that match any of the given tags."""
    matching = []
    for activity in ACTIVITIES_DATABASE:
        if any(tag in activity['tags'] for tag in tags):
            matching.append(activity)
    return matching


def get_activities_for_problem(problem: str):
    """Get activities that target a specific problem."""
    matching = []
    for activity in ACTIVITIES_DATABASE:
        if problem in activity['target_problems']:
            matching.append(activity)
    return matching


def get_activities_for_condition(condition: str):
    """Get activities that target a specific condition (stress, anxiety, depression)."""
    matching = []
    for activity in ACTIVITIES_DATABASE:
        if condition in activity.get('target_conditions', []):
            matching.append(activity)
    return matching


# Print summary when file is run directly
if __name__ == "__main__":
    print("=" * 60)
    print("ACTIVITY DATABASE SUMMARY")
    print("=" * 60)

    categories = {}
    for activity in ACTIVITIES_DATABASE:
        cat = activity['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(activity['name'])

    print(f"\nTotal Activities: {len(ACTIVITIES_DATABASE)}")
    print("\nBy Category:")
    for cat, activities in categories.items():
        print(f"\n  {cat.upper()} ({len(activities)} activities):")
        for act in activities:
            print(f"    - {act}")

    # Show condition coverage
    print("\n\nBy Target Condition:")
    for condition in ['stress', 'anxiety', 'depression']:
        matching = get_activities_for_condition(condition)
        print(f"\n  {condition.upper()} ({len(matching)} activities):")
        for act in matching:
            print(f"    - {act['name']}")
