import {
  ChartColumnIcon,
  ChartLineIcon,
  ClipboardListIcon,
  CpuIcon,
  FlaskConicalIcon,
  GaugeIcon,
  HouseIcon,
  LayoutDashboardIcon,
  LibraryIcon,
  ListChecksIcon,
  RouteIcon,
  SchoolIcon,
  TrendingUpIcon,
  UserIcon,
  UsersIcon,
  BookOpenIcon,
} from "lucide-react";

import type { NavItem } from "@/components/app-shell";

export const STUDENT_NAV: NavItem[] = [
  { href: "/home", label: "Home", icon: HouseIcon },
  { href: "/path", label: "Learning path", icon: RouteIcon },
  { href: "/library", label: "Library", icon: LibraryIcon },
  { href: "/progress", label: "Progress", icon: ChartLineIcon },
  { href: "/profile", label: "My profile", icon: UserIcon },
];

export const TEACHER_NAV: NavItem[] = [
  { href: "/teacher", label: "Class overview", icon: LayoutDashboardIcon, exact: true },
  { href: "/teacher/students", label: "Students", icon: UsersIcon },
  { href: "/teacher/aids", label: "Aid library", icon: BookOpenIcon },
  { href: "/teacher/questions", label: "Question bank", icon: ListChecksIcon },
  { href: "/teacher/effectiveness", label: "Aid effectiveness", icon: TrendingUpIcon },
  { href: "/teacher/classes", label: "Classes", icon: SchoolIcon },
];

export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Overview", icon: GaugeIcon, exact: true },
  { href: "/admin/users", label: "Users", icon: UsersIcon },
  { href: "/admin/models", label: "Model report", icon: FlaskConicalIcon },
  { href: "/admin/jobs", label: "Jobs", icon: CpuIcon },
  { href: "/admin/study", label: "Pilot study", icon: ClipboardListIcon },
  { href: "/teacher", label: "Teacher views", icon: ChartColumnIcon },
];
