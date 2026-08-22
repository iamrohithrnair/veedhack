import { ResourcePage } from "@/components/resource-page";

export default function HistoryPage() {
  return <ResourcePage endpoint="/api/projects" title="History" description="Your project generation history returned by the backend." />;
}
