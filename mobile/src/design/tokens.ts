/**
 * Homely design tokens.
 *
 * Single source of truth for colour roles, spacing, radii and type. Screens
 * must consume these tokens instead of hard-coding hex literals so the brand
 * stays consistent between light and dark schemes.
 *
 * Brand direction: "Casa em equilíbrio" — calm, minimal, warm without being
 * cute. Light is a cool light stone washed with deep petrol-green ink; dark is
 * a first-class deep petrol scheme, not a quick inversion.
 */

export type ColorScheme = 'light' | 'dark';

export type ThemeColors = {
  /** App background, the cool light stone / deep night base. */
  background: string;
  /** Default card / panel fill sitting on top of the background. */
  surface: string;
  /** Raised surface for elevated cards and inputs. */
  surfaceElevated: string;
  /** Recessed surface for search fields and inset areas. */
  surfaceSunken: string;
  /** Soft brand tint used for selections and quiet emphasis. */
  surfaceAccent: string;
  /** Primary text.  */
  textPrimary: string;
  /** Supporting text and labels. */
  textSecondary: string;
  /** Captions, hints and disabled-adjacent copy. */
  textMuted: string;
  /** Text placed on top of `primary` fills. */
  textOnPrimary: string;
  /** Deep forest / petrol brand colour; primary action fill. */
  primary: string;
  /** Pressed state for primary fills. */
  primaryPressed: string;
  /** Quiet brand tint for selected or informational backgrounds. */
  primarySubtle: string;
  /** Mist blue secondary accent. */
  secondary: string;
  /** Quiet mist blue tint. */
  secondarySubtle: string;
  /** Muted lilac accent reserved for the brandmark core and small highlights. */
  accent: string;
  /** Quiet lilac tint. */
  accentSubtle: string;
  /** Positive feedback. Always paired with an icon/text, never colour alone. */
  success: string;
  /** Quiet success tint. */
  successSubtle: string;
  /** Error feedback. Always paired with text, never colour alone. */
  error: string;
  /** Quiet error tint. */
  errorSubtle: string;
  /** Hairline borders and separators. */
  outline: string;
  /** Stronger outline for interactive edges. */
  outlineStrong: string;
  /** Text input placeholder colour. */
  placeholder: string;
  /** Modal / overlay scrim. */
  scrim: string;
};

export type TypographyToken = {
  fontSize: number;
  lineHeight: number;
  fontWeight: '400' | '500' | '600' | '700';
};

export type Typography = {
  display: TypographyToken;
  title: TypographyToken;
  heading: TypographyToken;
  body: TypographyToken;
  bodyStrong: TypographyToken;
  label: TypographyToken;
  caption: TypographyToken;
};

export type Theme = {
  scheme: ColorScheme;
  colors: ThemeColors;
  spacing: typeof spacing;
  radius: typeof radius;
  typography: Typography;
};

/** Semantic spacing scale: 4 / 8 / 12 / 16 / 24 / 32. */
export const spacing = {
  xxs: 4,
  xs: 8,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
} as const;

/** Moderate radii — intentionally not pills everywhere. */
export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  /** Full round, reserved for avatars and the brandmark core. */
  full: 999,
} as const;

/** Native system type scale (no remote fonts are loaded). */
export const typography: Typography = {
  display: { fontSize: 40, lineHeight: 46, fontWeight: '700' },
  title: { fontSize: 30, lineHeight: 36, fontWeight: '700' },
  heading: { fontSize: 22, lineHeight: 28, fontWeight: '700' },
  body: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  bodyStrong: { fontSize: 16, lineHeight: 24, fontWeight: '600' },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '600' },
  caption: { fontSize: 12, lineHeight: 16, fontWeight: '500' },
};

const lightColors: ThemeColors = {
  background: '#E8ECE9',
  surface: '#F3F6F4',
  surfaceElevated: '#FBFCFB',
  surfaceSunken: '#DEE4E0',
  surfaceAccent: '#D9E7E2',

  textPrimary: '#131E1B',
  textSecondary: '#46564F',
  textMuted: '#68766F',
  textOnPrimary: '#F2F7F4',

  primary: '#123D34',
  primaryPressed: '#0B2C25',
  primarySubtle: '#D6E6E0',

  secondary: '#5F7F92',
  secondarySubtle: '#DCE7EC',

  accent: '#7E6FA0',
  accentSubtle: '#E8E3F0',

  success: '#20694A',
  successSubtle: '#D8EADF',

  error: '#A33A33',
  errorSubtle: '#F1DEDB',

  outline: '#C3CCC7',
  outlineStrong: '#93A19A',

  placeholder: '#7E8C85',
  scrim: 'rgba(9, 20, 17, 0.5)',
};

const darkColors: ThemeColors = {
  background: '#0C1513',
  surface: '#13211D',
  surfaceElevated: '#1B2C27',
  surfaceSunken: '#091110',
  surfaceAccent: '#1E332D',

  textPrimary: '#E7EFEB',
  textSecondary: '#A9B7B1',
  textMuted: '#7D8C86',
  textOnPrimary: '#07201A',

  primary: '#9AC8B7',
  primaryPressed: '#B4D8CA',
  primarySubtle: '#1D332C',

  secondary: '#9FBECE',
  secondarySubtle: '#1C2E36',

  accent: '#BCACDA',
  accentSubtle: '#2A2438',

  success: '#6FC196',
  successSubtle: '#17311F',

  error: '#E2928B',
  errorSubtle: '#3A211F',

  outline: '#2F403A',
  outlineStrong: '#48605A',

  placeholder: '#6E7D77',
  scrim: 'rgba(0, 0, 0, 0.6)',
};

export const lightTheme: Theme = {
  scheme: 'light',
  colors: lightColors,
  spacing,
  radius,
  typography,
};

export const darkTheme: Theme = {
  scheme: 'dark',
  colors: darkColors,
  spacing,
  radius,
  typography,
};

export const themes: Record<ColorScheme, Theme> = {
  light: lightTheme,
  dark: darkTheme,
};
