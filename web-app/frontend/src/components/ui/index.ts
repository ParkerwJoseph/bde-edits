/**
 * BDE UI V2 - Common UI Components
 *
 * Barrel export for all reusable UI components.
 * Migrated to Tailwind CSS + CVA + Radix UI (shadcn/ui pattern).
 */

// Accordion
export { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from './Accordion';

// Alert
export { Alert, AlertTitle, AlertDescription } from './Alert';

// Avatar
export { Avatar, AvatarImage, AvatarFallback } from './Avatar';

// Badge
export { Badge, badgeVariants } from './Badge';
export type { BadgeProps } from './Badge';

// Button
export { Button, buttonVariants } from './Button';
export type { ButtonProps } from './Button';

// Card
export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './Card';

// Chart
export { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent, ChartStyle } from './Chart';
export type { ChartConfig } from './Chart';

// Collapsible
export { Collapsible, CollapsibleTrigger, CollapsibleContent } from './Collapsible';

// Dialog
export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogClose,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './Dialog';

// DropdownMenu
export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
} from './DropdownMenu';

// Input
export { Input } from './Input';

// Label
export { Label } from './Label';

// Pagination
export {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from './Pagination';

// Popover
export { Popover, PopoverTrigger, PopoverContent } from './Popover';

// Progress
export { Progress } from './Progress';

// ScrollArea
export { ScrollArea, ScrollBar } from './ScrollArea';

// Separator
export { Separator } from './Separator';

// Sheet
export {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetOverlay,
  SheetPortal,
  SheetTitle,
  SheetTrigger,
} from './Sheet';

// Sidebar
export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInput,
  SidebarInset,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
  useSidebar,
} from './Sidebar';

// Skeleton
export { Skeleton } from './Skeleton';

// Switch
export { Switch } from './Switch';

// Table
export { Table, TableHeader, TableBody, TableFooter, TableHead, TableRow, TableCell, TableCaption } from './Table';

// Tabs
export { Tabs, TabsList, TabsTrigger, TabsContent } from './Tabs';

// Textarea
export { Textarea } from './Textarea';

// Toast
export {
  type ToastProps,
  type ToastActionElement,
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
} from './Toast';

// Toaster
export { Toaster } from './Toaster';

// Toggle
export { Toggle, toggleVariants } from './Toggle';

// Tooltip
export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './Tooltip';

// Custom Components (project-specific, not from shadcn/ui)
export { ConfidenceMeter } from './ConfidenceMeter';
export { KpiCard } from './KpiCard';
export { AcronymTooltip, AcronymText, useHasAcronyms } from './AcronymTooltip';
