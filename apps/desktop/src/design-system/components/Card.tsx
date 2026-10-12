/**
 * Design-system Card — re-export of the shared ui Card.
 *
 * Exists so `design-system/patterns/*` can import from
 * `design-system/components/Card`. No forked styles.
 */

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../../components/ui/card';
export type { CardProps } from '../../components/ui/card';
export { Card as default } from '../../components/ui/card';
