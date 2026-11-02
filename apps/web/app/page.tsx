import { HeroSection } from "@/components/marketing/HeroSection";
import { FeaturedAgents } from "@/components/marketing/FeaturedAgents";
import { CategoriesSection } from "@/components/marketing/CategoriesSection";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { CreatorSection } from "@/components/marketing/CreatorSection";
import { PricingPreview } from "@/components/marketing/PricingPreview";
import { FAQSection } from "@/components/marketing/FAQSection";
import { FooterSection } from "@/components/layout/FooterSection";
import { Navbar } from "@/components/layout/Navbar";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection />
        <FeaturedAgents />
        <CategoriesSection />
        <HowItWorks />
        <CreatorSection />
        <PricingPreview />
        <FAQSection />
      </main>
      <FooterSection />
    </div>
  );
}
