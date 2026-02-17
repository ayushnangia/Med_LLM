'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { ReviewerHeader } from './ReviewerHeader';
import { useI18n, LanguageToggle } from '@/lib/i18n';
import { Home, FileText, Scale } from 'lucide-react';

export function Navigation() {
  const pathname = usePathname();
  const isHomePage = pathname === '/';
  const { t } = useI18n();

  const navItems = [
    { href: '/', label: t('nav.start'), icon: Home },
    { href: '/cases', label: t('nav.allCases'), icon: FileText },
    { href: '/judge-review', label: t('nav.judgeReview'), icon: Scale, activePrefix: '/judge-review' },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between">
        {/* Left: Logo and Nav */}
        <div className="flex items-center">
          <Link href="/" className="mr-8 flex items-center space-x-2">
            <span className="font-bold text-lg">NCC Review</span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            {navItems.map(item => {
              const Icon = item.icon;
              const matchPath = item.activePrefix || item.href;
              const isActive = pathname === matchPath ||
                (matchPath !== '/' && pathname.startsWith(matchPath));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 transition-colors hover:text-foreground/80',
                    isActive ? 'text-foreground font-semibold' : 'text-foreground/60'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: Language Toggle and Reviewer */}
        <div className="flex items-center gap-4">
          <LanguageToggle />
          {!isHomePage && <ReviewerHeader />}
        </div>
      </div>
    </header>
  );
}
