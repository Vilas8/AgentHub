const STEPS = [
  {
    step: "1",
    title: "Browse the marketplace",
    description: "Explore agents by category, use case, or search for specific tasks you want to automate.",
    icon: "🔍",
  },
  {
    step: "2",
    title: "Try an agent for free",
    description: "Many agents offer free tiers. Provide your input and run the agent — no setup required.",
    icon: "▶️",
  },
  {
    step: "3",
    title: "Get real results",
    description: "The agent uses AI to complete your task and returns structured, useful output.",
    icon: "✅",
  },
  {
    step: "4",
    title: "Build your own (optional)",
    description: "Use the Creator Studio to build, test, and publish your own agents. Monetize your expertise.",
    icon: "🛠️",
  },
];

export function HowItWorks() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="container mx-auto px-4">
        <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">How It Works</h2>
        <p className="text-muted-foreground text-center mb-12">From discovery to execution in minutes</p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {STEPS.map((step, i) => (
            <div key={step.step} className="relative flex flex-col items-center text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-2xl mb-4">
                {step.icon}
              </div>
              <h3 className="font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
