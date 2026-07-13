import Navbar from "@/components/landing/Navbar";
import Hero from "@/components/landing/Hero";
import FeatureGrid from "@/components/landing/FeatureGrid";
import HowItWorks from "@/components/landing/HowItWorks";
import CtaBand from "@/components/landing/CtaBand";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div>
      <Navbar />
      <Hero />
      <FeatureGrid />
      <HowItWorks />
      <CtaBand />
      <Footer />
    </div>
  );
}
