import Sidebar from "@/components/central-implantacao/Sidebar";
import Header from "@/components/central-implantacao/Header";

export default function ProcessosLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="ci-shell">
      <Sidebar />
      <div className="ci-main">
        <Header />
        <div className="ci-content">{children}</div>
      </div>
    </div>
  );
}
