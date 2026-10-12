/**
 * AetherOS Design System — ActionBar Pattern
 * Consistent action bar for object-level actions.
 */

import { type MouseEvent as ReactMouseEvent } from 'react';

import { MoreHorizontal } from '@/lib/icons';
import { cn } from '@/lib/utils';

import { Button, type ButtonProps } from '../components/Button';
import { DropdownMenu, DropdownMenuContentComponent, DropdownMenuItemComponent, DropdownMenuTriggerComponent } from '../components/DropdownMenu';

export interface ActionItem extends ButtonProps {
  label: string;
  dividerBefore?: boolean;
  danger?: boolean;
}

export interface ActionBarProps {
  primaryActions?: (ButtonProps & { label: string })[];
  secondaryActions?: ActionItem[];
  moreActions?: ActionItem[];
  className?: string;
  align?: 'start' | 'center' | 'end';
}

export function ActionBar({
  primaryActions = [],
  secondaryActions = [],
  moreActions = [],
  className,
  align = 'end',
}: ActionBarProps) {
  const hasMoreActions = moreActions.length > 0;

  return (
    <div className={cn('flex flex-wrap items-center gap-2', `justify-${align}`, className)}>
      {primaryActions.map((action, index) => (
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

      {secondaryActions.map((action, index) => (
        <Button
          className={cn(action.dividerBefore && 'border-l border-border pl-3', action.className)}
          disabled={action.disabled}
          key={`secondary-${index}`}
          leftIcon={action.leftIcon}
          onClick={action.onClick}
          rightIcon={action.rightIcon}
          size={action.size || 'default'}
          variant={action.danger ? 'destructive' : action.variant || 'outline'}
        >
          {action.label}
        </Button>
      ))}

      {hasMoreActions && (
        <DropdownMenu>
          <DropdownMenuTriggerComponent asChild>
            <Button aria-label="More actions" size="icon" variant="ghost">
              <MoreHorizontal aria-hidden="true" className="h-4 w-4" />
            </Button>
          </DropdownMenuTriggerComponent>
          <DropdownMenuContentComponent align="end">
            {moreActions.map((action, index) => (
              <DropdownMenuItemComponent
                className={cn(action.danger && 'text-destructive focus:bg-destructive/10 focus:text-destructive')}
                disabled={action.disabled}
                key={index}
                onSelect={(event) => {
                  event.preventDefault();
                  action.onClick?.(event as unknown as ReactMouseEvent<HTMLButtonElement>);
                }}
              >
                {action.leftIcon && <span aria-hidden="true" className="mr-2">{action.leftIcon}</span>}
                {action.label}
                {action.rightIcon && <span aria-hidden="true" className="ml-auto">{action.rightIcon}</span>}
              </DropdownMenuItemComponent>
            ))}
          </DropdownMenuContentComponent>
        </DropdownMenu>
      )}
    </div>
  );
}

export default ActionBar;