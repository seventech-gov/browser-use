'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/app/components/ui/button';
import { cn } from '@/app/utils/utils';

export interface ActionButton {
  id: string;
  label: string;
  icon: React.ElementType;
  href?: string;
  onClick?: () => void;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' | 'success';
  iconClassName?: string;
  className?: string;
  showLabel?: boolean;
}

interface AppHeaderProps {
  title: string;
  subtitle?: string | null;
  actions?: ActionButton[];
  centerTitle?: boolean;
}

export default function AppHeader({ title, subtitle, actions = [], centerTitle = false }: AppHeaderProps) {
  return (
    <header className="w-full border-b bg-background py-6 mb-8">
      <div className="container mx-auto flex flex-wrap items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div
          className={cn(
            'flex min-w-0 flex-grow items-center gap-4',
            centerTitle && 'justify-center'
          )}
        >
          <h1 className="truncate text-2xl font-semibold sm:text-3xl">{title}</h1>
          {subtitle && (
            <small
              className="hidden min-w-0 truncate border-l-2 pl-4 text-base text-muted-foreground sm:block"
              dangerouslySetInnerHTML={{ __html: subtitle }}
            />
          )}
        </div>
        <div className="flex flex-shrink-0 items-center justify-center gap-3 mr-4">
          {actions.map(action => {
            const Icon = action.icon;
            const buttonVariant = action.variant || 'outline';
            const buttonSize = action.showLabel ? 'default' : 'icon';

            const buttonContent = (
              <>
                <Icon className={cn("h-4 w-4", action.iconClassName)} />
                {action.showLabel && <span>{action.label}</span>}
              </>
            );

            if (action.href) {
              return (
                <Button key={action.id} variant={buttonVariant} size={buttonSize} className={action.className} asChild>
                  <Link href={action.href} title={action.label}>
                    {buttonContent}
                  </Link>
                </Button>
              );
            }
            
            return (
              <Button key={action.id} variant={buttonVariant} size={buttonSize} onClick={action.onClick} title={action.label} className={action.className}>
                {buttonContent}
              </Button>
            );
          })}
        </div>
      </div>
    </header>
  );
}