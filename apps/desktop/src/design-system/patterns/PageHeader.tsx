/**
 * AetherOS Design System — PageHeader Pattern
 * Consistent page headers with title, description, and actions.
 */

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils';

import { Button, type ButtonProps } from '../components/Button';

export interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  actions?: (ButtonProps & { label: string })[];
  breadcrumbs?: Array<{ label: string; href?: string; onClick?: () => void }>;
  className?: string;
}

export function PageHeader({
  title,
  description,
  icon,
  actions,
  breadcrumbs,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn('flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6', className)}>
      <div className="flex flex-col gap-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-caption-sm text-muted-foreground">
            {breadcrumbs.map((crumb, index) => (
              <span className="flex items-center gap-1.5" key={crumb.label}>
                {index > 0 && <span aria-hidden="true">/</span>}
                {crumb.href ? (
                  <a className="hover:text-foreground underline-offset-2 hover:underline" href={crumb.href}>
                    {crumb.label}
                  </a>
                ) : crumb.onClick ? (
                  <button
                    className="hover:text-foreground underline-offset-2 hover:underline bg-transparent p-0 text-inherit font-inherit"
                    onClick={crumb.onClick}
                    type="button"
                  >
                    {crumb.label}
                  </button>
                ) : (
                  <span className="text-foreground font-medium">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <div className="flex items-start gap-3">
          {icon && <div aria-hidden="true" className="flex-shrink-0 text-muted-foreground">{icon}</div>}
          <div>
            <h1 className="text-display-sm font-semibold tracking-tight text-foreground">{title}</h1>
            {description && <p className="text-body-sm text-muted-foreground mt-1">{description}</p>}
          </div>
        </div>
      </div>
      {actions && actions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {actions.map((action, index) => (
            <Button
              disabled={action.disabled}
              fullWidth={action.fullWidth}
              key={index}
              leftIcon={action.leftIcon}
              onClick={action.onClick}
              rightIcon={action.rightIcon}
              size={action.size || 'default'}
              variant={action.variant || 'primary'}
            >
              {action.label}
            </Button>
          ))}
        </div>
      )}
    </header>
  );
}

export default PageHeader;