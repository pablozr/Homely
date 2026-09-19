import { useColorScheme } from 'react-native';

import { darkTheme, lightTheme, type Theme } from './tokens';

/**
 * Resolve the active theme from the system colour scheme.
 *
 * Returns the stable pre-built theme objects, so consumers get a referentially
 * stable value and do not re-create styles on every render.
 */
export function useTheme(): Theme {
  const scheme = useColorScheme();

  return scheme === 'dark' ? darkTheme : lightTheme;
}
