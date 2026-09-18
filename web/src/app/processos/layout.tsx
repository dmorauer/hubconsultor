import { auth } from "@/auth";
import Sidebar from "@/components/central-implantacao/Sidebar";
import Header from "@/components/central-implantacao/Header";

export default async function ProcessosLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  const isOwner = session?.user?.role === "owner";

  return (
    <div className="ci-shell">
      <Sidebar isOwner={isOwner} />
      <div className="ci-main">
        <Header />
        <div className="ci-content">{children}</div>
      </div>
    </div>
  );
}
