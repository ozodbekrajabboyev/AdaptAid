import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";

export default function PublicLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="bg-graph flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 lg:px-8">
        <Brand />
        <ThemeToggle />
      </header>
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 pb-16 lg:px-8">{children}</main>
      <footer className="mx-auto w-full max-w-6xl px-4 py-6 text-sm text-muted-foreground lg:px-8">
        AdaptAid · An intelligent adaptive learning framework for teaching-aid recommendation
      </footer>
    </div>
  );
}
