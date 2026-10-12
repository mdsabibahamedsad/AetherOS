/**
 * AetherOS Design System — Section Pattern
 * Consistent section layout with header and content.
 */

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils';

import { Button, type ButtonProps } from '../components/Button';

export interface SectionProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ButtonProps & { label: string };
  children: ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
}

export function Section({
  title,
  description,
  icon,
  action,
  children,
  className,
  headerClassName,
  contentClassName,
}: SectionProps) {
  return (
    <section className={cn('space-y-4', className)}>
      {(title || description || icon || action) && (
        <header className={cn('flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3', headerClassName)}>
          <div className="flex items-start gap-3">
            {icon && <div aria-hidden="true" className="flex-shrink-0 text-muted-foreground">{icon}</div>}
            <div>
              {title && <h2 className="text-h4 font-semibold tracking-tight text-foreground">{title}</h2>}
              {description && <p className="text-body-sm text-muted-foreground mt-0.5">{description}</p>}
            </div>
          </div>
          {action && (
            <div className="shrink-0">
              <Button
                disabled={action.disabled}
                leftIcon={action.leftIcon}
                onClick={action.onClick}
                rightIcon={action.rightIcon}
                size={action.size || 'default'}
                variant={action.variant || 'primary'}
              >
                {action.label}
              </Button>
            </div>
          )}
        </header>
      )}
      <div className={cn('space-y-4', contentClassName)}>{children}</div>
    </section>
  );
}

export default Section;