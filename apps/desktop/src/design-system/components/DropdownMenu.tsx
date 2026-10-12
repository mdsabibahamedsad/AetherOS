/**
 * Design-system DropdownMenu — aliases over the shared Radix-based menu.
 *
 * The patterns layer references `*Component` names; the underlying
 * implementation is `components/ui/dropdown-menu` (no forked behavior).
 */

import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenu as Root,
} from '../../components/ui/dropdown-menu';

export const DropdownMenu = Root;
export const DropdownMenuTriggerComponent = DropdownMenuTrigger;
export const DropdownMenuContentComponent = DropdownMenuContent;
export const DropdownMenuItemComponent = DropdownMenuItem;
export const DropdownMenuSeparatorComponent = DropdownMenuSeparator;

export default Root;
