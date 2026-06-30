"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { MobileHeader } from "@/components/mobile-header";
import { AuthProvider, useAuth } from "@/context/auth-context";
import { StudentProvider } from "@/context/student-context";

function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;

    if (!user && pathname !== "/login") {
      router.replace("/login");
    } else if (user && pathname === "/login") {
      router.replace("/chat");
    }
  }, [user, loading, pathname, router]);

  // While checking stored token, show a loading state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500/30 border-t-violet-500" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  // Guard renders while redirecting is in progress
  if (!user && pathname !== "/login") {
    return null;
  }
  if (user && pathname === "/login") {
    return null;
  }

  // Login page renders without the shell
  if (pathname === "/login") {
    return <>{children}</>;
  }


  // Authenticated — render the full app shell
  return (
    <StudentProvider>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </StudentProvider>
  );
}

function AuthenticatedShell({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-gray-950">
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />
      <div className="flex flex-1 flex-col lg:ml-64">
        <MobileHeader onMenuToggle={() => setMobileMenuOpen(true)} />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AuthGate>{children}</AuthGate>
    </AuthProvider>
  );
}
