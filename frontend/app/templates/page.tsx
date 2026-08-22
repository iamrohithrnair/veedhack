import { ResourcePage } from "@/components/resource-page";

export default function TemplatesPage() {
  return <ResourcePage endpoint="/api/templates" title="Templates" description="Reusable creative starting points from your backend." actionLabel="Create from scratch" />;
}
