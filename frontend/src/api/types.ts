export type User = {
  id: number;
  email: string;
  display_name: string;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  user: User;
};

export type LifeRule = {
  id: number;
  title: string;
  description: string | null;
  emoji: string | null;
  is_active: boolean;
  streak: number;
  done_today: boolean;
};

export type DailyTask = {
  id: number;
  title: string;
  emoji: string | null;
  scheduled_for: string;
  life_rule_id: number | null;
  completed: boolean;
  completed_at: string | null;
};

export type PlanItem = {
  title: string;
  emoji?: string | null;
  life_rule_id?: number | null;
  completed?: boolean;
};

export type TodaySummary = {
  date: string;
  total_tasks: number;
  completed_tasks: number;
  completion_rate: number;
  streak: number;
  checked_in: boolean;
  mood: string | null;
  headline: string;
  greeting: string;
  display_name: string;
};

export type Insight = { title: string; body: string };

export type RuleBreakdown = {
  id: number;
  title: string;
  emoji: string | null;
  planned: number;
  kept: number;
  rate: number;
};

export type WeeklyReport = {
  week_start: string;
  consistency: number;
  previous_consistency: number;
  delta: number;
  days: Array<{
    date: string;
    label: string;
    total: number;
    completed: number;
    rate: number;
    /** A day later this week that has not happened yet. */
    future: boolean;
  }>;
  best_day: string | null;
  rule_breakdown: RuleBreakdown[];
  patterns: Insight[];
  ai_provider: string;
};

export type Journey = {
  score: number;
  reliability: number;
  presence: number;
  active_days: number;
  window_days: number;
  tasks_planned: number;
  tasks_completed: number;
  current_streak: number;
  longest_streak: number;
  traits: string[];
};

export type CheckIn = {
  id: number;
  checkin_date: string;
  mood: string | null;
  reflection: string | null;
  completed_tasks: number;
  total_tasks: number;
};

export type CheckInResult = {
  check_in: CheckIn;
  insight: Insight;
};

export type CoachAnswer = {
  question: string;
  answer: string;
  ai_provider: string;
};

export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  id: number;
  role: ChatRole;
  content: string;
  created_at: string;
};

export type Conversation = {
  id: number | null;
  title?: string | null;
  messages: ChatMessage[];
  ai_provider: string;
};
