"use client";

import type { LucideIcon } from "lucide-react";
import { LogOutIcon, MenuIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, Suspense, useEffect, useState } from "react";

import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { type Role, roleHome, useLogout, useMe } from "@/lib/auth";
import { cn } from "@/lib/utils";

export type NavItem = { href: string; label: string; icon: LucideIcon; exact?: boolean };

function isActive(pathname: string, item: NavItem) {
  return item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavList(props: { items: NavItem[]; onNavigate?: () => void }) {
  // usePathname is request data on dynamic routes; Suspense lets the shell prerender.
  return (
    <Suspense fallback={<NavLinks {...props} pathname="" />}>
      <ActiveNavList {...props} />
    </Suspense>
  );
}

function ActiveNavList(props: { items: NavItem[]; onNavigate?: () => void }) {
  const pathname = usePathname();
  return <NavLinks {...props} pathname={pathname} />;
}

function NavLinks({ items, onNavigate, pathname }: { items: NavItem[]; onNavigate?: () => void; pathname: string }) {
  return (
    <nav className="grid gap-0.5" aria-label="Main">
      {items.map((item) => {
        const active = isActive(pathname, item);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
              active && "bg-accent font-bold text-accent-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <item.icon className="size-4" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({
  nav,
  allowed,
  areaLabel,
  children,
}: {
  nav: NavItem[];
  allowed: Role[];
  areaLabel: string;
  children: ReactNode;
}) {
  const { data: me, error } = useMe();
  const router = useRouter();
  const logout = useLogout();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (error) router.replace("/login");
    else if (me && !allowed.includes(me.role)) router.replace(roleHome(me.role));
  }, [me, error, allowed, router]);

  return (
    <div className="bg-graph flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-6 border-r bg-sidebar px-3 py-5 lg:flex">
        <div className="px-2">
          <Brand href={me ? roleHome(me.role) : "/"} />
          <p className="mt-0.5 text-xs text-muted-foreground">{areaLabel}</p>
        </div>
        <NavList items={nav} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur lg:px-8">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open menu">
                <MenuIcon />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-4">
              <SheetTitle className="px-2">
                <Brand />
              </SheetTitle>
              <div className="mt-6">
                <NavList items={nav} onNavigate={() => setOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>
          <div className="lg:hidden">
            <Brand />
          </div>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            {me ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="gap-2" data-testid="user-menu">
                    <span className="grid size-7 place-items-center rounded-full bg-accent text-xs font-bold text-accent-foreground">
                      {me.full_name
                        .split(" ")
                        .map((p) => p[0])
                        .slice(0, 2)
                        .join("")
                        .toUpperCase()}
                    </span>
                    <span className="hidden max-w-40 truncate sm:inline">{me.full_name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="grid">
                    <span className="truncate">{me.full_name}</span>
                    <span className="truncate text-xs font-normal text-muted-foreground">{me.email}</span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onSelect={() => logout.mutate()}>
                    <LogOutIcon /> Sign out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Skeleton className="h-8 w-32" />
            )}
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 lg:px-8 lg:py-8">
          {me && allowed.includes(me.role) ? children : <PageSkeleton />}
        </main>
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="grid gap-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-28 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="grid gap-1">
        <h1 className="font-heading text-2xl font-bold tracking-tight md:text-3xl">{title}</h1>
        {description ? <p className="max-w-prose text-muted-foreground">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
