import { useMemo } from 'react';
import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { Theme } from '@/design/tokens';
import { useTheme } from '@/design/useTheme';

export type ConfirmationSheetProps = {
  visible: boolean;
  title: string;
  /** Explicit consequence copy shown above the actions. */
  message: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** Disables both actions and blocks dismissal while a mutation is running. */
  pending?: boolean;
  /** Inline, retryable error shown above the actions. */
  errorMessage?: string | null;
  /** Uses the semantic error token and keeps the destructive wording explicit. */
  destructive?: boolean;
};

/**
 * Cross-platform confirmation bottom sheet.
 *
 * Controlled presentation on top of React Native's `Modal`: Android back,
 * scrim tap while idle and iOS `onAccessibilityEscape` all cancel, while a
 * pending mutation locks the sheet open.
 */
export function ConfirmationSheet({
  visible,
  title,
  message,
  confirmLabel,
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
  pending = false,
  errorMessage = null,
  destructive = false,
}: ConfirmationSheetProps) {
  const theme = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const insets = useSafeAreaInsets();

  const requestClose = () => {
    if (!pending) {
      onCancel();
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={requestClose}
    >
      <View style={styles.root}>
        <Pressable
          style={styles.scrim}
          onPress={requestClose}
          disabled={pending}
          accessible={false}
          importantForAccessibility="no-hide-descendants"
        />

        <View
          style={[styles.content, { paddingBottom: Math.max(insets.bottom, theme.spacing.lg) }]}
          accessibilityViewIsModal
          onAccessibilityEscape={requestClose}
        >
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.message}>{message}</Text>

          {errorMessage ? (
            <Text style={styles.error} accessibilityLiveRegion="polite">
              {errorMessage}
            </Text>
          ) : null}

          <View style={styles.actions}>
            <Pressable
              style={({ pressed }) => [
                styles.button,
                styles.cancelButton,
                pressed && !pending && styles.buttonPressed,
                pending && styles.buttonDisabled,
              ]}
              onPress={onCancel}
              disabled={pending}
              accessibilityRole="button"
              accessibilityLabel={cancelLabel}
              accessibilityState={{ disabled: pending }}
            >
              <Text style={styles.cancelLabel}>{cancelLabel}</Text>
            </Pressable>

            <Pressable
              style={({ pressed }) => [
                styles.button,
                destructive ? styles.destructiveButton : styles.confirmButton,
                pressed && !pending && styles.buttonPressed,
                pending && styles.buttonDisabled,
              ]}
              onPress={onConfirm}
              disabled={pending}
              accessibilityRole="button"
              accessibilityLabel={confirmLabel}
              accessibilityState={{ disabled: pending, busy: pending }}
            >
              {pending ? (
                <ActivityIndicator color={theme.colors.textOnPrimary} />
              ) : (
                <Text style={styles.confirmLabel}>{confirmLabel}</Text>
              )}
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const createStyles = (theme: Theme) =>
  StyleSheet.create({
    root: { flex: 1, justifyContent: 'flex-end' },
    scrim: {
      ...StyleSheet.absoluteFill,
      backgroundColor: theme.colors.scrim,
    },
    content: {
      width: '100%',
      maxWidth: 480,
      alignSelf: 'center',
      paddingHorizontal: theme.spacing.lg,
      paddingTop: theme.spacing.lg,
      borderTopLeftRadius: theme.radius.lg,
      borderTopRightRadius: theme.radius.lg,
      backgroundColor: theme.colors.surfaceElevated,
    },

    title: { ...theme.typography.heading, color: theme.colors.textPrimary },
    message: {
      ...theme.typography.body,
      marginTop: theme.spacing.xs,
      color: theme.colors.textSecondary,
    },
    error: {
      ...theme.typography.label,
      marginTop: theme.spacing.sm,
      color: theme.colors.error,
    },

    actions: {
      flexDirection: 'row',
      gap: theme.spacing.sm,
      marginTop: theme.spacing.lg,
    },
    button: {
      flex: 1,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      paddingHorizontal: theme.spacing.lg,
      borderRadius: theme.radius.md,
    },
    buttonPressed: { opacity: 0.85 },
    buttonDisabled: { opacity: 0.6 },

    cancelButton: {
      borderWidth: 1,
      borderColor: theme.colors.outlineStrong,
      backgroundColor: theme.colors.surface,
    },
    cancelLabel: { ...theme.typography.bodyStrong, color: theme.colors.primary },

    confirmButton: { backgroundColor: theme.colors.primary },
    destructiveButton: { backgroundColor: theme.colors.error },
    confirmLabel: { ...theme.typography.bodyStrong, color: theme.colors.textOnPrimary },
  });
