import React from 'react';
import { ScrollViewStyleReset } from 'expo-router/html';

/** Expo Web uses its own RU/KG/EN/KZ translations.
 * Prevent browser auto-translation from corrupting the MARINA SMART wordmark,
 * employee-role buttons and interface labels in the interactive QA preview.
 */
export default function Root({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" translate="no">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <meta name="google" content="notranslate" />
        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
