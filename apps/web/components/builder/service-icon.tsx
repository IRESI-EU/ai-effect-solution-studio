import {
  Boxes, BrainCircuit, ChartColumn, ClipboardCheck, Database, FileText, Flame, Image as ImageIcon,
  Settings2, Shapes, Sparkles, Trophy, Waves, Zap,
} from "lucide-react";
import type { ServiceIcon as ServiceIconKind } from "../../lib/service-presentation";

const ICONS: Record<ServiceIconKind, typeof Boxes> = {
  config: Settings2,
  topology: Flame,
  drawing: ImageIcon,
  grid: Zap,
  benchmark: Trophy,
  data: Database,
  timeseries: Waves,
  check: ClipboardCheck,
  features: Shapes,
  model: BrainCircuit,
  generate: Sparkles,
  analysis: ChartColumn,
  report: FileText,
  service: Boxes,
};

export function ServiceIcon({ kind, size = 18 }: { kind: ServiceIconKind; size?: number }) {
  const Icon = ICONS[kind] || Boxes;
  return <Icon size={size} strokeWidth={1.75} aria-hidden="true" />;
}
