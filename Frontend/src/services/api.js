// Replace this adapter with POST /ask when the backend is ready.
// Contract: askQuestion(question) -> { answer, sources: [{ title, section, text }] }
export const examples = [
  {
    question: 'How many vacation days do I get?',
    answer: 'Full-time employees receive 15 paid vacation days per calendar year. If you join partway through the year, your allowance is prorated based on your start date.',
    sources: [{ title: 'vacation_policy.md', section: 'Annual Vacation Allowance', text: 'Full-time employees receive 15 paid vacation days per calendar year. Employees who begin work partway through the year receive a prorated vacation allowance based on their start date.' }],
  },
  {
    question: 'How often can I work remotely?',
    answer: 'Eligible employees can work remotely up to three days per week, depending on their role and team responsibilities. You should remain available during core collaboration hours, from 10:00 a.m. to 3:00 p.m.',
    sources: [{ title: 'remote_work_policy.md', section: 'Eligibility & Availability', text: 'Employees may work remotely up to three days per week when their role and team responsibilities allow it. Employees working remotely are expected to remain available during core collaboration hours from 10:00 a.m. to 3:00 p.m.' }],
  },
  {
    question: 'How do I contact IT support?',
    answer: 'Contact IT through the internal help desk portal. If an issue prevents you from working, mark your request as high priority.',
    sources: [{ title: 'it_support.md', section: 'Getting Help', text: 'Employees can contact IT support through the internal help desk portal. For urgent issues that prevent an employee from working, the request should be marked as high priority.' }],
  },
];

export async function askQuestion(question) {
  await new Promise((resolve) => setTimeout(resolve, 650));
  const example = examples.find((item) => item.question.toLowerCase() === question.trim().toLowerCase());
  return example ?? {
    answer: 'Your question has been added to this demo conversation. Live answers will be available once the RAG backend is connected. Try one of the example questions to preview an answer with document sources.',
    sources: [],
  };
}
