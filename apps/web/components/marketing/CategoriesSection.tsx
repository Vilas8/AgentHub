import Link from "next/link";

const CATEGORIES = [
  { icon: "🔍", name: "Research", slug: "research", count: "1 agent" },
  { icon: "📄", name: "Documents", slug: "document-processing", count: "1 agent" },
  { icon: "🎧", name: "Support", slug: "customer-support", count: "1 agent" },
  { icon: "📈", name: "Sales", slug: "sales-marketing", count: "1 agent" },
  { icon: "✉️", name: "Email", slug: "email", count: "1 agent" },
  { icon: "📊", name: "Data", slug: "data-analysis", count: "Coming soon" },
  { icon: "💡", name: "Productivity", slug: "productivity", count: "Coming soon" },
  { icon: "💻", name: "Coding", slug: "coding", count: "Coming soon" },
];

export function CategoriesSection() {
  return (
    <section className="py-16">
      <div className="container mx-auto px-4">
        <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Browse by Category</h2>
        <p className="text-muted-foreground text-center mb-8">Find agents built for your workflow</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/marketplace?category=${cat.slug}`}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-border bg-card hover:bg-muted/50 hover:border-primary/40 transition-all group text-center"
            >
              <span className="text-3xl">{cat.icon}</span>
              <span className="font-medium text-sm group-hover:text-primary transition-colors">{cat.name}</span>
              <span className="text-xs text-muted-foreground">{cat.count}</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
