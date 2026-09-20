import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: 'Homely',
  slug: 'homely',
  scheme: 'homely',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'automatic',

  ios: { supportsTablet: true },

  android: {
    package: 'com.pablozr.homely',
    adaptiveIcon: {
      backgroundColor: '#123D34',
      foregroundImage: './assets/android-icon-foreground.png',
      backgroundImage: './assets/android-icon-background.png',
      monochromeImage: './assets/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },

  plugins: [
    'expo-router',
    'expo-status-bar',
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 200,
        resizeMode: 'contain',
        backgroundColor: '#123D34',
      },
    ],
  ],
};

export default config;
