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
    icon: 'trending_down',
    title: 'Why did we miss our Q4 target?',
    description: 'Multi-source analysis with business context',
  },
  {
    icon: 'psychology',
    title: 'What do you remember about me?',
    description: 'Test persistent memory across sessions',
  },
];

export function WelcomeScreen({ userName = 'there', onQuestionClick }: WelcomeScreenProps) {
  return (
    <div className="max-w-[700px] w-full mx-auto px-6 py-4 flex flex-col">
      {/* Headline */}
      <div className="mb-5 text-center">
        <h1 className="text-[#0d141b] dark:text-white tracking-tight text-2xl font-bold leading-tight">
          Welcome back, {userName}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          What can I help you analyze today?
        </p>
      </div>

      {/* Question Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
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
