/**
 * ScoreFactors Component
 *
 * Grid display of 8 pillar scores with health indicators.
 * Shows pillar icons, scores, and status dots.
 */

import { useNavigate } from 'react-router-dom';
import {
  DollarSign,
  TrendingUp,
  Users,
  Cpu,
  Settings,
  Crown,
  Network,
  Layers,
  type LucideIcon,
} from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/Tooltip';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/home/ScoreFactors.module.css';

type HealthStatus = 'green' | 'yellow' | 'red';

interface PillarData {
  id: string;
  name: string;
  shortName: string;
  icon: LucideIcon;
  score: number;
}

export interface ScoreFactorsProps {
  /** Custom pillar data */
  pillars?: PillarData[];
  /** Callback when pillar is clicked */
  onPillarClick?: (pillarId: string) => void;
}

const DEFAULT_PILLARS: PillarData[] = [
  { id: 'financial', name: 'Financial', shortName: 'Fin', icon: DollarSign, score: 4.2 },
  { id: 'gtm', name: 'Go-to-Market', shortName: 'GTM', icon: TrendingUp, score: 3.6 },
  { id: 'customer', name: 'Customer', shortName: 'Cust', icon: Users, score: 4.5 },
  { id: 'product_tech', name: 'Product & Tech', shortName: 'Prod', icon: Cpu, score: 3.8 },
  { id: 'operations', name: 'Operations', shortName: 'Ops', icon: Settings, score: 4.0 },
  { id: 'leadership', name: 'Leadership', shortName: 'Lead', icon: Crown, score: 3.2 },
  { id: 'ecosystem', name: 'Ecosystem', shortName: 'Eco', icon: Network, score: 4.1 },
  { id: 'service_to_software', name: 'Service to Software', shortName: 'S2S', icon: Layers, score: 3.9 },
];

const getHealthStatus = (score: number): HealthStatus => {
  if (score >= 4.0) return 'green';
  if (score >= 3.0) return 'yellow';
  return 'red';
};

const healthStyles: Record<HealthStatus, { dotClass: string; label: string }> = {
  green: { dotClass: styles.dotGreen, label: 'Strong' },
  yellow: { dotClass: styles.dotYellow, label: 'Watch' },
  red: { dotClass: styles.dotRed, label: 'At Risk' },
};

export function ScoreFactors({
  pillars = DEFAULT_PILLARS,
  onPillarClick,
}: ScoreFactorsProps) {
  const navigate = useNavigate();

  const handlePillarClick = (pillarId: string) => {
    if (onPillarClick) {
      onPillarClick(pillarId);
    } else {
      navigate(`/analytics/pillar/${pillarId}`);
    }
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>Score Factors</span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button className={styles.helpButton}>?</button>
            </TooltipTrigger>
            <TooltipContent side="top">
              8 pillars that determine your exit readiness score
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Pillar Grid */}
      <div className={styles.grid}>
        {pillars.map((pillar) => {
          const status = getHealthStatus(pillar.score);
          const healthStyle = healthStyles[status];
          const Icon = pillar.icon;

          return (
            <TooltipProvider key={pillar.id}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={styles.pillarButton}
                    onClick={() => handlePillarClick(pillar.id)}
                  >
                    <Icon className={styles.pillarIcon} size={16} />
                    <span className={styles.pillarScore}>{pillar.score.toFixed(1)}</span>
                    <div className={cn(styles.statusDot, healthStyle.dotClass)} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <div className={styles.tooltipContent}>
                    <span className={styles.tooltipName}>{pillar.name}</span>
                    <span className={styles.tooltipStatus}>{healthStyle.label}</span>
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

export default ScoreFactors;
