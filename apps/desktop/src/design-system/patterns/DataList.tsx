/**
 * AetherOS Design System — DataList Pattern
 * Consistent list layout for data items.
 */

import { type ReactNode } from 'react';

import { cn } from '@/lib/utils';

import { Badge } from '../components/Badge';
import { Card, CardContent } from '../components/Card';

export interface DataListItem {
  id: string;
  title: string;
  subtitle?: string;
  description?: string;
  icon?: ReactNode;
  avatar?: ReactNode;
  badges?: Array<{ variant?: 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline' } & { children: ReactNode }>;
  actions?: ReactNode;
  metadata?: Array<{ label: string; value: string }>;
  href?: string;
  onClick?: () => void;
}

export interface DataListProps {
  items: DataListItem[];
  renderItem?: (item: DataListItem, index: number) => ReactNode;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  className?: string;
  divided?: boolean;
  hoverable?: boolean;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onSelectionChange?: (id: string, selected: boolean) => void;
}

export function DataList({
  items,
  renderItem,
  emptyMessage = 'No items found',
  emptyAction,
  className,
  divided = true,
  hoverable = false,
  selectable = false,
  selectedIds = new Set(),
  onSelectionChange,
}: DataListProps) {
  if (items.length === 0) {
    return (
      <Card className={cn('py-12', className)}>
        <CardContent className="flex flex-col items-center justify-center text-center py-8">
          <p className="text-body text-muted-foreground">{emptyMessage}</p>
          {emptyAction && <div className="mt-4">{emptyAction}</div>}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <div className="divide-y divide-border/50">
        {items.map((item, index) => (
          <div
            className={cn(
              'flex items-start gap-4 p-4 transition-colors-only',
              hoverable && 'hover:bg-muted/50',
              selectable && 'cursor-pointer',
              selectedIds.has(item.id) && 'bg-primary/5'
            )}
            key={item.id}
            onClick={selectable ? () => onSelectionChange?.(item.id, !selectedIds.has(item.id)) : item.onClick}
            onKeyDown={(e) => {
              if ((selectable || item.onClick) && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                onSelectionChange?.(item.id, !selectedIds.has(item.id));
              }
            }}
            role={selectable || item.onClick ? 'button' : undefined}
            tabIndex={selectable || item.onClick ? 0 : undefined}
          >
            {item.avatar && (
              <div aria-hidden="true" className="flex-shrink-0">{item.avatar}</div>
            )}
            {item.icon && !item.avatar && (
              <div aria-hidden="true" className="flex-shrink-0 mt-0.5 text-muted-foreground">{item.icon}</div>
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-2">
                <h3 className={cn('font-medium text-foreground truncate', selectedIds.has(item.id) && 'text-primary')}>
                  {item.href ? (
                    <a className="hover:underline" href={item.href}>{item.title}</a>
                  ) : (
                    item.title
                  )}
                </h3>
                {item.badges && item.badges.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-0.5">
                    {item.badges.map((badge, i) => (
                      <Badge key={i} {...badge} />
                    ))}
                  </div>
                )}
              </div>
              {item.subtitle && <p className="text-body-sm text-muted-foreground mt-0.5">{item.subtitle}</p>}
              {item.description && <p className="text-body-sm text-muted-foreground mt-1 line-clamp-2">{item.description}</p>}
              {item.metadata && item.metadata.length > 0 && (
                <dl className="flex flex-wrap gap-4 mt-2 text-caption text-muted-foreground">
                  {item.metadata.map((meta, i) => (
                    <div className="flex items-center gap-1" key={i}>
                      <dt className="font-medium">{meta.label}</dt>
                      <dd>{meta.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
            {item.actions && <div className="flex-shrink-0 ml-4">{item.actions}</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}

export default DataList;