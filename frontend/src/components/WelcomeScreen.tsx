/**
 * Welcome screen shown when there are no messages.
 */

import { QuestionCard } from './QuestionCard';

interface WelcomeScreenProps {
  userName?: string;
  onQuestionClick: (question: string) => void;
}

const SUGGESTED_QUESTIONS = [
  {
    icon: 'payments',
    title: 'What was our Q4 2024 revenue?',
    description: 'View total income trends and targets',
  },
  {
    icon: 'public',
    title: 'Compare regional performance',
    description: 'See sales performance by territory',
  },
  {
    icon: 'military_tech',
    title: 'Who are the top 5 performing reps?',
    description: 'Rank team by deal volume and closing rate',
  },
  {
    icon: 'warning',
    title: 'Identify churn risks this month',
    description: 'Predictive customer analysis and health scores',
  },
];

export function WelcomeScreen({ userName = 'there', onQuestionClick }: WelcomeScreenProps) {
  return (
    <div className="max-w-[800px] w-full mx-auto px-6 py-12 flex flex-col flex-1">
      {/* Headline */}
      <div className="mb-10">
        <h1 className="text-[#0d141b] dark:text-white tracking-tight text-4xl font-extrabold leading-tight">
          Welcome back, {userName}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">
          What can I help you analyze today?
        </p>
      </div>

      {/* Question Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
        {SUGGESTED_QUESTIONS.map((q) => (
          <QuestionCard
            key={q.title}
            icon={q.icon}
            title={q.title}
            description={q.description}
            onClick={() => onQuestionClick(q.title)}
          />
        ))}
      </div>
    </div>
  );
}
