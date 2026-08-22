import { ResourcePage } from "@/components/resource-page";

export default function ProjectsPage() {
  return <ResourcePage endpoint="/api/projects" title="Projects" description="Every video project returned by your Charismate backend." actionLabel="New project" />;
}
