import { auth } from "@/auth";
import { getStages, getTemplates, getModules } from "@/lib/content";
import Sidebar from "@/components/central-implantacao/Sidebar";
import Header from "@/components/central-implantacao/Header";

export default async function ProcessosLayout({ children }: { children: React.ReactNode }) {
  const [session, smStages, leStages, templates, modules] = await Promise.all([
    auth(),
    getStages("sm"),
    getStages("le"),
    getTemplates(),
    getModules(),
  ]);
  const isOwner = session?.user?.role === "owner";

  return (
    <div className="ci-shell">
      <Sidebar isOwner={isOwner} smStages={smStages} leStages={leStages} modules={modules} />
      <div className="ci-main">
        <Header smStages={smStages} leStages={leStages} modules={modules} templates={templates} />
        <div className="ci-content">{children}</div>
      </div>
    </div>
  );
}
