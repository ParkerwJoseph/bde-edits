/**
 * PillarStrip Component
 *
 * Horizontal strip of pillar score buttons with health-colored backgrounds.
 * Scrollable on mobile, evenly distributed on desktop.
 */

import { useNavigate } from 'react-router-dom';
import {
  DollarSign,
  Target,
  Users,
  Cpu,
  Settings,
  Crown,
  Network,
  ArrowRightLeft,
  type LucideIcon,
} from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/PillarStrip.module.css';

type HealthStatus = 'green' | 'yellow' | 'red';

interface PillarData {
  id: string;
  name: string;
  shortName: string;
  icon: LucideIcon;
  score: number;
}

export interface PillarStripProps {
  /** Custom pillar data */
  pillars?: PillarData[];
  /** Callback when pillar is clicked */
  onPillarClick?: (pillarId: string) => void;
}

// Empty state pillars (no scores yet)
const EMPTY_PILLARS: PillarData[] = [
  { id: 'financial', name: 'Financial', shortName: 'Fin', icon: DollarSign, score: 0 },
  { id: 'gtm', name: 'Go-to-Market', shortName: 'GTM', icon: Target, score: 0 },
  { id: 'customer', name: 'Customer', shortName: 'Cust', icon: Users, score: 0 },
  { id: 'product_tech', name: 'Product & Tech', shortName: 'Prod', icon: Cpu, score: 0 },
  { id: 'operations', name: 'Operations', shortName: 'Ops', icon: Settings, score: 0 },
  { id: 'leadership', name: 'Leadership', shortName: 'Lead', icon: Crown, score: 0 },
  { id: 'ecosystem', name: 'Ecosystem', shortName: 'Eco', icon: Network, score: 0 },
  { id: 'service_to_software', name: 'Service to Software', shortName: 'S2S', icon: ArrowRightLeft, score: 0 },
];

// Score thresholds: 3.5+ green, 2.5-3.5 yellow, <2.5 red, 0 = no data
type HealthStatusExtended = HealthStatus | 'none';

const getHealthStatus = (score: number): HealthStatusExtended => {
  if (score === 0) return 'none';
  if (score >= 3.5) return 'green';
  if (score >= 2.5) return 'yellow';
  return 'red';
};

const healthStyles: Record<HealthStatusExtended, { containerClass: string; label: string }> = {
  green: { containerClass: styles.statusGreen, label: 'Healthy' },
  yellow: { containerClass: styles.statusYellow, label: 'Needs Attention' },
  red: { containerClass: styles.statusRed, label: 'At Risk' },
  none: { containerClass: styles.statusNone, label: 'No Score Yet' },
};

export function PillarStrip({
  pillars = EMPTY_PILLARS,
  onPillarClick,
}: PillarStripProps) {
  const navigate = useNavigate();

  const handlePillarClick = (pillarId: string) => {
    if (onPillarClick) {
      onPillarClick(pillarId);
    } else {
      navigate(`/analytics/pillar/${pillarId}`);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.strip}>
        {pillars.map((pillar) => {
          const Icon = pillar.icon;
          const status = getHealthStatus(pillar.score);
          const healthStyle = healthStyles[status];

          return (
            <TooltipProvider key={pillar.id}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={cn(styles.pillarButton, healthStyle.containerClass)}
                    onClick={() => handlePillarClick(pillar.id)}
                  >
                    <div className={styles.iconWrapper}>
                      <Icon className={styles.icon} />
                    </div>
                    <span className={styles.score}>{pillar.score === 0 ? '—' : pillar.score.toFixed(1)}</span>
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <div className={styles.tooltipContent}>
                    <span className={styles.tooltipName}>{pillar.name}</span>
                    <span className={cn(styles.tooltipStatus, styles[`tooltip${status.charAt(0).toUpperCase() + status.slice(1)}`])}>
                      {healthStyle.label}
                    </span>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    </div>
  );
}

export default PillarStrip;
