import { Fragment } from "react";
import Link from "next/link";
import { Stage } from "@/data/types";

export default function Timeline({ stages, activeId, basePath }: { stages: Stage[]; activeId: string; basePath: string }) {
  const activeOrder = stages.find((s) => s.id === activeId)?.order ?? 0;
  return (
    <div className="ci-timeline">
      {stages.map((stage, index) => (
        <Fragment key={stage.id}>
          <Link href={`${basePath}/${stage.id}`} className={`ci-timeline-step ${stage.id === activeId ? "active" : stage.order < activeOrder ? "done" : ""}`}>
            <span className="ci-dot">{stage.order}</span>
            <span>{stage.title}</span>
          </Link>
          {index < stages.length - 1 && <div className="ci-timeline-line" />}
        </Fragment>
      ))}
    </div>
  );
}
