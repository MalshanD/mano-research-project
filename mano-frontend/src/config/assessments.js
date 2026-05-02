// PHQ-9 (Patient Health Questionnaire-9) - Depression
export const PHQ9_QUESTIONS = [
    {
        id: 1,
        text: "Little interest or pleasure in doing things",
        category: "anhedonia",
    },
    {
        id: 2,
        text: "Feeling down, depressed, or hopeless",
        category: "mood",
    },
    {
        id: 3,
        text: "Trouble falling or staying asleep, or sleeping too much",
        category: "sleep",
    },
    {
        id: 4,
        text: "Feeling tired or having little energy",
        category: "energy",
    },
    {
        id: 5,
        text: "Poor appetite or overeating",
        category: "appetite",
    },
    {
        id: 6,
        text: "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
        category: "self-esteem",
    },
    {
        id: 7,
        text: "Trouble concentrating on things, such as reading the newspaper or watching television",
        category: "concentration",
    },
    {
        id: 8,
        text: "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
        category: "psychomotor",
    },
    {
        id: 9,
        text: "Thoughts that you would be better off dead or of hurting yourself in some way",
        category: "suicidal",
        isCritical: true,
    },
];

export const PHQ9_OPTIONS = [
    { value: 0, label: "Not at all", description: "0 days" },
    { value: 1, label: "Several days", description: "1-7 days" },
    { value: 2, label: "More than half the days", description: "8-11 days" },
    { value: 3, label: "Nearly every day", description: "12-14 days" },
];

export const PHQ9_SCORING = {
    minimal: { min: 0, max: 4, label: "Minimal", color: "success", description: "Your responses suggest minimal depression symptoms." },
    mild: { min: 5, max: 9, label: "Mild", color: "warning", description: "Your responses suggest mild depression symptoms." },
    moderate: { min: 10, max: 14, label: "Moderate", color: "accent", description: "Your responses suggest moderate depression symptoms." },
    moderatelySevere: { min: 15, max: 19, label: "Moderately Severe", color: "danger", description: "Your responses suggest moderately severe depression symptoms." },
    severe: { min: 20, max: 27, label: "Severe", color: "danger", description: "Your responses suggest severe depression symptoms." },
};

// GAD-7 (Generalized Anxiety Disorder-7)
export const GAD7_QUESTIONS = [
    {
        id: 1,
        text: "Feeling nervous, anxious, or on edge",
        category: "nervousness",
    },
    {
        id: 2,
        text: "Not being able to stop or control worrying",
        category: "worry",
    },
    {
        id: 3,
        text: "Worrying too much about different things",
        category: "worry",
    },
    {
        id: 4,
        text: "Trouble relaxing",
        category: "relaxation",
    },
    {
        id: 5,
        text: "Being so restless that it's hard to sit still",
        category: "restlessness",
    },
    {
        id: 6,
        text: "Becoming easily annoyed or irritable",
        category: "irritability",
    },
    {
        id: 7,
        text: "Feeling afraid as if something awful might happen",
        category: "fear",
    },
];

export const GAD7_OPTIONS = [
    { value: 0, label: "Not at all", description: "0 days" },
    { value: 1, label: "Several days", description: "1-7 days" },
    { value: 2, label: "More than half the days", description: "8-11 days" },
    { value: 3, label: "Nearly every day", description: "12-14 days" },
];

export const GAD7_SCORING = {
    minimal: { min: 0, max: 4, label: "Minimal", color: "success", description: "Your responses suggest minimal anxiety symptoms." },
    mild: { min: 5, max: 9, label: "Mild", color: "warning", description: "Your responses suggest mild anxiety symptoms." },
    moderate: { min: 10, max: 14, label: "Moderate", color: "accent", description: "Your responses suggest moderate anxiety symptoms." },
    severe: { min: 15, max: 21, label: "Severe", color: "danger", description: "Your responses suggest severe anxiety symptoms." },
};

// PSS-10 (Perceived Stress Scale)
export const PSS10_QUESTIONS = [
    {
        id: 1,
        text: "In the last month, how often have you been upset because of something that happened unexpectedly?",
        category: "upset",
        reversed: false,
    },
    {
        id: 2,
        text: "In the last month, how often have you felt that you were unable to control the important things in your life?",
        category: "control",
        reversed: false,
    },
    {
        id: 3,
        text: "In the last month, how often have you felt nervous and stressed?",
        category: "stress",
        reversed: false,
    },
    {
        id: 4,
        text: "In the last month, how often have you felt confident about your ability to handle your personal problems?",
        category: "confidence",
        reversed: true,
    },
    {
        id: 5,
        text: "In the last month, how often have you felt that things were going your way?",
        category: "optimism",
        reversed: true,
    },
    {
        id: 6,
        text: "In the last month, how often have you found that you could not cope with all the things that you had to do?",
        category: "coping",
        reversed: false,
    },
    {
        id: 7,
        text: "In the last month, how often have you been able to control irritations in your life?",
        category: "control",
        reversed: true,
    },
    {
        id: 8,
        text: "In the last month, how often have you felt that you were on top of things?",
        category: "mastery",
        reversed: true,
    },
    {
        id: 9,
        text: "In the last month, how often have you been angered because of things that happened that were outside of your control?",
        category: "anger",
        reversed: false,
    },
    {
        id: 10,
        text: "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?",
        category: "overwhelm",
        reversed: false,
    },
];

export const PSS10_OPTIONS = [
    { value: 0, label: "Never" },
    { value: 1, label: "Almost Never" },
    { value: 2, label: "Sometimes" },
    { value: 3, label: "Fairly Often" },
    { value: 4, label: "Very Often" },
];

export const PSS10_SCORING = {
    low: { min: 0, max: 13, label: "Low Stress", color: "success", description: "Your responses suggest low perceived stress levels." },
    moderate: { min: 14, max: 26, label: "Moderate Stress", color: "warning", description: "Your responses suggest moderate perceived stress levels." },
    high: { min: 27, max: 40, label: "High Stress", color: "danger", description: "Your responses suggest high perceived stress levels." },
};

// Assessment types configuration
export const ASSESSMENT_TYPES = {
    PHQ9: {
        id: 'PHQ9',
        name: 'PHQ-9',
        fullName: 'Patient Health Questionnaire-9',
        description: 'A standardized screening tool for depression',
        category: 'depression',
        questions: PHQ9_QUESTIONS,
        options: PHQ9_OPTIONS,
        scoring: PHQ9_SCORING,
        maxScore: 27,
        timeframe: 'Over the last 2 weeks',
        duration: '2-3 minutes',
        icon: '😔',
    },
    GAD7: {
        id: 'GAD7',
        name: 'GAD-7',
        fullName: 'Generalized Anxiety Disorder-7',
        description: 'A standardized screening tool for anxiety',
        category: 'anxiety',
        questions: GAD7_QUESTIONS,
        options: GAD7_OPTIONS,
        scoring: GAD7_SCORING,
        maxScore: 21,
        timeframe: 'Over the last 2 weeks',
        duration: '2-3 minutes',
        icon: '😰',
    },
    PSS10: {
        id: 'PSS10',
        name: 'PSS-10',
        fullName: 'Perceived Stress Scale',
        description: 'Measures the perception of stress in your life',
        category: 'stress',
        questions: PSS10_QUESTIONS,
        options: PSS10_OPTIONS,
        scoring: PSS10_SCORING,
        maxScore: 40,
        timeframe: 'In the last month',
        duration: '3-4 minutes',
        icon: '😤',
    },
};

// Helper functions
export const getScoreLevel = (assessmentType, score) => {
    const scoring = ASSESSMENT_TYPES[assessmentType]?.scoring;
    if (!scoring) return null;

    for (const [key, level] of Object.entries(scoring)) {
        if (score >= level.min && score <= level.max) {
            return { key, ...level };
        }
    }
    return null;
};

export const calculatePSS10Score = (answers) => {
    return PSS10_QUESTIONS.reduce((total, question, index) => {
        const answer = answers[index] || 0;
        if (question.reversed) {
            return total + (4 - answer);
        }
        return total + answer;
    }, 0);
};

export const calculateScore = (assessmentType, answers) => {
    if (assessmentType === 'PSS10') {
        return calculatePSS10Score(answers);
    }
    return answers.reduce((sum, val) => sum + (val || 0), 0);
};