import Svg, { Circle, Path } from 'react-native-svg';

import {
  BRANDMARK_ACCESSIBILITY_LABEL,
  BRANDMARK_CORE,
  BRANDMARK_STROKES,
  BRANDMARK_STROKE_WIDTH,
  brandmarkSvgProps,
} from './brandmark-shape';
import { useTheme } from './useTheme';

type BrandMarkProps = {
  /** Rendered size in dp. */
  size?: number;
  /** Override the stroke colour (defaults to the theme primary). */
  color?: string;
  /** Override the centre core colour (defaults to the theme accent). */
  coreColor?: string;
  /** Set false when the mark is purely decorative next to a labelled wordmark. */
  accessible?: boolean;
};

/**
 * Reusable vector brandmark: two mirrored strokes cradling a central core.
 * Abstract, calm and house-related without a literal roof.
 */
export function BrandMark({ size = 48, color, coreColor, accessible = true }: BrandMarkProps) {
  const theme = useTheme();
  const stroke = color ?? theme.colors.primary;
  const core = coreColor ?? theme.colors.accent;

  return (
    <Svg
      {...brandmarkSvgProps(size)}
      accessible={accessible}
      accessibilityRole="image"
      accessibilityLabel={BRANDMARK_ACCESSIBILITY_LABEL}
    >
      <Path
        d={BRANDMARK_STROKES.left}
        stroke={stroke}
        strokeWidth={BRANDMARK_STROKE_WIDTH}
        strokeLinecap="round"
        fill="none"
      />
      <Path
        d={BRANDMARK_STROKES.right}
        stroke={stroke}
        strokeWidth={BRANDMARK_STROKE_WIDTH}
        strokeLinecap="round"
        fill="none"
      />
      <Circle cx={BRANDMARK_CORE.cx} cy={BRANDMARK_CORE.cy} r={BRANDMARK_CORE.r} fill={core} />
    </Svg>
  );
}
