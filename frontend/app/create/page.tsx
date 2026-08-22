import { Suspense } from "react";
import { CreateWorkbench } from "@/components/create-workbench";

export default function CreatePage() {
  return (
    <Suspense fallback={<div className="panel-loading">Loading studio workbench…</div>}>
      <CreateWorkbench />
    </Suspense>
  );
}
